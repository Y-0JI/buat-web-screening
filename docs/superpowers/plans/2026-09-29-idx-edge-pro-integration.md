# Integrasi IDX Edge PRO sebagai Sumber Data — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memakai REST API IDX Edge PRO (`stock.arjum.com`) sebagai sumber data utama untuk harga/history, verifikasi ticker, sync daftar ticker, dan broker summary, tanpa mengubah kontrak yang dikonsumsi scoring/UI.

**Architecture:** Tambah satu adapter provider (`IdxEdgeProvider`) sebagai satu-satunya klien HTTP ke IDX Edge PRO. Repository lama tetap menjadi seam: `StockPriceRepository`, `app/data/ticker_sync.py`, dan `MarketIntelligenceRepository` memanggil adapter baru; provider lama dipertahankan hanya untuk celah (berita, profil detail, rasio fundamental, earnings/analyst). Screening memakai endpoint `/api/screener/latest` sebagai pre-filter agar muat kuota 1000/hari.

**Tech Stack:** Python 3.12, FastAPI, httpx (AsyncClient + MockTransport untuk test), pandas, SQLAlchemy(async), SQLite. Test berupa script standalone (tanpa pytest), dijalankan `./.venv/bin/python test_xxx.py`.

## Global Constraints

- Base URL: `https://stock.arjum.com`. Auth: header `X-API-Key`. Kuota: 1000 request/hari.
- `market-cap` `per_page` maksimum 50.
- Format DataFrame harga yang diwajibkan scoring/indicators: index `DatetimeIndex` terurut naik, kolom `Open, High, Low, Close, Volume` (kapitalisasi awal).
- Provider IDX Edge PRO **tidak boleh raise** ke layer atas: kembalikan `None`/`{}`/`[]` saat gagal.
- Jalur IDX Edge PRO tidak memakai mock; `is_simulated=False`.
- Kill-switch: bila `IDX_EDGE_API_KEY` kosong, jalur harga/verify/ticker-sync kembali memakai provider lama.
- Jangan commit `.env` (sudah di-gitignore). Hanya `.env.example` yang di-commit.
- Test mengikuti gaya repo: script standalone `backend/test_*.py` dengan `main()` + `asyncio.run`, dijalankan dengan `./.venv/bin/python`.

---

### Task 1: Config & dependency

**Files:**
- Modify: `backend/app/config.py` (tambah 4 field di class `Settings`)
- Modify: `backend/.env.example`
- Modify: `backend/requirements.txt`

**Interfaces:**
- Produces: `settings.idx_edge_api_key: str`, `settings.idx_edge_base_url: str`, `settings.idx_edge_timeout: int`, `settings.idx_edge_daily_quota: int`

- [ ] **Step 1: Tambah field config**

Di `backend/app/config.py`, tepat setelah baris `sectors_api_key: str = ""` tambahkan:

```python
    idx_edge_api_key: str = ""
    idx_edge_base_url: str = "https://stock.arjum.com"
    idx_edge_timeout: int = 20
    idx_edge_daily_quota: int = 1000
```

- [ ] **Step 2: Tambah ke `.env.example`**

Di `backend/.env.example`, setelah baris `SECTORS_API_KEY=` (bila ada; jika tidak, setelah `FRONTEND_URL=...`) tambahkan:

```
IDX_EDGE_API_KEY=
IDX_EDGE_BASE_URL=https://stock.arjum.com
IDX_EDGE_TIMEOUT=20
IDX_EDGE_DAILY_QUOTA=1000
```

- [ ] **Step 3: Tambah dependency httpx eksplisit**

Di `backend/requirements.txt` tambahkan satu baris:

```
httpx>=0.27
```

- [ ] **Step 4: Verifikasi config terbaca**

Run:
```bash
cd backend && ./.venv/bin/python -c "from app.config import settings; print(settings.idx_edge_base_url, settings.idx_edge_daily_quota)"
```
Expected: `https://stock.arjum.com 1000`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/.env.example backend/requirements.txt
git commit -m "feat: config & dependency IDX Edge PRO"
```

---

### Task 2: Provider — client, kuota, health, search

**Files:**
- Create: `backend/app/providers/idx_edge_provider.py`
- Create: `backend/test_idx_edge_provider.py`

**Interfaces:**
- Consumes: `settings.idx_edge_*`, `request_scheduler.acquire()`
- Produces:
  - `class IdxEdgeProvider(client: httpx.AsyncClient | None = None)`
  - `.enabled -> bool`
  - `async .health() -> dict | None`
  - `async .search(q: str) -> list[dict]` (selalu list)

- [ ] **Step 1: Write the failing test**

Buat `backend/test_idx_edge_provider.py`:

```python
"""Test unit IdxEdgeProvider (tanpa jaringan, pakai httpx.MockTransport).

Jalan: ./.venv/bin/python test_idx_edge_provider.py
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider


def _client(handler):
    return httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://stock.arjum.com",
    )


def _with_key(key="test-key"):
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = key
    return old


def test_enabled_flag():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = ""
    assert IdxEdgeProvider().enabled is False
    settings.idx_edge_api_key = "abc"
    assert IdxEdgeProvider().enabled is True
    settings.idx_edge_api_key = old


async def _test_search():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        return httpx.Response(200, json=[{"stock_code": "BBCA", "stock_name": "Bank Central Asia Tbk."}])

    p = IdxEdgeProvider(client=_client(handler))
    try:
        res = await p.search("BBCA")
        assert res == [{"stock_code": "BBCA", "stock_name": "Bank Central Asia Tbk."}], res
        assert seen["key"] == "test-key", seen
        assert "/api/search" in seen["url"] and "q=BBCA" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


async def _test_search_error_returns_empty():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "down"})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        assert await p.search("BBCA") == []
    finally:
        settings.idx_edge_api_key = old


async def _test_disabled_returns_none():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = ""
    try:
        p = IdxEdgeProvider()
        assert await p.search("BBCA") == []
        assert await p.health() is None
    finally:
        settings.idx_edge_api_key = old


def main():
    test_enabled_flag()
    asyncio.run(_test_search())
    asyncio.run(_test_search_error_returns_empty())
    asyncio.run(_test_disabled_returns_none())
    print("OK: test_idx_edge_provider (bagian 1) lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_idx_edge_provider.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.providers.idx_edge_provider'`

- [ ] **Step 3: Write minimal implementation**

Buat `backend/app/providers/idx_edge_provider.py`:

```python
"""Provider IDX Edge PRO (stock.arjum.com) — satu-satunya klien REST API-nya.

