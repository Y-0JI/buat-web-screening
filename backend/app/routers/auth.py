import asyncio
import bcrypt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.config import settings
from app.database import get_session
from app.database.models import User
from app.email import send_reset_email
from app.schemas.auth import (
    AuthRegister,
    AuthLogin,
    TokenResponse,
    UserProfile,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

RESET_TOKEN_TTL = timedelta(hours=1)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid"
            )
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token tidak valid")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan")
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> Optional[User]:
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError):
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.post("/register", response_model=TokenResponse)
async def register(req: AuthRegister, session: AsyncSession = Depends(get_session)):
    user = User(
        username=req.username,
        email=req.email,
        password_hash=bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode(),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Username atau email sudah terdaftar")
    await session.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserProfile(id=user.id, username=user.username, email=user.email),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: AuthLogin, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not bcrypt.checkpw(req.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Username atau password salah")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserProfile(id=user.id, username=user.username, email=user.email),
    )


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(get_current_user)):
    return UserProfile(id=user.id, username=user.username, email=user.email)


@router.post("/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    # Gunakan sumber data & session YANG SAMA dengan Login (tabel users).
    result = await session.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    # Keamanan: jangan ungkap apakah email terdaftar.
    if user:
        token = secrets.token_urlsafe(32)
        # Simpan hash token (bukan token aslinya) agar aman bila DB bocor.
        user.reset_token_hash = bcrypt.hashpw(
            token.encode(), bcrypt.gensalt()
        ).decode()
        user.reset_token_expiry = datetime.now(timezone.utc) + RESET_TOKEN_TTL
        await session.commit()
        # Kirim email di luar alur utama (background task + thread pool) supaya
        # request tidak nyangkut dan event loop tidak terblokir kalau server
        # SMTP lambat/tidak responsif.
        background_tasks.add_task(asyncio.to_thread, send_reset_email, user.email, token)

    return {
        "detail": "Jika email terdaftar, tautan reset password akan dikirim ke alamat tersebut."
    }


@router.post("/reset-password")
async def reset_password(
    req: ResetPasswordRequest, session: AsyncSession = Depends(get_session)
):
    # Cari user lewat verifikasi hash (token asli tak pernah disimpan di DB).
    result = await session.execute(
        select(User).where(
            User.reset_token_hash.isnot(None),
            User.reset_token_expiry.isnot(None),
            User.reset_token_expiry >= datetime.now(timezone.utc),
        )
    )
    user = None
    for candidate in result.scalars().all():
        if bcrypt.checkpw(req.token.encode(), candidate.reset_token_hash.encode()):
            user = candidate
            break

    if not user:
        raise HTTPException(status_code=400, detail="Token reset tidak valid.")

    user.password_hash = bcrypt.hashpw(
        req.password.encode(), bcrypt.gensalt()
    ).decode()
    user.reset_token_hash = None
    user.reset_token_expiry = None
    await session.commit()

    return {"detail": "Password berhasil direset. Silakan login kembali."}
