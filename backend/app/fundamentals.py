"""Perhitungan fundamental dari IDX Edge PRO (financial-statements + market-cap + history).

Menghasilkan payload ringkas untuk kartu Fundamental di chat. Hanya memuat
metrik yang datanya tersedia di IDX Edge PRO (tanpa dividend/forward PE/
market-rank yang tidak ada sumbernya).
"""

import logging
from typing import Any, Optional

from app.providers.idx_edge_provider import IdxEdgeProvider

logger = logging.getLogger(__name__)

_INCOME_CANDIDATES = {
    "revenue": ["penjualan_dan_pendapatan_usaha", "pendapatan_bunga", "pendapatan"],
    "gross_profit": ["laba_bruto"],
    "operating_profit": ["laba_operasional"],
    "net_income": ["laba_rugi"],
    "eps": ["laba_rugi_per_saham"],
}

_PERF_PERIODS = [("1D", 1), ("1W", 5), ("1M", 21), ("3M", 63), ("6M", 126), ("1Y", 252)]


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _pick(d: dict, keys: list[str]) -> Optional[float]:
    for k in keys:
        n = _num(d.get(k))
        if n is not None:
            return n
    return None


def _deep(d: Any, keys: list[str]) -> Optional[float]:
    """Ambil nilai numerik pertama dari kandidat key (termasuk 'total')."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        n = _num(v)
        if n is not None:
            return n
        if isinstance(v, dict):
            n = _num(v.get("total")) or _num(v.get(k))
            if n is not None:
                return n
    return None


def _items(payload: Optional[dict]) -> list[dict]:
    if not payload:
        return []
    return payload.get("items") or []


def _sorted_asc(items: list[dict]) -> list[dict]:
    def key(it: dict):
        try:
            return (int(it.get("year") or 0), int(it.get("quarter") or 0))
        except (TypeError, ValueError):
            return (0, 0)

    return sorted(items, key=key)


def _ttm(items: list[dict], metric: str) -> Optional[float]:
    keys = _INCOME_CANDIDATES[metric]
    vals = [_pick(it.get("data") or {}, keys) for it in _sorted_asc(items)[-4:]]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def _growth(items: list[dict], metric: str) -> Optional[float]:
    """YoY kuartal terakhir vs kuartal sama tahun sebelumnya."""
    ordered = _sorted_asc(items)
    if len(ordered) < 2:
        return None
    last = ordered[-1]
    target = next(
        (
            it
            for it in reversed(ordered[:-1])
            if str(it.get("quarter")) == str(last.get("quarter"))
            and str(it.get("year")) != str(last.get("year"))
        ),
        None,
    )
    if target is None:
        return None
    a = _pick(last.get("data") or {}, _INCOME_CANDIDATES[metric])
    b = _pick(target.get("data") or {}, _INCOME_CANDIDATES[metric])
    if a is None or b is None or b == 0:
        return None
    return (a - b) / abs(b) * 100


def _performance(rows: list[dict]) -> list[dict]:
    closes = [r for r in rows if _num(r.get("close")) is not None]
    if len(closes) < 2:
        return []
    latest = closes[-1]
    last_close = _num(latest.get("close"))
    out = []
    for label, back in _PERF_PERIODS:
        if len(closes) <= back:
            continue
        start = _num(closes[-1 - back].get("close"))
        window = closes[-1 - back:]
        if start is None or start == 0:
            continue
        lows = [_num(r.get("low")) for r in window]
        highs = [_num(r.get("high")) for r in window]
        lows = [x for x in lows if x is not None]
        highs = [x for x in highs if x is not None]
        out.append({
            "period": label,
            "change_pct": (last_close - start) / start * 100,
            "low": min(lows) if lows else None,
            "high": max(highs) if highs else None,
        })
    return out


async def build_fundamentals(
    code: str, provider: Optional[IdxEdgeProvider] = None
) -> Optional[dict]:
    p = provider or IdxEdgeProvider()
    ticker = code.upper()

    income = await p.fetch_financial_statements(ticker, report_type="INCOME_STATEMENT", period="quarterly", limit=8)
    balance = await p.fetch_financial_statements(ticker, report_type="BALANCE_SHEET", period="quarterly", limit=1)
    cashflow = await p.fetch_financial_statements(ticker, report_type="CASH_FLOW_REPORT", period="quarterly", limit=4)
    mcap = await p.fetch_market_cap(codes=[ticker])
    hist = await p.fetch_history(ticker, limit=260)

    inc_items = _items(income)
    if not inc_items:
        return None

    market_cap = None
    shares = None
    if mcap and mcap.get("data"):
        row = mcap["data"][0]
        market_cap = _num(row.get("market_cap"))
        shares = _num(row.get("listed_shares"))

    revenue_ttm = _ttm(inc_items, "revenue")
    gross_ttm = _ttm(inc_items, "gross_profit")
    op_ttm = _ttm(inc_items, "operating_profit")
    net_ttm = _ttm(inc_items, "net_income")
    eps_ttm = _ttm(inc_items, "eps")
    as_of = (inc_items[0].get("label") if inc_items else None)

    # Balance sheet (kuartal terbaru)
    bs = (balance.get("items") or [{}])[0].get("data") if balance and balance.get("items") else {}
    aset = (bs or {}).get("aset") or {}
    le = (bs or {}).get("liabilitas_dan_ekuitas") or {}
    total_assets = _deep(aset, ["aset", "total"])
    current_assets = _deep(aset.get("aset_lancar") or {}, ["total", "aset_lancar"])
    cash = _num((aset.get("aset_lancar") or {}).get("kas_dan_setara_kas"))
    liab = le.get("liabilitas") or {}
    total_liabilities = _deep(liab, ["liabilitas", "total"])
    current_liabilities = _deep(liab.get("liabilitas_jangka_pendek") or {}, ["total", "liabilitas_jangka_pendek"])
    equity = _deep(le.get("ekuitas") or {}, ["ekuitas", "total"])

    # Cash flow (TTM)
    cf_items = _sorted_asc(_items(cashflow))[-4:]
    op_cf = inv_cf = fin_cf = capex = None
    if cf_items:
        ops = [_deep((it.get("data") or {}).get("arus_kas_dari_aktivitas_operasi") or {}, ["total", "arus_kas_bersih_yang_diperoleh_dari_digunakan_untuk_aktivitas_operasi"]) for it in cf_items]
        invs = [_deep((it.get("data") or {}).get("arus_kas_dari_aktivitas_investasi") or {}, ["total", "arus_kas_bersih_yang_diperoleh_dari_digunakan_untuk_aktivitas_investasi"]) for it in cf_items]
        fins = [_deep((it.get("data") or {}).get("arus_kas_dari_aktivitas_pendanaan") or {}, ["total", "arus_kas_bersih_yang_diperoleh_dari_digunakan_untuk_aktivitas_pendanaan"]) for it in cf_items]
        caps = [_num(((it.get("data") or {}).get("arus_kas_dari_aktivitas_investasi") or {}).get("pembayaran_untuk_perolehan_aset_tetap")) for it in cf_items]
        op_cf = sum(x for x in ops if x is not None) or None
        inv_cf = sum(x for x in invs if x is not None) or None
        fin_cf = sum(x for x in fins if x is not None) or None
        capex = sum(x for x in caps if x is not None) or None

    fcf = (op_cf + capex) if (op_cf is not None and capex is not None) else None

    def ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b in (None, 0):
            return None
        return a / b

    valuation = {
        "market_cap": market_cap,
        "pe": ratio(market_cap, net_ttm),
        "pbv": ratio(market_cap, equity),
        "psr": ratio(market_cap, revenue_ttm),
        "earnings_yield": (net_ttm / market_cap * 100) if (net_ttm is not None and market_cap) else None,
    }
    per_share = {
        "eps": eps_ttm if eps_ttm is not None else ratio(net_ttm, shares),
        "book_value": ratio(equity, shares),
        "revenue": ratio(revenue_ttm, shares),
    }
    profitability = {
        "gross_margin": (gross_ttm / revenue_ttm * 100) if (gross_ttm is not None and revenue_ttm) else None,
        "operating_margin": (op_ttm / revenue_ttm * 100) if (op_ttm is not None and revenue_ttm) else None,
        "net_margin": (net_ttm / revenue_ttm * 100) if (net_ttm is not None and revenue_ttm) else None,
    }
    solvency = {
        "current_ratio": ratio(current_assets, current_liabilities),
        "debt_to_equity": ratio(total_liabilities, equity),
        "liabilities_to_equity": ratio(total_liabilities, equity),
    }
    growth = {
        "revenue_yoy": _growth(inc_items, "revenue"),
        "net_income_yoy": _growth(inc_items, "net_income"),
    }

    return {
        "ticker": ticker,
        "as_of": as_of,
        "shares": shares,
        "market_cap": market_cap,
        "valuation": valuation,
        "income": {
            "revenue": revenue_ttm,
            "gross_profit": gross_ttm,
            "operating_profit": op_ttm,
            "net_income": net_ttm,
        },
        "balance": {
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": equity,
            "cash": cash,
        },
        "cashflow": {
            "operating": op_cf,
            "investing": inv_cf,
            "financing": fin_cf,
            "free_cash_flow": fcf,
        },
        "per_share": per_share,
        "profitability": profitability,
        "solvency": solvency,
        "growth": growth,
        "performance": _performance(hist or []),
    }
