"""Cache untuk Data Layer.

Satu implementasi nyata: `MemoryCache` (in-memory, TTL per-entry), diakses
terpusat lewat `CacheService` (`cache/service.py`). Tanpa lapisan abstraksi
tambahan — bila kelak butuh backend kedua (Redis/DB), abstraksinya dibangun
saat itu, bukan disiapkan duluan.
"""

def get_cache_service():
    """Akses singleton CacheService (import malas hindari circular import)."""
    from app.cache.service import cache_service
    return cache_service
