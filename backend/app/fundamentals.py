"""Perhitungan fundamental dari IDX Edge PRO (financial-statements + market-cap + history).

Menghasilkan payload ringkas untuk kartu Fundamental di chat. Hanya memuat
metrik yang datanya tersedia di IDX Edge PRO (tanpa dividend/forward PE/
market-rank yang tidak ada sumbernya).
"""

import logging
from datetime import date
from typing import Any, Optional

from app.providers.idx_edge_provider import IdxEdgeProvider

logger = logging.getLogger(__name__)

_INCOME_CANDIDATES = {
    "revenue": ["penjualan_dan_pendapatan_usaha", "pendapatan_bunga", "pendapatan"],
    "gross_profit": ["laba_bruto"],
    "operating_profit": ["laba_operasional", "laba_usaha", "laba_operasi"],
    "net_income": ["laba_rugi"],
    "eps": ["laba_per_saham_dasar"],
    "cogs": ["beban_pokok_pendapatan", "beban_pokok_penjualan", "beban_pokok"],
    "admin_expense": ["beban_umum_dan_administrasi"],
    "sales_expense": ["beban_penjualan"],
}

_PERF_PERIODS = [("1D", 1), ("1W", 5), ("1M", 21), ("3M", 63), ("6M", 126), ("YTD", -1), ("1Y", 252)]


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


def _seek(data: Any, needle: str, exclude: Optional[str] = None) -> Optional[float]:
    """Nilai numerik pertama yang jalur dotted-nya mengandung `needle`.

    Bila grup cocok, pakai anak `total`-nya (agar dapat angka agregat,
    bukan sub-baris). Untuk baris bersarang yang namanya beda antar
    industri/bank, saat key top-level bukan angka.
    """
    found: Optional[float] = None

    def walk(d: Any, path: str) -> None:
        nonlocal found
        if found is not None:
            return
        if not isinstance(d, dict):
            return
        for k, v in d.items():
            p = f"{path}.{k}" if path else str(k)
            if exclude and exclude in p:
                continue
            if isinstance(v, dict):
                if needle in p:
                    t = _num(v.get("total"))
                    if t is not None:
                        found = t
                        return
                walk(v, p)
            elif needle in p:
                n = _num(v)
                if n is not None:
                    found = n
                    return

    walk(data, "")
    return found


def _eps_of(d: dict) -> Optional[float]:
    v = _pick(d, ["laba_per_saham_dasar"])
    if v is not None:
        return v
    return _seek(d, "laba_per_saham_dasar") or _seek(d, "laba_rugi_per_saham")


def _op_of(d: dict) -> Optional[float]:
    """Laba operasi: baris langsung (bank) atau bruto − beban (non-bank)."""
    v = _pick(d, _INCOME_CANDIDATES["operating_profit"])
    if v is not None:
        return v
    g = _pick(d, _INCOME_CANDIDATES["gross_profit"])
    a = _pick(d, _INCOME_CANDIDATES["admin_expense"])
    s = _pick(d, _INCOME_CANDIDATES["sales_expense"])
    if g is None:
        return None
    if a is None and s is None:
        return None
    # beban tersimpan negatif di API -> pakai nilai absolut
    return g - abs(a if a is not None else 0.0) - abs(s if s is not None else 0.0)


def _sum4(items: list[dict], fn) -> Optional[float]:
    vals = [fn(it.get("data") or {}) for it in _sorted_asc(items)[-4:]]
    vals = [v for v in vals if v is not None]
    return sum(vals) if vals else None


def _q1(items: list[dict], fn) -> Optional[float]:
    ordered = _sorted_asc(items)
    if not ordered:
        return None
    return fn(ordered[-1].get("data") or {})


_CF_OP_KEYS = ["total", "arus_kas_bersih_yang_diperoleh_dari_digunakan_untuk_aktivitas_operasi"]
_CF_INV_KEYS = ["total", "arus_kas_bersih_yang_diperoleh_dari_digunakan_untuk_aktivitas_investasi"]
_CF_FIN_KEYS = ["total", "arus_kas_bersih_yang_diperoleh_dari_digunakan_untuk_aktivitas_pendanaan"]
_CAPEX_KEY = "pembayaran_untuk_perolehan_aset_tetap"


