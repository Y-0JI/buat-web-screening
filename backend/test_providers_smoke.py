"""Smoke test Data Layer (tanpa framework — jalan via `python3 test_providers_smoke.py`).

Cek:
1. Semua provider & repository terimport tanpa error (termasuk wiring IDX).
2. Repository profile/fundamental/price sudah terhubung ke IdxProvider.
3. IdxProvider tetap aman saat jaringan gagal: tidak raise, kembalikan dict
   `error` (profile/fundamental) atau (None, False) (price).
4. RssProvider terdaftar.
"""

import asyncio
import sys

import app.providers as providers
import app.repositories as repositories
from app.providers.idx_provider import IdxProvider, _fetch_json
from app.providers.rss_provider import RssProvider
from app.repositories.fundamentals_repository import (
    _CANONICAL_FIELDS,
    _merge_fundamentals,
)
from app.repositories.news_repository import (
    NewsRepository,
    _dedupe,
    _normalize_item,
    _sort_items,
)

_NEWS_CANONICAL = (
    "headline",
    "publisher",
    "published_date",
    "summary",
    "url",
    "related_ticker",
    "source",
)


def test_imports():
    for name in (
        "StockPriceProvider",
        "CompanyProfileProvider",
        "NewsProvider",
        "FundamentalsProvider",
        "IdxProvider",
        "RssProvider",
    ):
        assert hasattr(providers, name), f"provider {name} tidak ter-export"


def test_repository_wiring():
    assert isinstance(repositories.company_profile_repository._idx_provider, IdxProvider)
    assert isinstance(repositories.fundamentals_repository._idx_provider, IdxProvider)
    assert isinstance(repositories.stock_price_repository._idx_provider, IdxProvider)


def test_profile_endpoint_wiring():
    from app.routers.stock import router as stock_router

    paths = [r.path for r in stock_router.routes]
    assert "/api/stock/{ticker}/profile" in paths, paths


def test_fundamentals_endpoint_wiring():
    from app.routers.stock import router as stock_router

    paths = [r.path for r in stock_router.routes]
    assert "/api/stock/{ticker}/fundamentals" in paths, paths


def test_fundamentals_canonical_merge():
    """16.4.3: _merge_fundamentals selalu keluarkan daftar field kanonik.

    IDX (primary) menang untuk field yang ia punya; Yahoo isi sisanya. Beta &
    book_value TIDAK boleh muncul (di-drop). `pb` = alias `pbv`. net_income
    di-estimasi dari revenue*net_margin bila Yahoo tak beri.
    """
    idx = {
        "market_cap": 100, "pe": 10, "pbv": 2, "roe": 0.15, "roa": 0.08,
        "revenue": 1000, "net_margin": 20, "debt_to_equity": 0.5,
        "shares_outstanding": 500, "source": "idx", "fetched_at": "t0",
    }
    yf = {
        "enterprise_value": 120, "forward_pe": 9, "eps": 5, "peg": 1.2,
        "revenue_growth": 0.1, "gross_margin": 0.4, "operating_margin": 0.25,
        "current_ratio": 1.5, "free_cash_flow": 300, "dividend_yield": 0.03,
        "dividend_payout_ratio": 0.4, "fifty_two_week_high": 200,
        "fifty_two_week_low": 80, "avg_volume_3m": 12345, "beta": 1.1,
        "source": "yahoo", "fetched_at": "t1",
    }
    out = _merge_fundamentals(idx, yf)
    for f in _CANONICAL_FIELDS:
        assert f in out, f"field kanonik {f} hilang"
    assert "beta" not in out and "book_value" not in out, out
    assert out["market_cap"] == 100  # IDX menang
    assert out["enterprise_value"] == 120  # Yahoo isi
    assert out["pb"] == out["pbv"] == 2  # alias
    assert out["week_52_high"] == 200 and out["average_volume"] == 12345
    assert out["net_income"] == 200  # 1000 * 20%
    assert out["source"] == "idx+yahoo"


async def _test_profile_fields():
    """Profile IDX (langkah 16.4.2): online → field lengkap + employees/logo None.
    Offline → tetap dict aman dengan name/symbol + error (tidak raise)."""
    provider = IdxProvider()
    prof = await provider.fetch_company_profile("BBCA")
    assert isinstance(prof, dict) and prof.get("symbol") == "BBCA", prof
    if not prof.get("error"):
        for key in ("name", "sector", "industry", "website",
                    "business_summary", "listing_date", "market_segment",
                    "employees", "logo"):
            assert key in prof, f"field {key} hilang dari profile"
        assert prof["employees"] is None
        assert prof["logo"] is None


async def _test_idx_fallback():
    provider = IdxProvider()

    async def _boom(*a, **k):
        raise RuntimeError("simulasi offline")

    orig = providers.idx_provider._fetch_json
    providers.idx_provider._fetch_json = _boom
    try:
        prof = await provider.fetch_company_profile("BBCA")
        assert isinstance(prof, dict) and "name" in prof, prof
        assert "error" in prof, "profile harus catat error saat offline"

        fund = await provider.fetch_fundamentals("BBCA")
        assert isinstance(fund, dict) and "error" in fund, fund

        df, sim = await provider.fetch_daily_price("BBCA")
        assert df is None and sim is False, (df, sim)
    finally:
        providers.idx_provider._fetch_json = orig


async def _test_fundamentals_repo():
    """Repo fundamental: online → dict field kanonik lengkap. Offline → dict
    aman ber-key `error` (tidak raise)."""
    repo = repositories.fundamentals_repository
    result = await repo.get_fundamentals("BBCA")
    assert isinstance(result, dict), result
    if not result.get("error"):
        for f in _CANONICAL_FIELDS:
            assert f in result, f"field kanonik {f} hilang dari hasil repo"
        assert "beta" not in result and "book_value" not in result, result
        assert "pb" in result, "alias pb harus ada"


