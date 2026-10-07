"""Live feed IDX Edge PRO via WebSocket (`wss://.../ws/running-trade`).

Satu koneksi persisten ke provider dipakai semua klien; tiap klien hanya
menonton ticker tertentu. Auth server-side (X-API-Key + Origin), jadi kunci
tidak pernah bocor ke browser.

Arus pesan (JSON):
- masuk: `{"type":"snapshot",...}`, `{"type":"trade","data":{...}}`, `{"type":"top5",...}`
- keluar: `{"type":"snapshot",...}`, `{"type":"trade","data":{...}}` (filtered)
- kirim: `{"type":"filter","codes":[...]}`; `{}` = reset.

Tidak ada dependensi baru (stdlib + FastAPI + `websockets` dari uvicorn).
"""

import asyncio
import json
import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_PROVIDER_WS = "/ws/running-trade"
_ORIGIN = "https://stock.arjum.com"

_BACKOFF_INITIAL = 2.0
_BACKOFF_MAX = 30.0
_RECENT_CAP = 100


def _provider_ws_url() -> Optional[str]:
    base = (settings.idx_edge_base_url or "").rstrip("/")
    if not base or not settings.idx_edge_api_key:
        return None
    if base.startswith("https://"):
        host = base[len("https://"):]
    elif base.startswith("http://"):
        host = base[len("http://"):]
    else:
        host = base
    return f"wss://{host}{_PROVIDER_WS}"


def _norm_trade(d: dict) -> dict:
    """Normalisasi satu transaksi -> skema OrderFlowRow + ticker."""
    return {
        "t": d.get("t"),
        "action": str(d.get("c") or "").upper() or None,
        "time": d.get("a"),
        "price": d.get("p"),
        "lot": d.get("l"),
        "value": d.get("v"),
        "buyer": d.get("buyer"),
        "seller": d.get("seller"),
        "board": d.get("board") or "RG",
        "change_pct": d.get("pc"),
    }


def quote_view(d: dict) -> Optional[dict]:
    """View ringkas harga dari satu transaksi: ticker, price, change_pct, time."""
    if d.get("t") is None or d.get("p") is None:
        return None
    return {
        "type": "quote",
        "ticker": d.get("t"),
        "price": d.get("p"),
        "change_pct": d.get("pc"),
        "time": d.get("a"),
    }


def extract_view(message: dict, codes: set[str]) -> Optional[dict]:
    """Ambil view relevan (snapshot/trade) dari pesan provider utk kode."""
    typ = message.get("type")
    if typ == "snapshot":
        recent = [t for t in (message.get("recent") or []) if t.get("t") in codes]
        top = [t for t in (message.get("top") or []) if t.get("ticker") in codes]
        return {
            "type": "snapshot",
            "market": message.get("market"),
            "recent": recent[:_RECENT_CAP],
            "top": top,
        }
    if typ == "trade":
        d = message.get("data") or {}
        if d.get("t") in codes:
            return {"type": "trade", "data": _norm_trade(d)}
        return None
    return None


