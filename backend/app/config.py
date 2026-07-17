import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    env: str = "development"
    gemini_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./bsjp.db"
    yfinance_period: str = "6mo"
    cache_ttl_seconds: int = 3600
    rate_limit_per_minute: int = 15
    scheduler_enabled: bool = True
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:3000"
    sectors_api_key: str = ""
    frontend_url: str = "http://localhost:3000"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "no-reply@bsjp.local"
    smtp_timeout: int = 10

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        env = info.data.get("env", os.getenv("ENV", "development"))
        if env == "production" and v in ("change-me-in-production", ""):
            raise ValueError(
                "JWT_SECRET must be set to a secure value in production. "
                "The default value is not allowed."
            )
        return v

    @field_validator("database_url")
    @classmethod
    def resolve_sqlite_path(cls, v: str) -> str:
        # Resolve relative SQLite paths to an absolute path anchored at the
        # backend directory so every process (regardless of CWD) reads/writes
        # the SAME physical database. This prevents "Login can't recognize
        # existing accounts" caused by the engine silently creating/using a
        # different file when the server is launched from another directory.
        if not v.startswith("sqlite"):
            return v
        # Format: sqlite+driver:///path
        prefix, _, dbpath = v.partition(":///")
        p = Path(dbpath)
        if not p.is_absolute():
            p = (BASE_DIR / p).resolve()
        return f"{prefix}:///{p}"


settings = Settings()
