"""Repository layer — abstraksi tunggal akses data.

Setiap repository adalah satu-satunya pintu antara aplikasi dan sumber data
(Yahoo Finance / cache). Export instance default agar modul lain cukup import
satu objek tanpa menginstansiasi ulang cache-nya.
"""

from app.repositories.company_profile_repository import (
    CompanyProfileRepository,
)
from app.repositories.fundamentals_repository import FundamentalsRepository
from app.repositories.news_repository import NewsRepository
from app.repositories.stock_price_repository import StockPriceRepository

company_profile_repository = CompanyProfileRepository()
fundamentals_repository = FundamentalsRepository()
news_repository = NewsRepository()
stock_price_repository = StockPriceRepository()

__all__ = [
    "CompanyProfileRepository",
    "FundamentalsRepository",
    "NewsRepository",
    "StockPriceRepository",
    "company_profile_repository",
    "fundamentals_repository",
    "news_repository",
    "stock_price_repository",
]
