from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from passlib.hash import bcrypt
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import get_session
from app.database.models import User
from app.schemas.auth import AuthRegister, AuthLogin, TokenResponse, UserProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
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


@router.post("/register", response_model=TokenResponse)
async def register(req: AuthRegister, session: AsyncSession = Depends(get_session)):
    existing = await session.execute(
        select(User).where((User.username == req.username) | (User.email == req.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username atau email sudah terdaftar")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=bcrypt.hash(req.password),
    )
    session.add(user)
    await session.commit()
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

    if not user or not bcrypt.verify(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Username atau password salah")

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user=UserProfile(id=user.id, username=user.username, email=user.email),
    )


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(get_current_user)):
    return UserProfile(id=user.id, username=user.username, email=user.email)
