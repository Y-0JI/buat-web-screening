"""Test fail-fast error 4xx di _fetch_json IDX (tanpa jaringan).

Jalan: ./.venv/bin/python test_idx_provider_fastfail.py
"""

import asyncio
import sys
import time

import app.providers.idx_provider as idx


class _FakeResp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.headers = {}

    def raise_for_status(self):
        raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return {}


def _patch(status_code):
    orig = idx.curl_requests

    class _Session:
        def __init__(self, *a, **k):
            pass

        def get(self, *a, **k):
            return _FakeResp(status_code)

    class _CurlMod:
        Session = _Session

    idx.curl_requests = _CurlMod
    return orig


def _run(status_code):
    orig = _patch(status_code)
    try:
        t = time.time()
        raised = False
        try:
            asyncio.run(idx._fetch_json("https://example.test/x"))
        except Exception:
            raised = True
        return raised, time.time() - t
    finally:
        idx.curl_requests = orig


def test_403_fail_fast():
    raised, dur = _run(403)
    assert raised, "harus raise untuk 403"
    assert dur < 1.0, f"tidak fail-fast (butuh {dur:.1f}s)"


def test_429_still_retries():
    raised, dur = _run(429)
    assert raised, "harus raise setelah retry habis"
    assert dur > 1.0, f"429 harus di-retry (durasi {dur:.1f}s terlalu cepat)"


def main():
    test_403_fail_fast()
    test_429_still_retries()
    print("OK: test_idx_provider_fastfail lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
