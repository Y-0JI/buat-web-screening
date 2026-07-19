"""Abstraksi cache untuk Data Layer.

Repository tidak bergantung pada implementasi cache tertentu; mereka hanya
menggunakan `CacheBackend`. Implementasi nyata (MemoryCache saat ini, Redis/
database di masa depan) bisa diganti tanpa menyentuh repository.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Ambil value berdasarkan key, atau None bila tidak ada/kadaluarsa."""

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Simpan value dengan time-to-live (detik)."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Hapus satu entry."""

    @abstractmethod
    async def clear(self, prefix: Optional[str] = None) -> None:
        """Hapus entry. `prefix` None → semua; selain itu hanya key berawalan prefix."""


def get_cache_service():
    """Akses singleton CacheService (import malas hindari circular import)."""
    from app.cache.service import cache_service
    return cache_service