class LiveFeed:
    """Satu koneksi ke WS provider + sebar ke subscriber per kode."""

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        recent_cap: int = _RECENT_CAP,
    ) -> None:
        self._url = url
        self._api_key = api_key
        self._recent_cap = recent_cap
        self._subs: dict[str, set["asyncio.Queue[str]"]] = {}
        self._state: dict[str, dict] = {}
        self._snapshotted: set[str] = set()
        # Cuplikan pasar terakhir dari pesan snapshot/top5 (bukan per-kode).
        self._top: list = []
        self._boards: dict = {}
        self._window_seconds: Optional[int] = None
        self._market: dict = {}
        self._task: Optional["asyncio.Task[None]"] = None
        self._lock = asyncio.Lock()

    @property
    def _endpoint(self) -> Optional[str]:
        return self._url or _provider_ws_url()

    @property
    def _key(self) -> str:
        return self._api_key if self._api_key is not None else settings.idx_edge_api_key

    async def ensure_running(self) -> None:
        async with self._lock:
            if self._task is None or self._task.done():
                self._task = asyncio.create_task(self._run_loop())

    async def subscribe(self, codes: set[str]) -> "asyncio.Queue[str]":
        await self.ensure_running()
        q: asyncio.Queue[str] = asyncio.Queue()
        for code in codes:
            self._subs.setdefault(code, set()).add(q)
        await self._push_filter()
        for code in codes:
            if code in self._snapshotted and code in self._state:
                q.put_nowait(json.dumps(self._state[code]))
        return q

    async def unsubscribe(self, codes: set[str], q: "asyncio.Queue[str]") -> None:
        for code in codes:
            bucket = self._subs.get(code)
            if bucket is not None:
                bucket.discard(q)
                if not bucket:
                    del self._subs[code]
        await self._push_filter()

    def _union_codes(self) -> set[str]:
        return set(self._subs.keys())

    async def _push_filter(self) -> None:
        ws = getattr(self, "_ws", None)
        if ws is None:
            return
        codes = sorted(self._union_codes())
        try:
            await ws.send(json.dumps({"type": "filter", "codes": codes} if codes else {"type": "filter"}))
        except Exception as e:  # noqa: BLE001 — kirim gagal; loop coba lagi
            logger.warning("Gagal kirim filter WS: %s", e)

    def _ingest(self, message: dict) -> None:
        """Simpan state saja (tanpa kirim) — pengiriman diatur di _fanout."""
        typ = message.get("type")
        if typ == "snapshot":
            for d in message.get("recent") or []:
                t = d.get("t")
                if t:
                    self._store(t, {"type": "trade", "data": _norm_trade(d)})
        if typ == "trade":
            d = message.get("data") or {}
            if d.get("t"):
                self._store(d["t"], {"type": "trade", "data": _norm_trade(d)})

    def _store(self, code: str, view: dict) -> None:
        self._state[code] = view

    def _emit_quote(self, code: str, d: dict) -> None:
        view = quote_view(d)
        if view is None:
            return
        for q in self._subs.get(code, ()):
            q.put_nowait(json.dumps(view))

    async def _fanout(self, message: dict) -> None:
        """Sebar satu pesan provider ke subscriber yang cocok."""
        typ = message.get("type")
        if typ == "snapshot":
            self._capture_market(message)
            for code in self._union_codes():
                self._snapshotted.add(code)
                view = extract_view(message, {code})
                if view is not None:
                    for q in self._subs.get(code, ()):
                        q.put_nowait(json.dumps(view))
            self._ingest(message)
        elif typ == "trade":
            self._ingest(message)
            d = message.get("data") or {}
            code = d.get("t")
            if code and code in self._subs:
                self._emit_quote(code, d)
                view = extract_view(message, {code})
                if view is not None:
                    for q in self._subs.get(code, ()):
                        q.put_nowait(json.dumps(view))
        elif typ == "top5":
            self._capture_market(message)
        # "filter_applied": tidak ada state yang perlu disimpan.

    def _capture_market(self, message: dict) -> None:
        """Simpan top-aktif/boards/window/status pasar dari snapshot|top5."""
        top = message.get("top")
        if isinstance(top, list):
            self._top = top
        boards = message.get("boards")
        if isinstance(boards, dict):
            self._boards = boards
        window = message.get("window_seconds")
        if isinstance(window, int):
            self._window_seconds = window
        market = message.get("market")
        if isinstance(market, dict):
            self._market = market

    def latest_top(self) -> dict:
        """Cuplikan 5 saham teraktif terakhir (list mentah dari provider)."""
        return {
            "top": list(self._top),
            "boards": dict(self._boards),
            "window_seconds": self._window_seconds,
        }

    def latest_market(self) -> dict:
        """Status pasar terakhir (status/label/next_open) dari snapshot."""
        return dict(self._market)

    async def _run_loop(self) -> None:
        try:
            from websockets.asyncio.client import connect
        except ImportError:
            logger.warning("websockets tidak tersedia; live feed nonaktif")
            return
        url = self._endpoint
        delay = _BACKOFF_INITIAL
        while True:
            if not url:
                url = self._endpoint
            if not url or not self._key:
                logger.warning("Live feed: URL/kunci belum diset; coba lagi nanti")
                await asyncio.sleep(_BACKOFF_MAX)
                continue
            try:
                async with connect(
                    url,
                    additional_headers={"X-API-Key": self._key, "Origin": _ORIGIN},
                    open_timeout=20,
                    close_timeout=5,
                    max_size=2**21,
                ) as ws:
                    self._ws = ws  # type: ignore[attr-defined]
                    await self._push_filter()
                    delay = _BACKOFF_INITIAL
                    idle = 0
                    while True:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        except asyncio.TimeoutError:
                            # Provider diam (mis. pasar tutup): ping agar tahu masih hidup.
                            try:
                                pong = await ws.ping()
                                await asyncio.wait_for(pong, timeout=10.0)
                                idle += 1
                                if idle > 20:  # ~10 menit sepi: sambung ulang
                                    break
                                continue
                            except Exception:
                                break
                        idle = 0
                        try:
                            message = json.loads(raw)
                        except (TypeError, ValueError):
                            continue
                        if isinstance(message, dict):
                            await self._fanout(message)
            except Exception as e:  # noqa: BLE001 — putus; backoff lalu sambung ulang
                logger.warning("Live feed putus (%s); sambung ulang dalam %.0fs", e, delay)
            finally:
                self._ws = None  # type: ignore[attr-defined]
            await asyncio.sleep(delay)
            delay = min(delay * 2, _BACKOFF_MAX)


_feed: Optional[LiveFeed] = None


def get_feed() -> LiveFeed:
    global _feed
    if _feed is None:
        _feed = LiveFeed()
    return _feed


def _reset_feed_for_test() -> None:
    global _feed
    _feed = None
