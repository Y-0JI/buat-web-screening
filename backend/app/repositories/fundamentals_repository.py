"""Repository Fundamentals — satu pintu akses data fundamental.

Primary: IDX (`IdxProvider`) untuk pe/pbv/roe/roa/der/market_cap/revenue.
Gap-fill: Yahoo Finance (`FundamentalsProvider`) untuk field yang IDX tidak
punyai (enterprise_value, forward_pe, eps, peg, revenue_growth, net_income,
gross/operating_margin, current_ratio, free_cash_flow, dividend_yield/payout,
52w high/low, average_volume). Hasil dinormalisasi ke daftar field kanonik
16.4.3 (whitelist eksplisit) — `pbv` dari IDX, `pb` dipertahankan sebagai alias
supaya konsumen downstream (orchestrator) tidak putus. Field `beta` &
`book_value` sengaja tidak dikanonikkan (di-drop dari scope 16.4.3).
"""

from app.cache.memory_cache import MemoryCache
from app.providers import FundamentalsProvider, IdxProvider

_FUNDAMENTALS_TTL = 24 * 3600  # 24 jam (sesuai arah 16.4.5)

# Daftar field kanonik 16.4.3 (urutan sesuai dokumen). Setiap output selalu
# memuat semua key ini (None bila tidak ada sumber). Beta & Book Value tidak
# masuk — di-drop dari scope.
_CANONICAL_FIELDS = (
    "market_cap",
    "enterprise_value",
    "pe",
    "forward_pe",
    "pbv",
    "peg",
    "eps",
    "roe",
    "roa",
    "revenue",
    "revenue_growth",
    "net_income",
    "gross_margin",
    "operating_margin",
    "debt_to_equity",
    "current_ratio",
    "free_cash_flow",
    "dividend_yield",
    "dividend_payout_ratio",
    "week_52_high",
    "week_52_low",
    "average_volume",
    "shares_outstanding",
)

# Alias sumber → key kanonik. Nilai pertama yang tidak None (IDX diprioritaskan
# karena dicek lebih dulu) yang dipakai.
_ALIASES = {
    "pbv": ("pbv", "pb"),
    "week_52_high": ("fifty_two_week_high",),
    "week_52_low": ("fifty_two_week_low",),
    "average_volume": ("avg_volume_3m", "avg_volume_10d"),
}


def _pick(canonical: str, *sources: dict):
    """Ambil nilai kanonik dari sumber (IDX dulu, lalu Yahoo). None bila kosong."""
    keys = _ALIASES.get(canonical, (canonical,))
    for src in sources:
        for k in keys:
            v = src.get(k)
            if v is not None:
                return v
    return None


def _merge_fundamentals(idx: dict, yf: dict) -> dict:
    """Gabung IDX (primary) + Yahoo (gap-fill) → dict field kanonik 16.4.3.

    IDX menang untuk field yang ia punya; Yahoo mengisi sisanya. `pb`
    dipertahankan sebagai alias `pbv` untuk kompatibilitas downstream.
    `net_income` di-estimasi dari revenue × net_margin bila Yahoo tak memberi.
    """
    merged = {f: _pick(f, idx, yf) for f in _CANONICAL_FIELDS}

    # ponytail: net_income estimasi revenue*net_margin (IDX hanya punya margin),
    # bukan angka GAAP presisi — cukup untuk konsumsi AI awal.
    if merged["net_income"] is None:
        rev, npm = merged["revenue"], idx.get("net_margin")
        if rev is not None and npm is not None:
            merged["net_income"] = rev * (npm / 100 if abs(npm) > 1 else npm)

    merged["pb"] = merged["pbv"]  # alias kompatibilitas downstream
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
        merged = _merge_fundamentals(idx, yf)
        if idx.get("error"):
            merged["source"] = "yahoo"
        await self._cache.set(key, merged)
        return merged

    async def _safe_yahoo(self, symbol: str) -> dict:
        try:
            return await self._provider.fetch_fundamentals(symbol)
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}
