from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Verdict(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    AVOID = "AVOID"


class RenderType(str, Enum):
    stock_report = "stock-report"
    comparison = "comparison"
    ranking = "ranking"
    vision_analysis = "vision-analysis"


class IndicatorData(BaseModel):
    ema: dict = {}
    rsi: Optional[float] = None
    macd: dict = {}
    atr: Optional[float] = None
    vwap: Optional[float] = None
    volume_ratio: Optional[float] = None
    gap_percent: Optional[float] = None
    support_resistance: dict = {}


class ScoreBreakdown(BaseModel):
    funnel_layer: str
    score: float
    weight: float
    note: str


class StockReport(BaseModel):
    render: RenderType = RenderType.stock_report
    ticker: str
    company_name: Optional[str] = None
    price: Optional[float] = None
    change_percent: Optional[float] = None
    score: float = Field(ge=0, le=100)
    verdict: Verdict
    confidence: float = Field(ge=0, le=100)
    summary: str
    indicators: IndicatorData = IndicatorData()
    score_breakdown: list[ScoreBreakdown] = []
    stop_loss: Optional[float] = None
    risk_percent: Optional[float] = None
    disclaimer: str = (
        "Hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi."
    )


class ResearchRequest(BaseModel):
    query: str
    ticker: Optional[str] = None


class ResearchResponse(BaseModel):
    success: bool
    data: Optional[StockReport] = None
    error: Optional[str] = None
