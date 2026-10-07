"""Test tool AI `get_live_price` (live tick + fallback snapshot REST).

Jalan: ./.venv/bin/python test_ai_live_price.py
"""

import asyncio
import sys

from app.ai import agent as agent_mod
from app.ai.agent import _extract_live_quote, _build_messages, _get_live_price


class _FakeProvider:
    """Provider yang hanya bisa fetch_price (tanpa jaringan)."""

    def __init__(self, payload):
        self._payload = payload
        self.calls = 0

    async def fetch_price(self, code):
        self.calls += 1
        return dict(self._payload, code=code) if self._payload else None


def _patch(monkey, provider=None, tick=None):
    real_provider = agent_mod._edge_provider
    real_tick = agent_mod._live_tick
    agent_mod._edge_provider = lambda: provider if provider else _FakeProvider(None)
    agent_mod._live_tick = tick if tick else _no_live
    return real_provider, real_tick


async def _no_live(code, timeout=agent_mod._LIVE_WAIT):
    return None


def _restore(real_provider, real_tick):
    agent_mod._edge_provider = real_provider
    agent_mod._live_tick = real_tick


def test_extract_quote_shape():
    q = _extract_live_quote(
        {"type": "quote", "ticker": "BBCA", "price": 6225, "change_pct": 1.48, "time": "14:32:07"}
    )
    assert q == {"price": 6225.0, "change_pct": 1.48, "time": "14:32:07"}, q


def test_extract_trade_shape():
    t = _extract_live_quote(
        {"type": "trade", "data": {"t": "BBCA", "price": 6000, "change_pct": -0.5, "time": "10:00:01"}}
    )
    assert t == {"price": 6000.0, "change_pct": -0.5, "time": "10:00:01"}, t


def test_extract_quote_rejects_junk():
    assert _extract_live_quote(None) is None
    assert _extract_live_quote({"type": "trade"}) is None  # tanpa price
    assert _extract_live_quote({"price": "bukan-angka"}) is None


def test_live_price_uses_tick_when_available():
    async def tick(code, timeout=agent_mod._LIVE_WAIT):
        return {"price": 7000.0, "change_pct": 2.0, "time": "15:00:00"}

    provider = _FakeProvider({"last_price": 6225})
    real_provider, real_tick = _patch(monkey=None, provider=provider, tick=tick)
    try:
        out = asyncio.run(_get_live_price("bbca"))
        # Tick menang: fetch_price tidak boleh dipanggil.
        assert out["source"] == "running-trade", out
        assert out["price"] == 7000.0 and out["change_pct"] == 2.0, out
        assert out["as_of"] == "15:00:00", out
        assert provider.calls == 0, provider.calls
    finally:
        _restore(real_provider, real_tick)


def test_live_price_falls_back_to_rest_snapshot():
    provider = _FakeProvider(
        {
            "last_price": 6225,
            "lot": 275000,
            "value": 226875000000,
            "data_ts": "14:32:07",
            "market_state": "open",
            "no_trade_today": False,
        }
    )
    real_provider, real_tick = _patch(monkey=None, provider=provider, tick=_no_live)
    try:
        out = asyncio.run(_get_live_price("BBCA"))
        assert out["source"] == "rest-snapshot", out
        assert out["price"] == 6225, out
        # change_pct tidak ada di endpoint harga -> None
        assert out["change_pct"] is None, out
        assert out["as_of"] == "14:32:07", out
        assert provider.calls == 1, provider.calls
    finally:
        _restore(real_provider, real_tick)


def test_live_price_snapshot_without_trade_today_marks_flag():
    provider = _FakeProvider(
        {"last_price": 5000, "data_ts": None, "source_date": "2026-10-01", "no_trade_today": True}
    )
    real_provider, real_tick = _patch(monkey=None, provider=provider, tick=_no_live)
    try:
        out = asyncio.run(_get_live_price("BBCA"))
        # as_of jatuh ke source_date (harga dari penutupan lama) + flag no_trade_today.
        assert out["as_of"] == "2026-10-01", out
        assert out["no_trade_today"] is True, out
    finally:
        _restore(real_provider, real_tick)