def test_news_repo_wiring():
    """16.4.4: repository berita agregasi 3 sumber (IDX primary + Yahoo + RSS)."""
    from app.providers import NewsProvider, RssProvider

    repo = repositories.news_repository
    assert isinstance(repo._idx_provider, IdxProvider)
    assert isinstance(repo._provider, NewsProvider)
    assert isinstance(repo._rss_provider, RssProvider)


def test_news_normalize_fields():
    """Normalisasi Yahoo & RSS → 7 field kanonik; related_ticker & source
    selalu terisi konsisten (Review #2 & #4)."""
    yahoo_raw = {"title": "Judul Yahoo", "publisher": "Reuters",
                 "link": "https://y.com/a", "published": "2026-01-02", "summary": "s"}
    rss_raw = {"title": "Judul RSS", "publisher": "investor.id",
               "link": "https://g.com/b", "published": "Wed, 01 Jul 2026 07:00:00 GMT",
               "summary": "d", "related_ticker": "ZZZZ"}
    y = _normalize_item(yahoo_raw, "Yahoo", "BBCA")
    r = _normalize_item(rss_raw, "Google RSS", "BBCA")
    for item, src in ((y, "Yahoo"), (r, "Google RSS")):
        for f in _NEWS_CANONICAL:
            assert f in item, f"field {f} hilang"
        assert item["related_ticker"] == "BBCA", item
        assert item["source"] == src, item
    assert y["headline"] == "Judul Yahoo" and y["url"] == "https://y.com/a"
    assert r["published_date"].startswith("Wed"), r


def test_news_dedupe_and_sort():
    """Dedupe lintas-sumber (headline sama, url beda) → 1 item; urut terbaru."""
    items = [
        _normalize_item({"title": "Laba BBCA Naik!", "link": "https://idx/a",
                         "published": "2026-01-01"}, "IDX", "BBCA"),
        _normalize_item({"title": "laba bbca naik", "link": "https://yahoo/z",
                         "published": "2026-01-01"}, "Yahoo", "BBCA"),
        _normalize_item({"title": "Berita Lama", "link": "https://g/c",
                         "published": "2025-06-01"}, "Google RSS", "BBCA"),
    ]
    deduped = _dedupe(items)
    assert len(deduped) == 2, deduped
    assert deduped[0]["source"] == "IDX", "item pertama (IDX) menang saat dedupe"
    ordered = _sort_items(deduped)
    assert ordered[0]["headline"] == "Laba BBCA Naik!", ordered
    assert ordered[-1]["headline"] == "Berita Lama", ordered


async def _test_news_fallback():
    """Semua sumber gagal → repository tidak raise, kembalikan dict aman."""
    class _BoomIdx:
        async def fetch_company_announcements(self, *a, **k):
            raise RuntimeError("idx offline")

    class _BoomYahoo:
        async def fetch_news(self, *a, **k):
            raise RuntimeError("yahoo offline")

    class _BoomRss:
        async def fetch_rss(self, *a, **k):
            raise RuntimeError("rss offline")

    repo = NewsRepository(provider=_BoomYahoo(), idx_provider=_BoomIdx(),
                          rss_provider=_BoomRss())
    result = await repo.get_news("BBCA", limit=5)
    assert isinstance(result, dict) and "error" in result, result


async def _test_news_primary_and_order():
    """Provider palsu: IDX primary sukses + Yahoo/RSS kosong → hasil dari IDX,
    field kanonik lengkap, terurut terbaru dulu, tanpa duplikat."""
    class _FakeIdx:
        async def fetch_company_announcements(self, symbol, limit=10):
            return {"items": [
                {"headline": "Baru", "publisher": "IDX", "url": "https://idx/1",
                 "published_date": "2026-02-02T10:00:00", "summary": ""},
                {"headline": "Lama", "publisher": "IDX", "url": "https://idx/2",
                 "published_date": "2026-01-01T10:00:00", "summary": ""},
                {"headline": "Baru", "publisher": "IDX", "url": "https://idx/3",
                 "published_date": "2026-02-02T10:00:00", "summary": ""},
            ], "fetched_at": "t"}

    class _EmptyYahoo:
        async def fetch_news(self, *a, **k):
            return {"items": [], "fetched_at": "t"}

    class _EmptyRss:
        async def fetch_rss(self, *a, **k):
            return {"items": [], "fetched_at": "t"}

    repo = NewsRepository(provider=_EmptyYahoo(), idx_provider=_FakeIdx(),
                          rss_provider=_EmptyRss())
    result = await repo.get_news("BBCA", limit=10)
    assert not result.get("error"), result
    items = result["items"]
    assert len(items) == 2, f"dedupe gagal: {items}"
    assert items[0]["headline"] == "Baru" and items[1]["headline"] == "Lama"
    for it in items:
        for f in _NEWS_CANONICAL:
            assert f in it, f"field {f} hilang"
        assert it["related_ticker"] == "BBCA" and it["source"] == "IDX"


def main():
    test_imports()
    test_repository_wiring()
    test_profile_endpoint_wiring()
    test_fundamentals_endpoint_wiring()
    test_fundamentals_canonical_merge()
    test_news_repo_wiring()
    test_news_normalize_fields()
    test_news_dedupe_and_sort()
    asyncio.run(_test_idx_fallback())
    asyncio.run(_test_profile_fields())
    asyncio.run(_test_fundamentals_repo())
    asyncio.run(_test_news_fallback())
    asyncio.run(_test_news_primary_and_order())
    print("OK: semua smoke test lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
