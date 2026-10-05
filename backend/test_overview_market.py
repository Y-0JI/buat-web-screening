"""Test router order-flow + news (tanpa jaringan asli, mock transport).

Jalan: ./.venv/bin/python test_overview_market.py
"""

import asyncio
import sys

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.routers import order_flow as of_mod
from app.routers.order_flow import order_flow_payload, router as of_router
from app.routers import news as news_mod
from app.routers.news import router as news_router
from app.providers import news_provider
from app.providers.news_provider import article_allowed, fetch_article, fetch_news

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>BBCA raih laba besar</title>
<link>https://www.cnbcindonesia.com/berita/bbca-laba</link>
<pubDate>Mon, 01 Sep 2026 10:00:00 GMT</pubDate>
<description><![CDATA[<p>Labanya naik.</p>]]></description></item>
<item><title>Cuaca cerah dan suku bunga bank hari ini</title>
<link>https://www.cnbcindonesia.com/berita/cuaca</link>
<pubDate>Mon, 01 Sep 2026 09:00:00 GMT</pubDate>
<description><![CDATA[<p>Cerah.</p>]]></description></item>
<item><title>BCA catat pertumbuhan kredit</title>
<link>https://www.cnbcindonesia.com/berita/bca-kredit</link>
<pubDate>Mon, 01 Sep 2026 08:00:00 GMT</pubDate>
<description><![CDATA[<p>Kredit tumbuh.</p>]]></description></item>
</channel></rss>"""


def test_order_flow_payload():
    rows = order_flow_payload({
        "code": "BBCA", "date": "2026-10-02", "total": 1,
        "data": [{
            "time": "16:13:59", "price_num": 6100, "lot": 2,
            "value_raw": 1220000, "buyer": "KZ", "seller": "BQ",
            "action": "sell", "buyer_type": "F", "seller_type": "D",
            "market_board": "RG",
        }],
    })
    assert rows is not None
    r = rows["rows"][0]
    assert r["price"] == 6100.0 and r["action"] == "SELL"
    assert r["buyer"] == "KZ" and r["board"] == "RG"
    assert order_flow_payload(None) is None


def test_order_flow_route_clamps():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"code": "BBCA", "date": "2026-10-02", "total": 0, "data": []})

    old = settings.idx_edge_api_key
    settings.idx_edge_api_key = "test-key"
    real = of_mod.IdxEdgeProvider
    from app.providers.idx_edge_provider import IdxEdgeProvider
    of_mod.IdxEdgeProvider = lambda: IdxEdgeProvider(client=httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://stock.arjum.com"))
    try:
        app = FastAPI()
        app.include_router(of_router)
        r = TestClient(app).get("/api/order-flow/BBCA?limit=500")
        assert r.status_code == 200, r.text
        assert "per_page=100" in seen["url"], seen
    finally:
        of_mod.IdxEdgeProvider = real
        settings.idx_edge_api_key = old


def test_news_feed_parse_and_filter():
    async def fake_fetch(client, url, source):
        assert isinstance(url, str)
        if "cnbcindonesia" not in url:
            return []
        return news_provider._parse_feed(SAMPLE_RSS.encode(), "CNBC Indonesia")

    real_fetch = news_provider._fetch_feed
    news_provider._fetch_feed = fake_fetch
    news_provider._feed_cache["items"] = []
    news_provider._feed_cache["ts"] = 0.0
    try:
        items = asyncio.run(fetch_news("BBCA", name="Bank Central Asia Tbk.", limit=10))
        codes = {u.rsplit("/", 1)[-1] for u in [i["url"] for i in items]}
        assert codes == {"bbca-laba", "bca-kredit"}, items
        assert items[0]["snippet"] == "Labanya naik."
    finally:
        news_provider._fetch_feed = real_fetch
        news_provider._feed_cache["items"] = []


def test_article_ssrf_guard():
    assert article_allowed("https://www.cnbcindonesia.com/berita/x")
    assert article_allowed("https://sub.detark.com/x") is False
    assert article_allowed("https://evil.com/?next=https://www.cnbcindonesia.com") is False
    assert article_allowed("not-a-url") is False
    assert asyncio.run(fetch_article("https://evil.com/x")) is None


def test_news_route_uses_provider():
    real_list = news_mod.news_provider.fetch_news
    real_name = news_mod._resolve_name

    async def fake_list(code, name=None, limit=20):
        return [{"title": "BBCA naik", "url": "https://www.cnbcindonesia.com/x",
                 "published": None, "snippet": "s", "source": "CNBC Indonesia"}]

    async def fake_name(code):
        return "Bank Central Asia Tbk."

    news_mod.news_provider.fetch_news = fake_list
    news_mod._resolve_name = fake_name
    try:
        app = FastAPI()
        app.include_router(news_router)
        r = TestClient(app).get("/api/news/BBCA")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["success"] and data["data"][0]["title"] == "BBCA naik"
    finally:
        news_mod.news_provider.fetch_news = real_list
        news_mod._resolve_name = real_name


def main():
    test_order_flow_payload()
    test_order_flow_route_clamps()
    test_news_feed_parse_and_filter()
    test_article_ssrf_guard()
    test_news_route_uses_provider()
    print("OK: test_overview_market lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
