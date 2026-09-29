"""Router katalog model AI — proxy `GET /v1/models` dari 9router.

Frontend butuh daftar model untuk pemilih model, tetapi TIDAK boleh memegang
API key 9router. Endpoint ini mem-proxy, menormalkan, dan menyaring hanya model
yang mendukung tool-calling (agar agen tidak memilih model yang tidak bisa
memanggil tool). Hasil di-cache singkat agar tidak memanggil 9router tiap request.
"""

import logging
import time

import httpx
from fastapi import APIRouter

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["models"])

_CACHE_TTL = 300
_cache: dict = {"ts": 0.0, "data": None}

_PROVIDER_LABELS = {
    "combo": "Combo",
    "openai": "OpenAI",
    "gemini": "Gemini",
    "gc": "Google",
    "kr": "KRouter",
    "ds": "DeepSeek",
    "gh": "GitHub",
    "cmc": "CMC",
}


def normalize_model(raw: dict) -> dict:
    """Bentuk satu model 9router → struktur stabil untuk UI."""
    caps = raw.get("capabilities") or {}
    provider = raw.get("owned_by") or "other"
    return {
        "id": raw.get("id"),
        "name": raw.get("id"),
        "provider": provider,
        "provider_label": _PROVIDER_LABELS.get(provider, provider.title()),
        "capabilities": {
            "vision": bool(caps.get("vision")),
            "tools": bool(caps.get("tools")),
            "reasoning": bool(caps.get("reasoning")),
            "search": bool(caps.get("search")),
        },
        "context_window": caps.get("contextWindow"),
    }


def filter_tool_models(models: list[dict]) -> list[dict]:
    """Hanya model yang mendukung tools (wajib untuk agen)."""
    return [m for m in models if m.get("capabilities", {}).get("tools")]


@router.get("/models")
async def list_models():
    now = time.time()
    if _cache["data"] is not None and now - _cache["ts"] < _CACHE_TTL:
        return {"success": True, "data": _cache["data"], "cached": True}

    if not settings.ai_api_key:
        return {"success": False, "error": "AI_API_KEY belum diisi", "data": []}

    url = f"{settings.ai_base_url.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                url, headers={"Authorization": f"Bearer {settings.ai_api_key}"}
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("Gagal mengambil daftar model dari 9router: %s", e)
        return {"success": False, "error": "Gagal mengambil daftar model", "data": []}

    models = filter_tool_models(
        [normalize_model(m) for m in payload.get("data", [])]
    )
    _cache["ts"] = now
    _cache["data"] = models
    return {"success": True, "data": models, "cached": False}
