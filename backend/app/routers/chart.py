from fastapi import APIRouter
from datetime import datetime
from app.services import stock_service
from app.schemas.history import PriceHistoryResponse, OHLCVPoint

router = APIRouter(prefix="/api/stock", tags=["chart"])


@router.get("/{ticker}/history", response_model=PriceHistoryResponse)
async def get_history(ticker: str, period: str = "6mo"):
    df, is_simulated = await stock_service.get_history(ticker, period)
    if df is None or df.empty:
        return PriceHistoryResponse(
            success=False,
            ticker=ticker.upper(),
            period=period,
            is_simulated=is_simulated,
            error="Data tidak tersedia",
        )

    points = []
    for idx, row in df.iterrows():
        points.append(
            OHLCVPoint(
                date=idx.strftime("%Y-%m-%d") if isinstance(idx, datetime) else str(idx),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=int(row["Volume"]),
            )
        )

    return PriceHistoryResponse(
        success=True,
        ticker=ticker.upper(),
        period=period,
        is_simulated=is_simulated,
        data=points,
    )