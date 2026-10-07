"""Test cache berita tidak tercampur antar-emiten.

Jalan: ./.venv/bin/python test_news_cache.py
"""

import asyncio
import sys

from app.providers import news_provider as np_mod
from app.providers.news_provider import fetch_news


class _FakeClient:
    pass


def _feed_rows():
    # Judul memuat kedua kode uji agar lolos filter untuk AAAA maupun BBBB.
    return [
        {
            "title": "Indeks dan saham AAAA BBBB bergerak hari ini",
            "url": "https://contoh.test/umum",
            "published": None,
            "snippet": "ringkasan umum pasar modal",
            "source": "Umum",
        }
    ]


def _bing_rows(code: str):
    return [
        {
            "title": f"Saham {code} naik",
            "url": f"https://contoh.test/{code.lower()}-1",
            "published": None,
            "snippet": f"berita {code}",
            "source": "Bing News",
        },
        {
            "title": f"Analisa {code}",
            "url": f"https://contoh.test/{code.lower()}-2",
            "published": None,
            "snippet": f"kabar {code}",
            "source": "Bing News",
        },
    ]


class _Calls:
    feed = 0
    bing = []


async def _fake_fetch_feed(client, url, source):
    _Calls.feed += 1
    return _feed_rows()


async def _fake_fetch_bing_page(client, query, first):
    _Calls.bing.append((query, first))
    if first > 0:
        return []
    return _bing_rows(query)


def _patch():
    real_feed = np_mod._fetch_feed
    real_bing = np_mod._fetch_bing_page
    np_mod._fetch_feed = _fake_fetch_feed
    np_mod._fetch_bing_page = _fake_fetch_bing_page
    # kosongkan cache agar kondisi uji deterministik
    np_mod._feed_cache = {"ts": 0.0, "items": []}
    np_mod._bing_cache = {}
    _Calls.feed = 0
    _Calls.bing = []
    return real_feed, real_bing


def _restore(real_feed, real_bing):
    np_mod._fetch_feed = real_feed
    np_mod._fetch_bing_page = real_bing


def test_bing_dua_emiten():
    real_feed, real_bing = _patch()
    try:
        aots = asyncio.run(fetch_news("AAAA"))
        ca = {it["url"] for it in aots}
        assert any("/aaaa-" in u for u in ca), ca
        assert {u for u in ca if "/bbbb-" in u} == set()

        bots = asyncio.run(fetch_news("BBBB"))
        cb = {it["url"] for it in bots}
        assert any("/bbbb-" in u for u in cb), cb
        # hasil AAAA tidak boleh bocor ke BBBB
        assert {u for u in cb if "/aaaa-" in u} == set()

        # query Bing benar-benar dipanggil terpisah per emiten
        queries = {q for q, _ in _Calls.bing if _ == 0}
        assert queries == {"AAAA", "BBBB"}, queries
    finally:
        _restore(real_feed, real_bing)


def test_feed_terpakai_sekali():
    real_feed, real_bing = _patch()
    try:
        asyncio.run(fetch_news("AAAA"))
        first_feed = _Calls.feed
        asyncio.run(fetch_news("BBBB"))
        # feed penerbit global jadi tidak diambil ulang
        assert _Calls.feed == first_feed, (_Calls.feed, first_feed)
    finally:
        _restore(real_feed, real_bing)


def test_feed_penerbit_tetap_dibagi_pakai():
    real_feed, real_bing = _patch()
    try:
        a = asyncio.run(fetch_news("AAAA"))
        urls = {it["url"] for it in a}
        assert "https://contoh.test/umum" in urls, urls
    finally:
        _restore(real_feed, real_bing)


def main():
    test_bing_dua_emiten()
    test_feed_penerbit_tetap_dibagi_pakai()
    test_feed_terpakai_sekali()
    print("OK: test_news_cache lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)