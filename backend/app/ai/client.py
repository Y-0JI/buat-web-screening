from openai import OpenAI
from app.config import settings

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.ai_api_key, base_url=settings.ai_base_url)
    return _client