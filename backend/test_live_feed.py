"""Test live feed WebSocket (tanpa provider asli; fake di level WS).

Jalan: ./.venv/bin/python test_live_feed.py
"""

import asyncio
import json
import sys

sys.path.insert(0, ".")

from app.services import live_feed as lf_mod
from app.services.live_feed import LiveFeed, extract_view, quote_view


class _FakeProviderWS:
    """Fake koneksi WS provider: jawab filter lalu kirim pesan terjadwal."""

    def __init__(self, script: list[dict]):
        self.script = script
        self.sent: list[str] = []
        self.inbox: "asyncio.Queue[str]" = asyncio.Queue()
        for m in script:
            self.inbox.put_nowait(json.dumps(m))

    async def send(self, text: str) -> None:
        self.sent.append(text)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return await asyncio.wait_for(self.inbox.get(), timeout=2.0)
        except asyncio.TimeoutError:
            raise StopAsyncIteration

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


def _snapshot() -> dict:
    return {
        "type": "snapshot",
        "market": {"status": "open"},
        "recent": [
            {"t": "BBCA", "c": "buy", "a": "10:00:01", "p": 6100, "l": 2, "v": 1220000, "pc": 0.5},
            {"t": "TLKM", "c": "sell", "a": "10:00:02", "p": 3000, "l": 1, "v": 300000, "pc": -0.2},
        ],
        "top": [{"ticker": "BBCA", "last_price": 6100}],
    }


def test_extract_view_filters_codes():
    snap = extract_view(_snapshot(), {"BBCA"})
    assert snap is not None
    assert [t["t"] for t in snap["recent"]] == ["BBCA"]
    zzz = extract_view(_snapshot(), {"ZZZ"})
    assert zzz is not None and zzz["top"] == []
    trade = extract_view({"type": "trade", "data": {"t": "BBCA", "c": "buy", "p": 6110}}, {"BBCA"})
    assert trade is not None
    assert trade["data"]["price"] == 6110
    assert extract_view({"type": "trade", "data": {"t": "TLKM"}}, {"BBCA"}) is None
    assert extract_view({"type": "top5"}, {"BBCA"}) is None


def test_quote_view():
    q = quote_view({"t": "BBCA", "p": 6100, "pc": 0.5, "a": "10:00:01"})
    assert q == {"type": "quote", "ticker": "BBCA", "price": 6100, "change_pct": 0.5, "time": "10:00:01"}
    assert quote_view({"t": "BBCA"}) is None


class _PatchedFeed(LiveFeed):
    def __init__(self, script: list[dict]):
        super().__init__(url="wss://test.invalid/ws", api_key="k")
        self._script = script
        self.sent_filters: list[str] = []

    async def _run_loop(self) -> None:
        fake = _FakeProviderWS(self._script)
        self._ws = fake  # type: ignore[attr-defined]
        await self._push_filter()
        self.sent_filters = list(fake.sent)
        try:
            async for raw in fake:
                message = json.loads(raw)
                if isinstance(message, dict):
                    await self._fanout(message)
        finally:
            self._ws = None  # type: ignore[attr-defined]


def _drain(q):
    out = []
    while not q.empty():
        out.append(json.loads(q.get_nowait()))
    return out


def test_subscribe_receives_filtered_snapshot_and_live_trade_then_quiet():
    feed = _PatchedFeed([_snapshot(), {"type": "trade", "data": {"t": "BBCA", "c": "buy", "a": "10:01:00", "p": 6125, "l": 1, "v": 612500, "pc": 0.9}}])

    async def scenario():
        q = await feed.subscribe({"BBCA"})
        await asyncio.sleep(0.3)
        await feed.unsubscribe({"BBCA"}, q)
        return _drain(q)

    got = asyncio.run(scenario())
    kinds = [m["type"] for m in got]
    assert "snapshot" in kinds and "trade" in kinds, kinds
    assert feed.sent_filters and json.loads(feed.sent_filters[-1])["codes"] == ["BBCA"]
    quotes = [m for m in got if m["type"] == "quote"]
    assert quotes and quotes[-1]["price"] == 6125


def test_unsubscribed_code_gets_nothing():
    feed = _PatchedFeed([_snapshot()])

    async def scenario():
        q = await feed.subscribe({"TLKM"})
        await asyncio.sleep(0.3)
        await feed.unsubscribe({"TLKM"}, q)
        return _drain(q)

    got = asyncio.run(scenario())
    assert all(m["type"] != "trade" or (m.get("data") or {}).get("t") == "TLKM" for m in got)
    assert not any((m.get("data") or {}).get("t") == "BBCA" for m in got if m["type"] == "trade")


def test_ws_route_rejects_empty_ticker_and_pipes_messages():
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from app.routers.live import router as live_router

    app = FastAPI()
    app.include_router(live_router)

    with TestClient(app) as client:
        try:
            with client.websocket_connect("/ws/live"):
                raise AssertionError("seharusnya ditolak tanpa ticker")
        except Exception as e:  # noqa: BLE001 — server menutup dengan 4400
            assert "Disconnect" in type(e).__name__

    real_feed = lf_mod._feed
    feed = _PatchedFeed([_snapshot()])
    lf_mod._feed = feed
    client = TestClient(app)
    try:
        with client.websocket_connect("/ws/live?ticker=bbca") as ws:
            hello = json.loads(ws.receive_text())
            assert hello["type"] == "hello" and hello["ticker"] == "BBCA"
            first = json.loads(ws.receive_text())
            assert first["type"] == "snapshot"
            assert [t["t"] for t in first["recent"]] == ["BBCA"]
    finally:
        lf_mod._feed = real_feed


def main():
    test_extract_view_filters_codes()
    test_quote_view()
    test_subscribe_receives_filtered_snapshot_and_live_trade_then_quiet()
    test_unsubscribed_code_gets_nothing()
    test_ws_route_rejects_empty_ticker_and_pipes_messages()
    print("OK: test_live_feed lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
