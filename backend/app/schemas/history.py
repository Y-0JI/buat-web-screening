from pydantic import BaseModel


class OHLCVPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceHistoryResponse(BaseModel):
    success: bool
    ticker: str
    period: str
    is_simulated: bool = False
    data: list[OHLCVPoint] = []
    error: str | None = None
