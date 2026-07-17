"""Base class untuk semua Service.

Menyediakan validasi ticker yang dipakai bersama. Service memegang seluruh
business logic & validasi; ia memanggil Repository (bukan Provider langsung).
"""

import re

from app.repositories import (
    company_profile_repository,
    fundamentals_repository,
    news_repository,
    stock_price_repository,
)
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


class BaseService:
    def __init__(
        self,
        stock_repo=stock_price_repository,
        company_repo=company_profile_repository,
        news_repo=news_repository,
        fundamentals_repo=fundamentals_repository,
    ):
        self._stock_repo = stock_repo
        self._company_repo = company_repo
        self._news_repo = news_repo
        self._fundamentals_repo = fundamentals_repo