Mengambil data mentah dari IDX Edge PRO. Tidak ada business logic di sini dan
tidak pernah raise ke caller: setiap kegagalan (timeout, 401, 429, 5xx) ditangani
aman dan mengembalikan None / list kosong, konsisten dengan provider lain.

Auth via header `X-API-Key` (dari settings). Semua request melewati
`request_scheduler` (rate-limit global) dan dihitung terhadap kuota harian
`idx_edge_daily_quota` supaya tidak melebihi batas layanan.
"""

import logging
from datetime import date
from typing import Any, Optional

import httpx

from app.config import settings
from app.providers.scheduler import request_scheduler

logger = logging.getLogger(__name__)

_QUOTA_WARN_RATIO = 0.9


class IdxEdgeProvider:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self._calls_today = 0
        self._quota_day = date.today()

    @property
    def enabled(self) -> bool:
        return bool(settings.idx_edge_api_key)

    def _roll_quota(self) -> None:
        today = date.today()
        if today != self._quota_day:
            self._quota_day = today
            self._calls_today = 0

    async def _get_json(
        self, path: str, params: Optional[dict] = None, require_key: bool = True
    ) -> Any:
        if require_key and not self.enabled:
            return None
        self._roll_quota()
        budget = settings.idx_edge_daily_quota
        if self._calls_today >= budget:
            logger.warning("Kuota IDX Edge PRO harian habis — request dilewati: %s", path)
            return None
        if budget and self._calls_today >= budget * _QUOTA_WARN_RATIO:
            logger.warning(
                "Kuota IDX Edge PRO hampir habis: %d/%d", self._calls_today, budget
            )

        await request_scheduler.acquire()
        url = f"{settings.idx_edge_base_url}{path}"
        headers = {"Accept": "application/json"}
        if require_key:
            headers["X-API-Key"] = settings.idx_edge_api_key
        try:
            if self._client is not None:
                resp = await self._client.get(
                    url, params=params, headers=headers,
                    timeout=settings.idx_edge_timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=settings.idx_edge_timeout) as client:
                    resp = await client.get(url, params=params, headers=headers)
            self._calls_today += 1
            if resp.status_code == 401:
                logger.error("IDX Edge PRO: API key tidak valid/absen (401) di %s", path)
                return None
            if resp.status_code == 429:
                logger.warning("IDX Edge PRO: rate limit (429) di %s", path)
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001 — kegagalan tidak fatal
            logger.warning("IDX Edge PRO error %s: %s", path, e)
            return None

    async def health(self) -> Optional[dict]:
        data = await self._get_json("/api/health", require_key=False)
        return data if isinstance(data, dict) else None

    async def search(self, q: str) -> list[dict]:
        data = await self._get_json("/api/search", {"q": q})
        return data if isinstance(data, list) else []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_idx_edge_provider.py`
Expected: `OK: test_idx_edge_provider (bagian 1) lolos`

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/idx_edge_provider.py backend/test_idx_edge_provider.py
git commit -m "feat: provider IDX Edge PRO (client, kuota, health, search)"
```

---

### Task 3: Provider — history & mapping DataFrame

**Files:**
- Modify: `backend/app/providers/idx_edge_provider.py`
- Modify: `backend/test_idx_edge_provider.py`

**Interfaces:**
- Produces:
  - `rows_to_price_df(rows: list[dict] | None) -> pd.DataFrame | None` (index `DatetimeIndex` naik, kolom `Open/High/Low/Close/Volume`)
  - `async IdxEdgeProvider.fetch_history(code, frame="daily", limit=160) -> list[dict] | None`

- [ ] **Step 1: Write the failing test**

Tambahkan ke `backend/test_idx_edge_provider.py` (ubah import dan `main()`):

Ubah baris import:
```python
from app.providers.idx_edge_provider import IdxEdgeProvider, rows_to_price_df
```

Tambahkan fungsi berikut sebelum `def main()`:

```python
def test_rows_to_price_df():
    rows = [
        {"date": "2026-09-29", "open": 6100, "high": 6200, "low": 6050,
         "close": 6150, "volume": 150000000, "f_buy": 1, "f_sell": 2},
        {"date": "2026-09-28", "open": 6200, "high": 6250, "low": 6100,
         "close": 6175, "volume": 120000000},
    ]
    df = rows_to_price_df(rows)
    assert df is not None
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"], list(df.columns)
    assert df.index.is_monotonic_increasing
    assert float(df["Close"].iloc[-1]) == 6150.0
    assert float(df["Volume"].iloc[0]) == 120000000.0
    assert rows_to_price_df([]) is None
    assert rows_to_price_df(None) is None


async def _test_fetch_history():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={
            "stock_code": "BBCA", "frame": "daily",
            "rows": [{"date": "2026-09-29", "open": 6100, "high": 6200,
                      "low": 6050, "close": 6150, "volume": 150000000}],
        })

    p = IdxEdgeProvider(client=_client(handler))
    try:
        rows = await p.fetch_history("BBCA", limit=120)
        assert isinstance(rows, list) and len(rows) == 1, rows
        assert "/api/history/BBCA" in seen["url"] and "limit=120" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


async def _test_fetch_history_error():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        assert await p.fetch_history("BBCA") is None
    finally:
        settings.idx_edge_api_key = old
```

Ubah `main()` menjadi:
```python
def main():
    test_enabled_flag()
    test_rows_to_price_df()
    asyncio.run(_test_search())
    asyncio.run(_test_search_error_returns_empty())
    asyncio.run(_test_disabled_returns_none())
    asyncio.run(_test_fetch_history())
    asyncio.run(_test_fetch_history_error())
    print("OK: test_idx_edge_provider (bagian 2) lolos")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_idx_edge_provider.py`
Expected: FAIL — `ImportError: cannot import name 'rows_to_price_df'`

- [ ] **Step 3: Write minimal implementation**

Di `backend/app/providers/idx_edge_provider.py`, ubah import `pandas`:

```python
import pandas as pd
```

Tambahkan fungsi modul tepat setelah `_QUOTA_WARN_RATIO = 0.9`:

```python
def rows_to_price_df(rows: Optional[list[dict]]) -> Optional[pd.DataFrame]:
    """Konversi `rows` respons /api/history → DataFrame siap scoring.

    Index = DatetimeIndex terurut naik; kolom = Open/High/Low/Close/Volume
    (kapitalisasi awal, sama seperti `_flatten_columns`).
    """
    if not rows:
        return None
    records = []
    for r in rows:
        try:
            records.append({
                "Date": pd.to_datetime(r.get("date")),
                "Open": float(r.get("open") or 0),
                "High": float(r.get("high") or 0),
                "Low": float(r.get("low") or 0),
                "Close": float(r.get("close") or 0),
                "Volume": float(r.get("volume") or 0),
            })
        except (TypeError, ValueError):
            continue
    if not records:
        return None
    return pd.DataFrame(records).sort_values("Date").set_index("Date")
```

Tambahkan method `fetch_history` di dalam class `IdxEdgeProvider`, setelah `search`:

```python
    async def fetch_history(
        self, code: str, frame: str = "daily", limit: int = 160
    ) -> Optional[list[dict]]:
        data = await self._get_json(
            f"/api/history/{code}", {"frame": frame, "limit": limit}
        )
        if isinstance(data, dict):
            return data.get("rows") or []
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_idx_edge_provider.py`
Expected: `OK: test_idx_edge_provider (bagian 2) lolos`

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/idx_edge_provider.py backend/test_idx_edge_provider.py
git commit -m "feat: IDX Edge PRO history + mapping DataFrame"
```

---

### Task 4: Provider — market-cap, screener, broker-summary

**Files:**
- Modify: `backend/app/providers/idx_edge_provider.py`
- Modify: `backend/test_idx_edge_provider.py`

**Interfaces:**
- Produces:
  - `async .fetch_market_cap(page=1, per_page=50, codes=None) -> dict | None`
  - `async .fetch_screener() -> dict | None`
  - `async .fetch_broker_summary(code, start_date=None, end_date=None, flow="all", net=False, broker_limit=None) -> dict | None`

- [ ] **Step 1: Write the failing test**

Tambahkan sebelum `def main()` di `backend/test_idx_edge_provider.py`:

```python
async def _test_market_cap():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"total": 963, "page": 1, "per_page": 50,
                                         "total_pages": 20, "data": [{"code": "BBCA"}]})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = await p.fetch_market_cap(page=2, per_page=50)
        assert data["total"] == 963 and data["data"][0]["code"] == "BBCA", data
        assert "/api/market-cap" in seen["url"] and "page=2" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old


async def _test_screener():
    old = _with_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"date": "2026-09-29",
                                         "rows": [{"stock_code": "ASHA"}]})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = await p.fetch_screener()
        assert data["rows"][0]["stock_code"] == "ASHA", data
    finally:
        settings.idx_edge_api_key = old


async def _test_broker_summary():
    old = _with_key()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"stock_code": "BBCA", "brokers": [
            {"broker_code": "ZP", "broker_name": "Maybank", "bval": 202, "bvol": 10,
             "bfrq": 5, "sval": 0, "svol": 0, "nval": 202, "nvol": 10},
        ]})

    p = IdxEdgeProvider(client=_client(handler))
    try:
        data = await p.fetch_broker_summary("BBCA", broker_limit=20)
        assert data["brokers"][0]["broker_code"] == "ZP", data
        assert "/api/broker-summary/BBCA" in seen["url"] and "broker_limit=20" in seen["url"], seen
    finally:
        settings.idx_edge_api_key = old
```

Ubah `main()` menjadi:
```python
def main():
    test_enabled_flag()
    test_rows_to_price_df()
    asyncio.run(_test_search())
    asyncio.run(_test_search_error_returns_empty())
    asyncio.run(_test_disabled_returns_none())
    asyncio.run(_test_fetch_history())
    asyncio.run(_test_fetch_history_error())
    asyncio.run(_test_market_cap())
    asyncio.run(_test_screener())
    asyncio.run(_test_broker_summary())
    print("OK: test_idx_edge_provider (lengkap) lolos")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_idx_edge_provider.py`
Expected: FAIL — `AttributeError: 'IdxEdgeProvider' object has no attribute 'fetch_market_cap'`

- [ ] **Step 3: Write minimal implementation**

Tambahkan tiga method berikut di dalam class `IdxEdgeProvider` setelah `fetch_history`:

```python
    async def fetch_market_cap(
        self, page: int = 1, per_page: int = 50, codes: Optional[list[str]] = None
    ) -> Optional[dict]:
        params: dict = {"page": page, "per_page": per_page}
        if codes:
            params["codes"] = ",".join(codes)
        data = await self._get_json("/api/market-cap", params)
        return data if isinstance(data, dict) else None

    async def fetch_screener(self) -> Optional[dict]:
        data = await self._get_json("/api/screener/latest")
        return data if isinstance(data, dict) else None

    async def fetch_broker_summary(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        flow: str = "all",
        net: bool = False,
        broker_limit: Optional[int] = None,
    ) -> Optional[dict]:
        params: dict = {"net": str(net).lower()}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if flow != "all":
            params["flow"] = flow
        if broker_limit:
            params["broker_limit"] = broker_limit
        data = await self._get_json(f"/api/broker-summary/{code}", params)
        return data if isinstance(data, dict) else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_idx_edge_provider.py`
Expected: `OK: test_idx_edge_provider (lengkap) lolos`

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/idx_edge_provider.py backend/test_idx_edge_provider.py
git commit -m "feat: IDX Edge PRO market-cap, screener, broker-summary"
```

---

### Task 5: Export provider

**Files:**
- Modify: `backend/app/providers/__init__.py`
- Modify: `backend/test_providers_smoke.py` (fungsi `test_imports`)

**Interfaces:**
- Produces: `app.providers.IdxEdgeProvider`

- [ ] **Step 1: Write the failing test**

Di `backend/test_providers_smoke.py`, ubah `test_imports` agar menyertakan `"IdxEdgeProvider"`:

```python
def test_imports():
    for name in (
        "StockPriceProvider",
        "CompanyProfileProvider",
        "NewsProvider",
        "FundamentalsProvider",
        "IdxProvider",
        "RssProvider",
        "IdxEdgeProvider",
    ):
        assert hasattr(providers, name), f"provider {name} tidak ter-export"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_providers_smoke.py`
Expected: FAIL — `provider IdxEdgeProvider tidak ter-export`

- [ ] **Step 3: Write minimal implementation**

Di `backend/app/providers/__init__.py`, tambahkan import dan `__all__`:

```python
from app.providers.idx_edge_provider import IdxEdgeProvider
```
```python
    "IdxProvider",
    "IdxEdgeProvider",
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_providers_smoke.py`
Expected: `OK: semua smoke test lolos`

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/__init__.py backend/test_providers_smoke.py
git commit -m "feat: export IdxEdgeProvider"
```

---

### Task 6: Wire harga/history/verify ke IDX Edge PRO

**Files:**
- Modify: `backend/app/repositories/stock_price_repository.py`
- Modify: `backend/test_providers_smoke.py` (tambah wiring assert)

**Interfaces:**
- Consumes: `IdxEdgeProvider.enabled`, `.fetch_history`, `.search`, `rows_to_price_df`
- Produces:
  - `StockPriceRepository(provider=None, idx_provider=None, edge_provider=None)`
  - `async ._known_ticker(clean) -> bool` (modul-level, dapat dimonkeypatch test)
  - `get_price`/`get_history` tetap `-> tuple[pd.DataFrame | None, bool]`; `verify_ticker` tetap `-> bool`

- [ ] **Step 1: Write the failing test**

Tambahkan ke `backend/test_providers_smoke.py` sebelum `def main()`:

```python
def test_stock_price_edge_wiring():
    import httpx
    from app.config import settings
    from app.providers.idx_edge_provider import IdxEdgeProvider
    from app.repositories.stock_price_repository import StockPriceRepository

    repo = StockPriceRepository()
    assert isinstance(repo._edge, IdxEdgeProvider), "repo harus punya _edge"


async def _test_stock_price_uses_edge():
    import httpx
    from app.config import settings
    from app.providers.idx_edge_provider import IdxEdgeProvider
    from app.repositories.stock_price_repository import StockPriceRepository

    old_key = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        if "/api/history/" in str(request.url):
            return httpx.Response(200, json={"rows": [
                {"date": "2026-09-28", "open": 6200, "high": 6250, "low": 6100,
                 "close": 6175, "volume": 120000000},
                {"date": "2026-09-29", "open": 6100, "high": 6200, "low": 6050,
                 "close": 6150, "volume": 150000000},
            ]})
        if "/api/search" in str(request.url):
            return httpx.Response(200, json=[{"stock_code": "BBCA"}])
        return httpx.Response(404, json={})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    repo = StockPriceRepository(edge_provider=edge)
    try:
        df, sim = await repo.get_history("BBCA", period="1mo")
        assert df is not None and sim is False, (df, sim)
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
        assert float(df["Close"].iloc[-1]) == 6150.0
        assert await repo.verify_ticker("BBCA") is True
    finally:
        settings.idx_edge_api_key = old_key
```

Ubah `main()` agar memanggil keduanya (sisipkan sebelum `asyncio.run(_test_idx_fallback())`):
```python
    test_stock_price_edge_wiring()
    asyncio.run(_test_stock_price_uses_edge())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_providers_smoke.py`
Expected: FAIL — `StockPriceRepository.__init__() got an unexpected keyword argument 'edge_provider'`

- [ ] **Step 3: Write minimal implementation**

Ganti seluruh isi `backend/app/repositories/stock_price_repository.py` menjadi:

```python
"""Repository Stock Price — satu pintu akses data harga & verifikasi ticker.