def test_live_price_no_data_returns_error():
    provider = _FakeProvider(None)
    real_provider, real_tick = _patch(monkey=None, provider=provider, tick=_no_live)
    try:
        out = asyncio.run(_get_live_price("XXXX"))
        assert "error" in out, out
    finally:
        _restore(real_provider, real_tick)


def test_live_price_rejects_empty_ticker():
    out = asyncio.run(_get_live_price("   "))
    assert "error" in out, out


def test_tool_registered_and_context_ticker():
    names = [t["function"]["name"] for t in agent_mod.TOOLS]
    assert "get_live_price" in names, names
    assert "get_live_price" in agent_mod._TOOL_MAP

    system = _build_messages([], {"view": "dashboard", "ticker": "BBCA"})[0]["content"]
    assert "BBCA" in system and "dashboard" in system, system

    # System prompt mengarahkan harga terkini ke get_live_price.
    assert "get_live_price" in agent_mod.SYSTEM_PROMPT


class _FakeFeed:
    """LiveFeed palsu: punya market/top siap, tanpa jaringan."""

    def __init__(self, market=None, top=None):
        self._market = market or {}
        self._top = {"top": top or [], "boards": {}, "window_seconds": None}

    async def ensure_running(self):
        return None

    def latest_market(self):
        return dict(self._market)

    def latest_top(self):
        return {"top": list(self._top["top"]), "boards": {}, "window_seconds": self._top["window_seconds"]}


def _patch_feed(feed):
    from app.services import live_feed as lf
    real = lf.get_feed
    lf.get_feed = lambda: feed
    return real


def _restore_feed(real):
    from app.services import live_feed as lf
    lf.get_feed = real


def test_top_active_returns_market_and_top():
    from app.ai.agent import _get_top_active

    feed = _FakeFeed(
        market={"status": "open", "label": "Sesi 1"},
        top=[{"ticker": "BBCA", "last_price": 6100, "last_change_pct": 1.2}],
    )
    real = _patch_feed(feed)
    try:
        out = asyncio.run(_get_top_active())
        assert out["market"]["status"] == "open", out
        assert out["as_of"] == "Sesi 1", out
        item = out["top"][0]
        # normalisasi defensif: last_price -> price, last_change_pct -> change_pct
        assert item["price"] == 6100 and item["change_pct"] == 1.2, item
        assert "top gainer" in out["note"].lower() or "BUKAN top gainer" in out["note"], out["note"]
    finally:
        _restore_feed(real)


def test_top_active_closed_market_empty_top():
    from app.ai.agent import _get_top_active

    feed = _FakeFeed(market={"status": "closed", "label": "Market belum buka"}, top=[])
    real = _patch_feed(feed)
    try:
        out = asyncio.run(_get_top_active())
        # pasar tutup: tetap jawaban (bukan error), top kosong
        assert "error" not in out, out
        assert out["market"]["status"] == "closed", out
        assert out["top"] == [], out
    finally:
        _restore_feed(real)


def test_top_active_error_when_feed_never_snapshots():
    from app.ai.agent import _get_top_active

    feed = _FakeFeed(market={}, top=[])
    real = _patch_feed(feed)
    agent_mod._TOP_WAIT = 0.05  # shorten so test is fast
    try:
        out = asyncio.run(_get_top_active())
        assert "error" in out, out
    finally:
        agent_mod._TOP_WAIT = 3.0
        _restore_feed(real)


def test_top_active_registered_and_prompt():
    from app.ai.agent import _get_top_active  # noqa: F401 — pastikan import
    names = [t["function"]["name"] for t in agent_mod.TOOLS]
    assert "get_top_active" in names, names
    assert "get_top_active" in agent_mod._TOOL_MAP
    assert "get_top_active" in agent_mod.SYSTEM_PROMPT


def main():
    test_extract_quote_shape()
    test_extract_trade_shape()
    test_extract_quote_rejects_junk()
    test_live_price_uses_tick_when_available()
    test_live_price_falls_back_to_rest_snapshot()
    test_live_price_snapshot_without_trade_today_marks_flag()
    test_live_price_no_data_returns_error()
    test_live_price_rejects_empty_ticker()
    test_tool_registered_and_context_ticker()
    test_top_active_returns_market_and_top()
    test_top_active_closed_market_empty_top()
    test_top_active_error_when_feed_never_snapshots()
    test_top_active_registered_and_prompt()
    print("OK: test_ai_live_price lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)