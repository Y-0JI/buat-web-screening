import os
import warnings
from pydantic import field_validator
from pydantic_settings import BaseSettings


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


settings = Settings()
