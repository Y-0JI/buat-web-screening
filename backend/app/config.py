from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    database_url: str = "postgresql+asyncpg://localhost/bsjp"
    yfinance_period: str = "6mo"
    cache_ttl_seconds: int = 3600
    rate_limit_per_minute: int = 15
    scheduler_enabled: bool = True
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    class Config:
        env_file = ".env"


settings = Settings()
