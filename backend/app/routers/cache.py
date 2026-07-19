"""Router manual refresh cache (16.4.5).

`POST /api/cache/refresh` menginvalidasi cache. Tanpa `type` → hapus semua
kategori; dengan `type` → hapus satu kategori. Semua lewat `cache_service`
terpusat.
"""

import logging

from fastapi import APIRouter

from app.cache.service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["cache"])

_VALID_CATEGORIES = {
    "profile",
    "fundamental",
    "news",
    "price",
    "verify",
    "technical",
    "screener",
    "screen",
}


@router.post("/cache/refresh")
async def refresh_cache(type: str | None = None):
    if type is None:
        await cache_service.clear()
        logger.info("Cache di-refresh: semua kategori")
        return {"success": True, "cleared": "all"}
    if type not in _VALID_CATEGORIES:
        return {
            "success": False,
            "error": f"type tidak dikenal: {type}",
            "valid_types": sorted(_VALID_CATEGORIES),
        }
    await cache_service.clear(type)
    logger.info("Cache di-refresh: kategori %s", type)
    return {"success": True, "cleared": type}
