import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from app.services import company_profile_service
from app.utils.errors import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stock", tags=["stock"])


class CompanyProfileResponse(BaseModel):
    success: bool
    ticker: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/{ticker}/profile", response_model=CompanyProfileResponse)
async def stock_profile(ticker: str):
    clean = ticker.upper().strip()
    try:
        data = await company_profile_service.get_profile(clean)
        if data.get("error"):
            return CompanyProfileResponse(success=False, ticker=clean, error=data["error"])
        return CompanyProfileResponse(success=True, ticker=clean, data=data)
    except AppError as e:
        logger.warning("Profile error for %s: %s", clean, e.message)
        return CompanyProfileResponse(success=False, ticker=clean, error=e.message)
    except Exception as e:
        logger.error("Profile error for %s: %s", clean, e, exc_info=True)
        return CompanyProfileResponse(
            success=False, ticker=clean, error=f"Gagal mengambil profil: {e}"
        )
