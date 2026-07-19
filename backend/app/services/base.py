"""Helper bersama untuk Service layer.

Hanya `validate_ticker` — fungsi biasa yang dipakai semua service (bukan
di-inherit). Tiap service memegang sendiri repository yang benar-benar ia pakai.
"""

import re

from app.utils.errors import InvalidTickerError

_TICKER_RE = re.compile(r"^[A-Z0-9]{1,6}$")


def validate_ticker(symbol: str) -> str:
    """Validasi & normalisasi ticker IDX. Raise InvalidTickerError bila invalid."""
    if not symbol or not isinstance(symbol, str):
        raise InvalidTickerError("Ticker tidak boleh kosong.")
    clean = symbol.strip().upper().replace(".JK", "")
    if not _TICKER_RE.match(clean):
        raise InvalidTickerError(f"Ticker '{symbol}' tidak valid (harus 1-6 huruf/angka).")
    return clean