def _cf_row(data: dict) -> dict:
    return {
        "op": _deep(data.get("arus_kas_dari_aktivitas_operasi") or {}, _CF_OP_KEYS),
        "inv": _deep(data.get("arus_kas_dari_aktivitas_investasi") or {}, _CF_INV_KEYS),
        "fin": _deep(data.get("arus_kas_dari_aktivitas_pendanaan") or {}, _CF_FIN_KEYS),
        "capex": _num((data.get("arus_kas_dari_aktivitas_investasi") or {}).get(_CAPEX_KEY)),
    }


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


def _growth(items: list[dict], metric: str, fn=None) -> Optional[float]:
    """YoY kuartal terakhir vs kuartal sama tahun sebelumnya.

    `fn` opsional mengekstrak nilai dari `data` (untuk metrik yang
    strukturnya beda bank vs non-bank, mis. revenue)."""
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
    get = fn or (lambda d: _pick(d, _INCOME_CANDIDATES[metric]))
    a = get(last.get("data") or {})
    b = get(target.get("data") or {})
    if a is None or b is None or b == 0:
        return None
    return (a - b) / abs(b) * 100


def _perf_row(latest_close: float, window: list[dict]) -> Optional[dict]:
    start = _num(window[0].get("close"))
    if start is None or start == 0:
        return None
    lows = [x for x in (_num(r.get("low")) for r in window) if x is not None]
    highs = [x for x in (_num(r.get("high")) for r in window) if x is not None]
    return {
        "change_pct": (latest_close - start) / start * 100,
        "low": min(lows) if lows else None,
        "high": max(highs) if highs else None,
    }


def _performance(rows: list[dict]) -> list[dict]:
    closes = [r for r in rows if _num(r.get("close")) is not None]
    if len(closes) < 2:
        return []
    last_close = _num(closes[-1].get("close"))
    if last_close is None:
        return []
    out = []
    for label, back in _PERF_PERIODS:
        if back == -1:  # YTD
            cur_year = str(date.today().year)
            window = [r for r in closes if str(r.get("date") or "")[:4] == cur_year]
            if len(window) < 2:
                continue
        else:
            if len(closes) <= back:
                continue
            window = closes[-1 - back:]
        row = _perf_row(last_close, window)
        if row is None:
            continue
        out.append({"period": label, **row})
    return out


def _rev_of(d: dict) -> Optional[float]:
    """Pendapatan: baris langsung, atau total pendapatan operasional (bank)."""
    v = _pick(d, _INCOME_CANDIDATES["revenue"])
    if v is not None:
        return v
    return _deep(d.get("pendapatan_dan_beban_operasional") or {}, ["total"])


def _seek_total(d: Any, needles: list[str]) -> Optional[float]:
    """Nilai `total` dari grup pertama yang key-nya mengandung needle."""
    found: Optional[float] = None

    def walk(x: Any) -> None:
        nonlocal found
        if found is not None or not isinstance(x, dict):
            return
        for k, v in x.items():
            if isinstance(v, dict):
                if any(n in str(k).lower() for n in needles):
                    t = _num(v.get("total"))
                    if t is not None:
                        found = t
                        return
                walk(v)

    walk(d)
    return found


def _inc_val(d: dict, exact: list[str], needle: Optional[str] = None) -> Optional[float]:
    v = _pick(d, exact)
    if v is not None:
        return v
    return _seek(d, needle) if needle else None


