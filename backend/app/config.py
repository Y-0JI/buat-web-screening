from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    database_url: str = "postgresql://localhost/bsjp"
    yfinance_period: str = "6mo"
    cache_ttl_seconds: int = 3600
    rate_limit_per_minute: int = 15
    scheduler_enabled: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
