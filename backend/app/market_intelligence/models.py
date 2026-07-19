"""Normalisasi data Market Intelligence (16.5) ke format seragam.

Provider mengembalikan payload mentah IDX/Yahoo; fungsi di sini mengubahnya
menjadi dict dengan field kanonik yang stabil, supaya layer berikutnya
(Intelligence/Scoring/AI Research) tidak perlu tahu bentuk mentah tiap sumber.

Semua fungsi bersifat murni & defensif: input aneh/None → nilai aman (None /
list kosong), tidak pernah raise.
"""

from typing import Any, Dict, List, Optional


def _num(v: Any) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def normalize_dividend(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Item `Dividen` dari GetCompanyProfilesDetail → field kanonik.

    Return None bila record kosong (tak ada dividen).
    """
    if not raw:
        return None
    return {
        "type": _str(raw.get("Jenis")),
        "fiscal_year": _str(raw.get("TahunBuku")),
        "cash_dividend_per_share": _num(raw.get("CashDividenPerSaham")),
        "cash_dividend_total": _num(raw.get("CashDividenTotal")),
        "currency": _str(raw.get("CashDividenTotalMU")) or "IDR",
        "bonus_shares_total": _num(raw.get("TotalSahamBonus")),
        "ratio": f"{raw.get('Rasio1')}:{raw.get('Rasio2')}"
        if raw.get("Rasio1") or raw.get("Rasio2")
        else None,
        "cum_date": _str(raw.get("TanggalCum")),
        "ex_date": _str(raw.get("TanggalExRegulerDanNegosiasi")),
        "recording_date": _str(raw.get("TanggalDPS")),
        "payment_date": _str(raw.get("TanggalPembayaran")),
    }


def normalize_stock_split(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Item LINK_STOCK_SPLIT → corporate action kanonik."""
    return {
        "action_type": "stock_split",
        "code": _str(raw.get("code")),
        "name": _str(raw.get("stockname")),
        "ratio": _str(raw.get("Ratio")),
        "nominal_value_old": _num(raw.get("NominalValue")),
        "nominal_value_new": _num(raw.get("NominalValueNew")),
        "additional_listed_shares": _num(raw.get("AdditionalListedShares")),
        "date": _str(raw.get("ListingDate")),
    }


def normalize_right_offering(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Item LINK_RIGHT_OFFERING → corporate action kanonik."""
    return {
        "action_type": "right_offering",
        "code": _str(raw.get("code")),
        "name": _str(raw.get("issuerName")),
        "ratio": _str(raw.get("ratio")),
        "exercise_price": _num(raw.get("exPrice")),
        "shares_issued": _num(raw.get("sharesIssued")),
        "fund_raised": _num(raw.get("fundRaised")),
        "date": _str(raw.get("exDate")),
        "recording_date": _str(raw.get("recDate")),
    }


def normalize_foreign_flow(raw: Dict[str, Any], date_str: str) -> Optional[Dict[str, Any]]:
    """Row GetStockSummary untuk satu ticker → foreign flow kanonik."""
    if not raw:
        return None
    buy = _num(raw.get("ForeignBuy"))
    sell = _num(raw.get("ForeignSell"))
    net = None
    if buy is not None or sell is not None:
        net = (buy or 0.0) - (sell or 0.0)
    return {
        "date": date_str,
        "foreign_buy": buy,
        "foreign_sell": sell,
        "foreign_net": net,
        "close": _num(raw.get("Close")),
        "volume": _num(raw.get("Volume")),
        "value": _num(raw.get("Value")),
    }


def normalize_broker(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Row GetBrokerSummary → broker kanonik (market-wide)."""
    return {
        "broker_code": _str(raw.get("IDFirm")),
        "broker_name": _str(raw.get("FirmName")),
        "volume": _num(raw.get("Volume")),
        "value": _num(raw.get("Value")),
        "frequency": _num(raw.get("Frequency")),
    }


def normalize_earnings(cal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Yahoo `Ticker.calendar` → earnings kanonik. None bila tak ada tanggal."""
    if not cal:
        return None
    dates = cal.get("Earnings Date")
    earnings_date = None
    if isinstance(dates, list) and dates:
        earnings_date = str(dates[0])
    elif dates:
        earnings_date = str(dates)
    if not earnings_date:
        return None
    return {
        "earnings_date": earnings_date,
        "eps_estimate_avg": _num(cal.get("Earnings Average")),
        "eps_estimate_high": _num(cal.get("Earnings High")),
        "eps_estimate_low": _num(cal.get("Earnings Low")),
        "revenue_estimate_avg": _num(cal.get("Revenue Average")),
        "revenue_estimate_high": _num(cal.get("Revenue High")),
        "revenue_estimate_low": _num(cal.get("Revenue Low")),
    }


def _int(v: Any) -> Optional[int]:
    n = _num(v)
    return int(n) if n is not None else None


def normalize_price_target(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Yahoo `info` → price target kanonik. None bila tak ada target sama sekali."""
    if not info:
        return None
    mean = _num(info.get("targetMeanPrice"))
    high = _num(info.get("targetHighPrice"))
    low = _num(info.get("targetLowPrice"))
    if mean is None and high is None and low is None:
        return None
    return {
        "mean": mean,
        "high": high,
        "low": low,
        "currency": _str(info.get("currency")),
        "number_of_analysts": _int(info.get("numberOfAnalystOpinions")),
    }


def normalize_recommendation(info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Yahoo `info` → recommendation kanonik. None bila tak ada rekomendasi.

    `key`: strong_buy/buy/hold/sell/strong_sell. `mean`: 1.0 (strong buy) .. 5.0
    (strong sell). Yahoo memakai "none" saat tak ada cakupan analis.
    """
    if not info:
        return None
    key = _str(info.get("recommendationKey"))
    if key and key.lower() == "none":
        key = None
    mean = _num(info.get("recommendationMean"))
    n = _int(info.get("numberOfAnalystOpinions"))
    if key is None and mean is None:
        return None
    return {"key": key, "mean": mean, "number_of_analysts": n}


def empty_intelligence(ticker: str) -> Dict[str, Any]:
    """Struktur default Market Intelligence — semua kosong tapi valid."""
    return {
        "ticker": ticker,
        "dividend": None,
        "corporate_actions": [],
        "foreign_flow": None,
        "broker_summary": [],
        "earnings": None,
        "price_target": None,
        "recommendation": None,
    }


def merge_corporate_actions(
    splits: List[Dict[str, Any]], rights: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Gabung split + right offering, urut terbaru dulu (by `date`)."""
    combined = list(splits) + list(rights)
    combined.sort(key=lambda a: a.get("date") or "", reverse=True)
    return combined