Primary: IDX Edge PRO (`IdxEdgeProvider`, REST API) saat `IDX_EDGE_API_KEY` diisi.
Kill-switch: bila key kosong, kembali memakai IDX scraping + Yahoo Finance.
Tidak ada business logic di sini; hanya orkestrasi sumber + cache.
"""

import logging

import pandas as pd

from app.cache.service import cache_service
from app.config import settings
from app.providers import IdxProvider, StockPriceProvider
from app.providers.idx_edge_provider import IdxEdgeProvider, rows_to_price_df

logger = logging.getLogger(__name__)

_PRICE_CATEGORY = "price"
_VERIFY_CATEGORY = "verify"

_PERIOD_LIMITS = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
}


def _period_to_limit(period: str) -> int:
    for key, limit in _PERIOD_LIMITS.items():
        if period.startswith(key):
            return limit
    return 252


async def _known_ticker(clean: str) -> bool:
    """Fallback verifikasi: cek daftar ticker terdaftar (DB → whitelist statis)."""
    try:
        from app.data.ticker_sync import get_listed_tickers

        return clean in {t.upper() for t in await get_listed_tickers()}
    except Exception:  # noqa: BLE001
        return False


class StockPriceRepository:
    def __init__(
        self,
        provider: StockPriceProvider | None = None,
        idx_provider: IdxProvider | None = None,
        edge_provider: IdxEdgeProvider | None = None,
    ):
        self._provider = provider or StockPriceProvider()
        self._idx_provider = idx_provider or IdxProvider()
        self._edge = edge_provider or IdxEdgeProvider()

    async def get_price(
        self, symbol: str, fast_fail: bool = False
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"price:{symbol.upper().replace('.JK', '')}:{fast_fail}"
        cached = await cache_service.get(_PRICE_CATEGORY, key)
        if cached is not None:
            return cached
        df, sim = await self._fetch(symbol, _period_to_limit(settings.yfinance_period))
        await cache_service.set(_PRICE_CATEGORY, key, (df, sim))
        return df, sim

    async def get_history(
        self, symbol: str, period: str = "6mo"
    ) -> tuple[pd.DataFrame | None, bool]:
        key = f"history:{symbol.upper().replace('.JK', '')}:{period}"
        cached = await cache_service.get(_PRICE_CATEGORY, key)
        if cached is not None:
            return cached
        df, sim = await self._fetch(symbol, _period_to_limit(period))
        await cache_service.set(_PRICE_CATEGORY, key, (df, sim))
        return df, sim

    async def _fetch(
        self, symbol: str, limit: int
    ) -> tuple[pd.DataFrame | None, bool]:
        if self._edge.enabled:
            clean = symbol.upper().replace(".JK", "")
            rows = await self._edge.fetch_history(clean, limit=limit)
            return rows_to_price_df(rows), False
        df, sim = await self._idx_provider.fetch_daily_price(symbol, limit=limit)
        if df is None:
            df, sim = await self._provider.fetch_history(
                symbol, period=settings.yfinance_period
            )
        return df, sim

    async def verify_ticker(self, candidate: str) -> bool:
        key = candidate.upper().replace(".JK", "")
        cached = await cache_service.get(_VERIFY_CATEGORY, key)
        if cached is not None:
            return cached
        if self._edge.enabled:
            results = await self._edge.search(key)
            result = any(
                (r.get("stock_code") or "").upper() == key for r in results
            )
            if not result:
                result = await _known_ticker(key)
        else:
            result = await self._provider.verify_ticker(candidate)
        await cache_service.set(_VERIFY_CATEGORY, key, result)
        return result

    async def clear(self) -> None:
        await cache_service.clear(_PRICE_CATEGORY)
        await cache_service.clear(_VERIFY_CATEGORY)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_providers_smoke.py`
Expected: `OK: semua smoke test lolos`

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/stock_price_repository.py backend/test_providers_smoke.py
git commit -m "feat: harga/history/verify via IDX Edge PRO"
```

---

### Task 7: Sync daftar ticker via market-cap

**Files:**
- Modify: `backend/app/data/ticker_sync.py`

**Interfaces:**
- Consumes: `IdxEdgeProvider.enabled`, `.fetch_market_cap(page, per_page)`
- Produces: `_fetch_from_sources()` mengembalikan `list[{"ticker","company_name","sector"}]`; `fetch_and_store_tickers()` tidak berubah kontrak.

- [ ] **Step 1: Write the failing test**

Buat `backend/test_ticker_sync_edge.py`:

```python
"""Test sync daftar ticker via IDX Edge PRO (tanpa jaringan).

