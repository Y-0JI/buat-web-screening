from openai import OpenAI, AsyncOpenAI
from app.config import settings

_client: OpenAI | None = None
_async_client: AsyncOpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
    return _client


def get_async_client() -> AsyncOpenAI:
    global _async_client
    if _async_client is None:
        _async_client = AsyncOpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
    return _async_client