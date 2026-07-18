"""Repository Fundamentals — satu pintu akses data fundamental.

Primary: IDX (`IdxProvider`) untuk pe/pbv/roe/roa/der/market_cap/revenue.
Gap-fill: Yahoo Finance (`FundamentalsProvider`) untuk dividend_yield, beta,
forward_pe, fifty_two_week_high/low, pb. Hasil dinormalisasi ke schema kanonik
(16.4.3) — `pb` dijamin ada (alias dari `pbv` IDX) supaya konsumen downstream
(orchestrator) tidak putus.
"""

from app.cache.memory_cache import MemoryCache
from app.providers import FundamentalsProvider, IdxProvider

_FUNDAMENTALS_TTL = 24 * 3600  # 24 jam (sesuai arah 16.4.5)

# Field yang hanya Yahoo punyai & dipakai downstream — diisi dari Yahoo bila
# IDX tidak menyediakan.
_YAHOO_ONLY = {"dividend_yield", "beta", "forward_pe", "fifty_two_week_high", "fifty_two_week_low"}


def _merge_fundamentals(idx: dict, yf: dict) -> dict:
    """Gabung IDX (primary) + Yahoo (gap-fill) lalu normalisasi.

    IDX menang untuk field yang ia punya; Yahoo mengisi field yang kurang.
    `pb` dijamin ada (alias `pbv` IDX) untuk kompatibilitas downstream.
    """
    merged: dict = {}
    for d in (idx, yf):
        for k, v in d.items():
            if k in ("error", "source", "fetched_at"):
                continue
            if v is None:
                continue
            if k not in merged:
                merged[k] = v
    # downstream membaca `pb`; IDX memberi `pbv`
    if merged.get("pb") is None and merged.get("pbv") is not None:
        merged["pb"] = merged["pbv"]
    merged["source"] = "idx+yahoo" if not yf.get("error") else "idx"
    merged["fetched_at"] = idx.get("fetched_at") or yf.get("fetched_at")
    return merged


class FundamentalsRepository:
    def __init__(
        self,
        provider: FundamentalsProvider | None = None,
        idx_provider: IdxProvider | None = None,
        cache: MemoryCache | None = None,
    ):
        self._provider = provider or FundamentalsProvider()
        self._idx_provider = idx_provider or IdxProvider()
        self._cache = cache or MemoryCache(default_ttl=_FUNDAMENTALS_TTL)

    async def get_fundamentals(self, symbol: str) -> dict:
        key = symbol.upper().replace(".JK", "")
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        idx = await self._idx_provider.fetch_fundamentals(symbol)
        yf = await self._safe_yahoo(symbol)
        if idx.get("error") and yf.get("error"):
            return {"error": idx.get("error") or yf.get("error"), "source": "none"}
        merged = _merge_fundamentals(idx, yf) if not idx.get("error") else yf
        await self._cache.set(key, merged)
        return merged

    async def _safe_yahoo(self, symbol: str) -> dict:
        try:
            return await self._provider.fetch_fundamentals(symbol)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}