Jalan: ./.venv/bin/python test_ticker_sync_edge.py
"""

import asyncio
import sys

import httpx

import app.data.ticker_sync as ts
from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider


async def _test_fetch_from_sources_paginates():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(dict(request.url.params).get("page", "1"))
        if page == 1:
            return httpx.Response(200, json={
                "total": 2, "page": 1, "per_page": 50, "total_pages": 2,
                "data": [{"code": "BBCA", "name": "Bank Central Asia Tbk."}],
            })
        return httpx.Response(200, json={
            "total": 2, "page": 2, "per_page": 50, "total_pages": 2,
            "data": [{"code": "BBRI", "name": "Bank Rakyat Indonesia Tbk."}],
        })

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    orig = ts._edge_provider
    ts._edge_provider = lambda: edge
    try:
        out = await ts._fetch_from_sources()
        codes = sorted(r["ticker"] for r in out)
        assert codes == ["BBCA", "BBRI"], out
        assert out[0]["company_name"]
    finally:
        ts._edge_provider = orig
        settings.idx_edge_api_key = old


def main():
    asyncio.run(_test_fetch_from_sources_paginates())
    print("OK: test_ticker_sync_edge lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_ticker_sync_edge.py`
Expected: FAIL — `AttributeError: module 'app.data.ticker_sync' has no attribute '_edge_provider'`

- [ ] **Step 3: Write minimal implementation**

Di `backend/app/data/ticker_sync.py`:

(a) Ganti blok konstanta sumber (baris `SECTORS_API_KEY` s/d `SECTORS_HEADERS`) menjadi:

```python
def _edge_provider():
    """Pabrik provider IDX Edge PRO — dapat diganti pada test."""
    from app.providers.idx_edge_provider import IdxEdgeProvider

    return IdxEdgeProvider()
```

(b) Hapus fungsi `_fetch_sectors` dan `_fetch_idx`.

(c) Ganti fungsi `_fetch_from_sources` menjadi:

```python
async def _fetch_from_sources():
    provider = _edge_provider()
    if not provider.enabled:
        logger.warning("IDX_EDGE_API_KEY kosong — sync ticker dilewati")
        return []
    out: list[dict] = []
    page = 1
    while True:
        data = await provider.fetch_market_cap(page=page, per_page=50)
        if not data or not data.get("data"):
            break
        for row in data["data"]:
            code = str(row.get("code") or "").strip().upper()
            if code:
                out.append({
                    "ticker": code,
                    "company_name": row.get("name"),
                    "sector": None,
                })
        total_pages = data.get("total_pages") or page
        if page >= total_pages:
            break
        page += 1
    return out
```

(d) Karena `_fetch_sectors`/`_fetch_idx` dihapus, hapus juga import yang jadi tak terpakai:
- hapus baris `from curl_cffi import requests as curl_requests` (kecuali masih dipakai di tempat lain — cek: hanya di fungsi yang dihapus).
- biarkan import lain (`asyncio`, `logging`, `datetime`, `text`, `settings`, `get_session`, `SyncStatus`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_ticker_sync_edge.py`
Expected: `OK: test_ticker_sync_edge lolos`

- [ ] **Step 5: Cek tidak ada sisa referensi fungsi yang dihapus**

Run: `cd backend && grep -rn "_fetch_sectors\|_fetch_idx\|curl_requests" app/data/ticker_sync.py`
Expected: tidak ada output.

- [ ] **Step 6: Commit**

```bash
git add backend/app/data/ticker_sync.py backend/test_ticker_sync_edge.py
git commit -m "feat: sync daftar ticker via IDX Edge PRO market-cap"
```

---

### Task 8: Broker summary Market Intelligence per-ticker via IDX Edge PRO

**Files:**
- Modify: `backend/app/market_intelligence/repository.py`
- Modify: `backend/app/market_intelligence/service.py`

**Interfaces:**
- Consumes: `IdxEdgeProvider.enabled`, `.fetch_broker_summary(code, broker_limit)`
- Produces: `MarketIntelligenceRepository.get_broker_summary(ticker: str, limit: int = 20) -> list[dict]` dengan field `broker_code, broker_name, volume, value, frequency` (per-ticker).

- [ ] **Step 1: Write the failing test**

Buat `backend/test_mi_broker_edge.py`:

```python
"""Test broker summary MI dari IDX Edge PRO (tanpa jaringan).

