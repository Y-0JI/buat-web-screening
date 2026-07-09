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
    mode: Optional[str] = None
    is_simulated: bool = False
    disclaimer: str = (
        "Hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi."
    )


class ResearchRequest(BaseModel):
    query: str
    ticker: Optional[str] = None
    mode: Optional[str] = None


class ResearchResponse(BaseModel):
    success: bool
    data: Optional[StockReport] = None
    error: Optional[str] = None


class ComparisonRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=5)


class ComparisonResponse(BaseModel):
    success: bool
    data: Optional[list[StockReport]] = None
    error: Optional[str] = None


class RankingItem(BaseModel):
    rank: int
    ticker: str
    company_name: Optional[str] = None
    score: float = Field(ge=0, le=100)
    verdict: Verdict
    confidence: float = Field(ge=0, le=100)
    summary: str
    price: Optional[float] = None
    change_percent: Optional[float] = None


class ScreeningResponse(BaseModel):
    success: bool
    data: Optional[list[RankingItem]] = None
    error: Optional[str] = None


class VisionReport(BaseModel):
    render: RenderType = RenderType.vision_analysis
    file_name: str
    analysis_text: str
    patterns_detected: list[str] = []
    trend: Optional[str] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    disclaimer: str = (
        "Hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi."
    )


class VisionAnalysisResponse(BaseModel):
    success: bool
    data: Optional[VisionReport] = None
    error: Optional[str] = None


class WatchlistItem(BaseModel):
    id: int
    ticker: str
    note: Optional[str] = None
    added_at: str


class AddWatchlistRequest(BaseModel):
    ticker: str = Field(min_length=2, max_length=10)
    note: Optional[str] = None


class WatchlistResponse(BaseModel):
    success: bool
    data: Optional[list[WatchlistItem]] = None
    error: Optional[str] = None


class HistoryItem(BaseModel):
    id: int
    ticker: str
    score: Optional[float] = None
    verdict: Optional[str] = None
    created_at: str


class HistoryResponse(BaseModel):
    success: bool
    data: Optional[list[HistoryItem]] = None
    error: Optional[str] = None