def _growth_n(items: list[dict], metric: str, years: int) -> Optional[float]:
    """YoY kuartal terakhir vs kuartal sama `years` tahun sebelumnya."""
    ordered = _sorted_asc(items)
    if len(ordered) < 2:
        return None
    last = ordered[-1]
    try:
        target_year = int(str(last.get("year") or 0)) - years
    except (TypeError, ValueError):
        return None
    target = next(
        (
            it
            for it in reversed(ordered[:-1])
            if str(it.get("quarter")) == str(last.get("quarter"))
            and str(it.get("year")) == str(target_year)
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


def _bal(bs: dict, exact_fn, needle: Optional[str] = None) -> Optional[float]:
    v = exact_fn()
    if v is not None:
        return v
    return _seek(bs, needle) if needle else None


async def build_fundamentals(
    code: str, provider: Optional[Any] = None, full: bool = False
) -> Optional[dict]:
    """Bangun payload fundamental. `full=False` = ringkas (untuk agen, hemat token)."""
    p = provider or IdxEdgeProvider()
    ticker = code.upper()

    income = await p.fetch_financial_statements(ticker, report_type="INCOME_STATEMENT", period="quarterly", limit=16)
    balance = await p.fetch_financial_statements(ticker, report_type="BALANCE_SHEET", period="quarterly", limit=1)
    cashflow = await p.fetch_financial_statements(ticker, report_type="CASH_FLOW_REPORT", period="quarterly", limit=8)
    mcap = await p.fetch_market_cap(codes=[ticker])
    hist = await p.fetch_history(ticker, limit=400)

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
    rev_fix = _sum4(inc_items, _rev_of)
    if rev_fix is not None:
        revenue_ttm = rev_fix
    op_fix = _sum4(inc_items, _op_of)
    if op_fix is not None:
        op_ttm = op_fix
    eps_fix = _sum4(inc_items, _eps_of)
    if eps_fix is not None:
        eps_ttm = eps_fix
    as_of = (inc_items[0].get("label") if inc_items else None)

    # Balance sheet (kuartal terbaru)
    bs = (balance.get("items") or [{}])[0].get("data") if balance and balance.get("items") else {}
    aset = (bs or {}).get("aset") or {}
    le = (bs or {}).get("liabilitas_dan_ekuitas") or (bs or {}).get("liabilitas_dana_syirkah_temporer_dan_ekuitas") or {}
    total_assets = _deep(aset, ["aset", "total"])
    current_assets = _deep(aset.get("aset_lancar") or {}, ["total", "aset_lancar"])
    cash = _num((aset.get("aset_lancar") or {}).get("kas_dan_setara_kas"))
    if cash is None:
        cash = _num(aset.get("kas"))
    liab = le.get("liabilitas") or {}
    total_liabilities = _deep(liab, ["liabilitas", "total"])
    current_liabilities = _deep(liab.get("liabilitas_jangka_pendek") or {}, ["total", "liabilitas_jangka_pendek"])
    equity = _deep(le.get("ekuitas") or {}, ["ekuitas", "total"])

    # Cash flow (TTM)
    cf_items = _sorted_asc(_items(cashflow))[-4:]
    op_cf = inv_cf = fin_cf = capex = None
    if cf_items:
        rows = [_cf_row(it.get("data") or {}) for it in cf_items]
        op_cf = sum(x["op"] for x in rows if x["op"] is not None) or None
        inv_cf = sum(x["inv"] for x in rows if x["inv"] is not None) or None
        fin_cf = sum(x["fin"] for x in rows if x["fin"] is not None) or None
        capex = sum(x["capex"] for x in rows if x["capex"] is not None) or None

    fcf = (op_cf + capex) if (op_cf is not None and capex is not None) else None

    def ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b in (None, 0):
            return None
        return a / b

    payload: dict = {
        "ticker": ticker,
        "as_of": as_of,
        "shares": shares,
        "market_cap": market_cap,
        "valuation": {
            "market_cap": market_cap,
            "pe": ratio(market_cap, net_ttm),
            "pbv": ratio(market_cap, equity),
            "psr": ratio(market_cap, revenue_ttm),
            "earnings_yield": (net_ttm / market_cap * 100) if (net_ttm is not None and market_cap) else None,
        },
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
        "per_share": {
            "eps": eps_ttm if eps_ttm is not None else ratio(net_ttm, shares),
            "book_value": ratio(equity, shares),
            "revenue": ratio(revenue_ttm, shares),
        },
        "profitability": {
            "gross_margin": (gross_ttm / revenue_ttm * 100) if (gross_ttm is not None and revenue_ttm) else None,
            "operating_margin": (op_ttm / revenue_ttm * 100) if (op_ttm is not None and revenue_ttm) else None,
            "net_margin": (net_ttm / revenue_ttm * 100) if (net_ttm is not None and revenue_ttm) else None,
        },
        "solvency": {
            "current_ratio": ratio(current_assets, current_liabilities),
            "debt_to_equity": ratio(total_liabilities, equity),
            "liabilities_to_equity": ratio(total_liabilities, equity),
        },
        "growth": {
            "revenue_yoy": _growth(inc_items, "revenue", _rev_of),
            "net_income_yoy": _growth(inc_items, "net_income"),
        },
        "performance": _performance(hist or []),
    }

    if not full:
        return payload

    # ---- Mode penuh (REST/dashboard): semua metrik yang tersedia di API ----
    cogs_ttm = _sum4(inc_items, lambda d: _pick(d, _INCOME_CANDIDATES["cogs"]) or _seek(d, "beban_pokok"))
    pretax_ttm = _sum4(inc_items, lambda d: _inc_val(d, ["laba_rugi_sebelum_pajak_penghasilan", "laba_sebelum_pajak"], "sebelum_pajak"))
    tax_ttm = _sum4(inc_items, lambda d: _inc_val(d, ["pendapatan_beban_pajak", "beban_pajak"], "beban_pajak"))
    interest_ttm = _sum4(inc_items, lambda d: _inc_val(d, ["beban_bunga", "beban_keuangan"], "beban_bunga"))

    ordered_inc = _sorted_asc(inc_items)
    last_inc = (ordered_inc[-1].get("data") or {}) if ordered_inc else {}
    rev_q = _rev_of(last_inc)
    gross_q = _pick(last_inc, _INCOME_CANDIDATES["gross_profit"])
    op_q = _op_of(last_inc)
    net_q = _pick(last_inc, _INCOME_CANDIDATES["net_income"])
    eps_q = _eps_of(last_inc)
    eps_ann = (eps_q * 4) if eps_q is not None else None
    net_ann = (net_q * 4) if net_q is not None else None

    inventory = _seek(bs, "persediaan")
    receivables = _seek(bs, "piutang_usaha")
    payables = _seek(bs, "utang_usaha", exclude="piutang")
    st_debt = _seek(bs, "utang_bank_jangka_pendek") or _seek(bs, "pinjaman_jangka_pendek") or _seek(bs, "utang_jangka_pendek")
    lt_debt = _seek(bs, "utang_bank_jangka_panjang") or _seek(bs, "pinjaman_jangka_panjang") or _seek(bs, "utang_obligasi")
    retained = _seek(bs, "saldo_laba") or _seek(bs, "laba_ditahan")
    common_equity = _seek_total(le, ["diatribusikan", "pemilik_entitas", "induk"]) or equity

    total_debt = None
    if st_debt is not None or lt_debt is not None:
        total_debt = (st_debt or 0.0) + (lt_debt or 0.0)
    net_debt = (total_debt - cash) if (total_debt is not None and cash is not None) else None
    working_capital = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    ev = (market_cap + net_debt) if (market_cap is not None and net_debt is not None) else None
    op_for_ratios = op_ttm
    net_g = _growth(inc_items, "net_income")
    pe_now = ratio(market_cap, net_ttm)

    peg = (pe_now / net_g) if (pe_now is not None and net_g is not None and net_g > 0) else None
    g3 = _growth_n(inc_items, "net_income", 3)
    peg_3yr = (pe_now / g3) if (pe_now is not None and g3 is not None and g3 > 0) else None

    tax_rate = (tax_ttm / pretax_ttm) if (tax_ttm is not None and pretax_ttm) else None
    nopat = (op_for_ratios * (1 - tax_rate)) if (op_for_ratios is not None and tax_rate is not None and 0 <= tax_rate < 1) else (net_ttm if net_ttm is not None else op_for_ratios)
    invested = None
    if equity is not None:
        invested = equity + (net_debt if net_debt is not None and net_debt > 0 else (total_debt or 0.0))
    roa = (net_ttm / total_assets * 100) if (net_ttm is not None and total_assets) else None
    roe = (net_ttm / equity * 100) if (net_ttm is not None and equity) else None
    roce = (op_for_ratios / (total_assets - current_liabilities) * 100) if (op_for_ratios is not None and total_assets is not None and current_liabilities is not None and (total_assets - current_liabilities)) else None
    _roic_base = ratio(nopat, invested)
    roic = (_roic_base * 100) if _roic_base is not None else None

    days = 365.0
    cogs_abs = abs(cogs_ttm) if cogs_ttm is not None else None
    dso = (receivables / revenue_ttm * days) if (receivables is not None and receivables > 0 and revenue_ttm) else None
    dio = (inventory / cogs_abs * days) if (inventory is not None and inventory > 0 and cogs_abs) else None
    dpo = (payables / cogs_abs * days) if (payables is not None and payables > 0 and cogs_abs) else None
    ccc = None
    if dso is not None and dio is not None and dpo is not None:
        ccc = dso + dio - dpo

    altman_z = None
    if all(v is not None for v in [working_capital, retained, op_for_ratios, equity, revenue_ttm]) and total_assets and total_liabilities:
        assert working_capital is not None and retained is not None and op_for_ratios is not None
        assert equity is not None and revenue_ttm is not None and total_assets is not None and total_liabilities is not None
        x1, x2, x3 = working_capital / total_assets, retained / total_assets, op_for_ratios / total_assets
        x4, x5 = equity / total_liabilities, revenue_ttm / total_assets
        altman_z = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5

    cf_last_items = _sorted_asc(_items(cashflow))
    cf_last = _cf_row(cf_last_items[-1].get("data") or {}) if cf_last_items else {}
    fcf_q = None
    if cf_last.get("op") is not None:
        fcf_q = cf_last["op"] + (cf_last.get("capex") or 0.0)

    quarterly = []
    for it in _sorted_asc(inc_items)[-12:]:
        d = it.get("data") or {}
        quarterly.append({
            "year": str(it.get("year") or ""),
            "quarter": str(it.get("quarter") or ""),
            "label": it.get("label"),
            "revenue": _rev_of(d),
            "gross": _pick(d, _INCOME_CANDIDATES["gross_profit"]),
            "net": _pick(d, _INCOME_CANDIDATES["net_income"]),
            "eps": _eps_of(d),
        })

    payload["valuation"].update({
        "pe_ann": ratio(market_cap, net_ann),
        "p_cf": ratio(market_cap, op_cf),
        "p_fcf": ratio(market_cap, fcf),
        "ev": ev,
        "ev_ebit": ratio(ev, op_for_ratios),
        "peg": peg,
        "peg_3yr": peg_3yr,
    })
    payload["income_q"] = {
        "revenue": rev_q,
        "gross_profit": gross_q,
        "operating_profit": op_q,
        "net_income": net_q,
        "eps": eps_q,
    }
    payload["balance"].update({
        "working_capital": working_capital,
        "long_term_debt": lt_debt,
        "short_term_debt": st_debt,
        "total_debt": total_debt,
        "net_debt": net_debt,
        "common_equity": common_equity,
        "inventory": inventory,
        "receivables": receivables,
        "payables": payables,
    })
    payload["per_share"].update({
        "eps_ann": eps_ann,
        "cash": ratio(cash, shares),
        "fcf": ratio(fcf, shares),
    })
    payload["profitability"] = {
        "gross_margin": (gross_q / rev_q * 100) if (gross_q is not None and rev_q) else None,
        "operating_margin": (op_q / rev_q * 100) if (op_q is not None and rev_q) else None,
        "net_margin": (net_q / rev_q * 100) if (net_q is not None and rev_q) else None,
    }
    payload["growth"]["gross_yoy"] = _growth(inc_items, "gross_profit")
    payload["solvency"].update({
        "quick_ratio": ((current_assets - inventory) / current_liabilities) if (current_assets is not None and inventory is not None and current_liabilities) else None,
        "lt_debt_equity": ratio(lt_debt, equity),
        "total_debt_assets": ratio(total_debt, total_assets),
        "financial_leverage": ratio(total_assets, equity),
        "interest_coverage": (pretax_ttm / abs(interest_ttm)) if (pretax_ttm is not None and interest_ttm) else None,
        "fcf_q": fcf_q,
        "altman_z": altman_z,
    })
    payload["effectiveness"] = {
        "roa": roa,
        "roe": roe,
        "roce": roce,
        "roic": roic,
        "dso": dso,
        "dio": dio,
        "dpo": dpo,
        "ccc": ccc,
        "receivables_turnover": ratio(revenue_ttm, receivables) if (receivables is not None and receivables > 0) else None,
        "asset_turnover": ratio(revenue_ttm, total_assets),
        "inventory_turnover": ratio(cogs_abs, inventory) if (inventory is not None and inventory > 0) else None,
    }
    payload["quarterly"] = quarterly
    payload["quarterly_meta"] = {"market_cap": market_cap, "ev": ev, "shares": shares}

    return payload