Jalan: ./.venv/bin/python test_mi_broker_edge.py
"""

import asyncio
import sys

import httpx

from app.config import settings
from app.market_intelligence.repository import MarketIntelligenceRepository
from app.providers.idx_edge_provider import IdxEdgeProvider


async def _test_repo_broker_from_edge():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"stock_code": "BBCA", "brokers": [
            {"broker_code": "ZP", "broker_name": "Maybank", "bval": 100,
             "bvol": 10, "bfrq": 5, "sval": 0, "svol": 0, "nval": 100, "nvol": 10},
            {"broker_code": "AK", "broker_name": "UBS", "bval": 300,
             "bvol": 30, "bfrq": 8, "sval": 0, "svol": 0, "nval": 300, "nvol": 30},
        ]})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    repo = MarketIntelligenceRepository(edge_provider=edge)
    try:
        items = await repo.get_broker_summary("BBCA", limit=2)
        assert items[0]["broker_code"] == "AK", items  # urut value desc
        for f in ("broker_code", "broker_name", "volume", "value", "frequency"):
            assert f in items[0], (f, items[0])
    finally:
        settings.idx_edge_api_key = old


def main():
    asyncio.run(_test_repo_broker_from_edge())
    print("OK: test_mi_broker_edge lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_mi_broker_edge.py`
Expected: FAIL — `TypeError: MarketIntelligenceRepository.__init__() got an unexpected keyword argument 'edge_provider'`

- [ ] **Step 3: Write minimal implementation**

Di `backend/app/market_intelligence/repository.py`:

(a) Tambah import setelah import `MarketIntelligenceProvider`:

```python
from app.providers.idx_edge_provider import IdxEdgeProvider
```

(b) Ganti `__init__`:

```python
    def __init__(
        self,
        provider: Optional[MarketIntelligenceProvider] = None,
        edge_provider: Optional[IdxEdgeProvider] = None,
    ):
        self._provider = provider or MarketIntelligenceProvider()
        self._edge = edge_provider or IdxEdgeProvider()
```

(c) Ganti seluruh blok `# ---------- Broker Summary (market-wide) ----------` (method `get_broker_summary`) menjadi:

```python
    # ---------- Broker Summary (per-ticker, IDX Edge PRO) ----------

    async def get_broker_summary(
        self, ticker: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        code = ticker.upper().replace(".JK", "")
        key = f"{code}:{limit}"
        cached = await self._cached_or_none("broker_summary", key)
        if cached is not _MISS:
            return cached
        rows = await self._edge_broker(code, limit)
        if rows is None:
            rows = await self._legacy_broker_summary(limit)
        await self._store("broker_summary", key, rows)
        return rows

    async def _edge_broker(
        self, code: str, limit: int
    ) -> Optional[List[Dict[str, Any]]]:
        if not self._edge.enabled:
            return None
        data = await self._edge.fetch_broker_summary(code, broker_limit=limit)
        if not data:
            return None
        items = [
            {
                "broker_code": b.get("broker_code"),
                "broker_name": b.get("broker_name"),
                "volume": b.get("bvol"),
                "value": b.get("bval"),
                "frequency": b.get("bfrq"),
            }
            for b in data.get("brokers") or []
        ]
        items.sort(key=lambda x: abs(x.get("value") or 0), reverse=True)
        return items[:limit]

    async def _legacy_broker_summary(
        self, limit: int
    ) -> List[Dict[str, Any]]:
        pointer = await cache_service.get("broker_summary", "latest_date")
        rows: Optional[List[Dict[str, Any]]] = None
        if pointer is not None:
            rows = await cache_service.get("broker_summary", pointer)
        if rows is None:
            for i in range(_LOOKBACK_TRADING_DAYS):
                d = (date.today() - timedelta(days=i)).isoformat()
                fetched = await self._provider.fetch_broker_summary(d)
                if fetched:
                    rows = fetched
                    await cache_service.set("broker_summary", d, fetched)
                    await cache_service.set("broker_summary", "latest_date", d)
                    break
        if not rows:
            return []
        brokers = [models.normalize_broker(r) for r in rows]
        brokers.sort(key=lambda b: b.get("value") or 0, reverse=True)
        return brokers[:limit]
```

Catatan: `_legacy_broker_summary` memakai key cache `broker_summary:latest_date` dan `broker_summary:<date>`; method baru memakai key `broker_summary:<code>:<limit>`. Prefix kategori sama sehingga `clear()` tetap bekerja.

Di `backend/app/market_intelligence/service.py`, ubah baris panggilan broker di `asyncio.gather`:

```python
            self._repo.get_broker_summary(ticker),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_mi_broker_edge.py`
Expected: `OK: test_mi_broker_edge lolos`

- [ ] **Step 5: Jalankan test MI lama (regresi)**

Run: `cd backend && ./.venv/bin/python test_16_5_3_validation.py`
Expected: `OK ...` (lolos). Bila ada test yang memanggil `get_broker_summary()` tanpa argumen, perbarui pemanggilnya menjadi `get_broker_summary("BBCA")`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/market_intelligence/repository.py backend/app/market_intelligence/service.py backend/test_mi_broker_edge.py
git commit -m "feat: broker summary MI per-ticker via IDX Edge PRO"
```

---

### Task 9: Screening pre-filter via /api/screener/latest

**Files:**
- Modify: `backend/app/scheduler.py`

**Interfaces:**
- Consumes: `IdxEdgeProvider.enabled`, `.fetch_screener()`, `get_listed_tickers()`
- Produces: `async _get_scan_candidates() -> list[str]`; `run_batch_scan(mode)` memakai kandidat ini; bila kosong → keluar tanpa menyentuh cache.

- [ ] **Step 1: Write the failing test**

Buat `backend/test_scheduler_candidates.py`:

```python
"""Test pre-filter kandidat screening via IDX Edge PRO (tanpa jaringan).

