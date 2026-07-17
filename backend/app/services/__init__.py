"""Service layer — business logic & validasi di atas Repository.

Export instance default agar router / modul lain cukup import satu objek.
"""

from app.services.company_profile_service import CompanyProfileService
from app.services.fundamentals_service import FundamentalsService
from app.services.news_service import NewsService
from app.services.stock_service import StockService

stock_service = StockService()
company_profile_service = CompanyProfileService()
news_service = NewsService()
fundamentals_service = FundamentalsService()

__all__ = [
    "StockService",
    "CompanyProfileService",
    "NewsService",
    "FundamentalsService",
    "stock_service",
    "company_profile_service",
    "news_service",
    "fundamentals_service",
]
