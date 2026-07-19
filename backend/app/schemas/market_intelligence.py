"""Schema respons Market Intelligence (16.5.2).

Semua field Optional / empty-safe supaya data yang tidak tersedia (khususnya
Price Target & Recommendation) tidak dianggap error — konsisten dengan pola
`Fundamentals` di `stock.py`.
"""

from typing import Optional

from pydantic import BaseModel


class DividendItem(BaseModel):
    type: Optional[str] = None
    fiscal_year: Optional[str] = None
    cash_dividend_per_share: Optional[float] = None
    cash_dividend_total: Optional[float] = None
    currency: Optional[str] = None
    bonus_shares_total: Optional[float] = None
    ratio: Optional[str] = None
    cum_date: Optional[str] = None
    ex_date: Optional[str] = None
    recording_date: Optional[str] = None
    payment_date: Optional[str] = None


class CorporateActionItem(BaseModel):
    action_type: str
    code: Optional[str] = None
    name: Optional[str] = None
    ratio: Optional[str] = None
    date: Optional[str] = None
    recording_date: Optional[str] = None
    # stock split
    nominal_value_old: Optional[float] = None
    nominal_value_new: Optional[float] = None
    additional_listed_shares: Optional[float] = None
    # right offering
    exercise_price: Optional[float] = None
    shares_issued: Optional[float] = None
    fund_raised: Optional[float] = None


class ForeignFlowItem(BaseModel):
    date: Optional[str] = None
    foreign_buy: Optional[float] = None
    foreign_sell: Optional[float] = None
    foreign_net: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    value: Optional[float] = None


class BrokerItem(BaseModel):
    broker_code: Optional[str] = None
    broker_name: Optional[str] = None
    volume: Optional[float] = None
    value: Optional[float] = None
    frequency: Optional[float] = None


class EarningsItem(BaseModel):
    earnings_date: Optional[str] = None
    eps_estimate_avg: Optional[float] = None
    eps_estimate_high: Optional[float] = None
    eps_estimate_low: Optional[float] = None
    revenue_estimate_avg: Optional[float] = None
    revenue_estimate_high: Optional[float] = None
    revenue_estimate_low: Optional[float] = None


class MarketIntelligenceData(BaseModel):
    ticker: str
    dividend: Optional[DividendItem] = None
    corporate_actions: list[CorporateActionItem] = []
    foreign_flow: Optional[ForeignFlowItem] = None
    broker_summary: list[BrokerItem] = []
    earnings: Optional[EarningsItem] = None
    # Belum ada sumber reliabel (lihat doc 16.5) — empty-safe, diisi di 16.5.3.
    price_target: Optional[float] = None
    recommendation: list[str] = []


class MarketIntelligenceResponse(BaseModel):
    success: bool
    data: Optional[MarketIntelligenceData] = None
    error: Optional[str] = None