Jalan: ./.venv/bin/python test_scheduler_candidates.py
"""

import asyncio
import sys

import httpx

import app.scheduler as sched
from app.config import settings
from app.providers.idx_edge_provider import IdxEdgeProvider


async def _test_candidates_from_screener():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rows": [
            {"stock_code": "ASHA"}, {"stock_code": "RAJA"},
        ]})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    orig = sched._edge_provider
    sched._edge_provider = lambda: edge
    try:
        codes = await sched._get_scan_candidates()
        assert codes == ["ASHA", "RAJA"], codes
    finally:
        sched._edge_provider = orig
        settings.idx_edge_api_key = old


async def _test_candidates_empty_when_api_fails():
    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    edge = IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    orig = sched._edge_provider
    sched._edge_provider = lambda: edge
    try:
        assert await sched._get_scan_candidates() == []
    finally:
        sched._edge_provider = orig
        settings.idx_edge_api_key = old


def main():
    asyncio.run(_test_candidates_from_screener())
    asyncio.run(_test_candidates_empty_when_api_fails())
    print("OK: test_scheduler_candidates lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && ./.venv/bin/python test_scheduler_candidates.py`
Expected: FAIL — `AttributeError: module 'app.scheduler' has no attribute '_edge_provider'`

- [ ] **Step 3: Write minimal implementation**

Di `backend/app/scheduler.py`:

(a) Tambahkan pabrik provider setelah blok `_TICKER_NAMES`:

```python
def _edge_provider():
    """Pabrik provider IDX Edge PRO — dapat diganti pada test."""
    from app.providers.idx_edge_provider import IdxEdgeProvider

    return IdxEdgeProvider()


async def _get_scan_candidates() -> list[str]:
    """Kandidat scan: pre-filter `screener/latest` bila IDX Edge aktif.

    Bila API gagal/key kosong → fallback whitelist lama hanya saat IDX Edge
    TIDAK aktif; saat aktif tapi gagal, kembalikan [] agar cache lama dipakai
    dan kuota tidak jebol karena scan seluruh emiten.
    """
    provider = _edge_provider()
    if provider.enabled:
        data = await provider.fetch_screener()
        if data and data.get("rows"):
            codes = [
                str(r.get("stock_code")).upper()
                for r in data["rows"]
                if r.get("stock_code")
            ]
            if codes:
                return codes
        logger.warning("Screener IDX Edge PRO gagal/kosong — pakai hasil cache terakhir")
        return []
    return await get_listed_tickers()
```

(b) Di `run_batch_scan`, ganti baris:

```python
    tickers = await get_listed_tickers()
```
```python
    if not tickers:
        logger.error("Tidak ada ticker untuk di-scan (mode=%s)", mode)
        return
```
menjadi:

```python
    tickers = await _get_scan_candidates()
    if not tickers:
        logger.error("Tidak ada kandidat scan (mode=%s) — cache tidak diubah", mode)
        return
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && ./.venv/bin/python test_scheduler_candidates.py`
Expected: `OK: test_scheduler_candidates lolos`

- [ ] **Step 5: Regresi persistence screening**

Run: `cd backend && ./.venv/bin/python test_screening_persistence.py`
Expected: `OK ...` (lolos).

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/test_scheduler_candidates.py
git commit -m "feat: screening pre-filter via IDX Edge PRO screener"
```

---

### Task 10: Isi API key, verifikasi menyeluruh, regresi

**Files:**
- Modify: `backend/.env` (lokal, tidak di-commit)

**Interfaces:**
- Consumes: semua task sebelumnya
- Produces: aplikasi berjalan dengan sumber IDX Edge PRO.

- [ ] **Step 1: Isi API key ke `.env` lokal**

Tambahkan baris berikut ke `backend/.env` (JANGAN di-commit; sudah di-gitignore):

```
IDX_EDGE_API_KEY=sk_live_GANTI_DENGAN_KEY_ANDA
IDX_EDGE_BASE_URL=https://stock.arjum.com
IDX_EDGE_TIMEOUT=20
IDX_EDGE_DAILY_QUOTA=1000
```

- [ ] **Step 2: Jalankan seluruh test standalone**

Run:
```bash
cd backend && for t in test_idx_edge_provider.py test_ticker_sync_edge.py test_mi_broker_edge.py test_scheduler_candidates.py test_providers_smoke.py test_screening_persistence.py test_insight_persistence.py test_16_4_7_validation.py test_16_5_3_validation.py; do echo "== $t =="; ./.venv/bin/python "$t" || exit 1; done
```
Expected: setiap file mencetak `OK ...`; tidak ada `FAIL`.

- [ ] **Step 3: Verifikasi live harga/history (1 panggilan nyata)**

Run:
```bash
cd backend && ./.venv/bin/python -c "
import asyncio
from app.repositories.stock_price_repository import StockPriceRepository
async def main():
    repo = StockPriceRepository()
    df, sim = await repo.get_history('BBCA', '1mo')
    assert df is not None and not df.empty, 'history kosong'
    assert list(df.columns) == ['Open','High','Low','Close','Volume'], list(df.columns)
    print('history OK:', len(df), 'baris; close terakhir', float(df['Close'].iloc[-1]))
    assert await repo.verify_ticker('BBCA') is True
    assert await repo.verify_ticker('ZZZX') is False
    print('verify OK')
asyncio.run(main())
"
```
Expected: `history OK: <n> baris; close terakhir ...` lalu `verify OK`.

- [ ] **Step 4: Verifikasi aplikasi menyala & endpoint kunci**

Run (di terminal terpisah atau background):
```bash
cd backend && ./.venv/bin/python -m uvicorn app.main:app --port 8000 &
sleep 5
curl -s "http://localhost:8000/api/stock/BBCA/history?period=1mo" | head -c 300
echo
curl -s "http://localhost:8000/api/market-intelligence/BBCA" | head -c 300
echo
kill %1
```
Expected: JSON `{"success":true,...}` untuk history (ada `data`) dan `{"success":true,...}` untuk market-intelligence tanpa error 500.

- [ ] **Step 5: Update spec status & commit catatan**

Ubah baris `Status:` di `docs/superpowers/specs/2026-09-29-idx-edge-pro-integration-design.md` menjadi:

```markdown
Status: Diimplementasikan (Tahap 1)
```

Run:
```bash
git add docs/superpowers/specs/2026-09-29-idx-edge-pro-integration-design.md
git commit -m "docs: tandai spec integrasi IDX Edge PRO terimplementasi"
```

---

## Self-Review

**Spec coverage:**
- §5.1 provider baru → Task 2–4 ✅
- §5.2 config → Task 1 ✅
- §6.1 harga/history → Task 6 ✅
- §6.2 verifikasi ticker → Task 6 ✅
- §6.3 sync ticker → Task 7 ✅
- §6.4 broker summary MI → Task 8 ✅
- §7 screening pre-filter → Task 9 ✅
- §8 kuota & error handling → Task 2 (`_get_json`), Task 9 ✅
- §9 tanpa mock → Task 6 (`is_simulated=False`, tak ada mock) ✅
- §10 testing → Task 2–9 + Task 10 regresi ✅
- Celah (berita/profil/rasio/earnings) tetap provider lama → tidak ada perubahan pada repo terkait ✅

**Catatan konsistensi tipe:**
- Semua method provider mengembalikan `None`/`list`/`dict`; repository menyesuaikan.
- `get_broker_summary(ticker, limit)` dipakai konsisten di repository, service, dan test.
- Nama `_edge_provider` dipakai konsisten di `ticker_sync.py` dan `scheduler.py`.
