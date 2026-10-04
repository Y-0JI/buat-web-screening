"""Test normalisasi fundamental bank vs non-bank + rasio baru (tanpa jaringan).

Jalan: ./.venv/bin/python test_fundamentals.py
"""

import asyncio
import sys
from datetime import date

sys.path.insert(0, ".")

from app.fundamentals import (
    _eps_of,
    _growth_n,
    _op_of,
    _rev_of,
    _seek,
    build_fundamentals,
)


def _inc_bank(year, quarter, net, op=None, rev_total=None, eps_detail=None):
    data = {
        "laba_rugi": net,
        "laba_rugi_sebelum_pajak_penghasilan": int(net * 1.25),
        "pendapatan_beban_pajak": -int(net * 0.25),
        "beban_bunga": -int(net * 0.3),
    }
    if op is not None:
        data["laba_operasional"] = op
    if rev_total is not None:
        data["pendapatan_dan_beban_operasional"] = {"total": rev_total}
    data["laba_rugi_per_saham"] = {"laba_per_saham_dasar": eps_detail, "total": 0.0} if eps_detail else {"total": 0.0}
    return {"year": str(year), "quarter": str(quarter), "label": f"Q{quarter} {year}", "data": data}


def _inc_nonbank(year, quarter, rev, net, eps=None):
    data = {
        "penjualan_dan_pendapatan_usaha": rev,
        "laba_bruto": int(rev * 0.3),
        "beban_umum_dan_administrasi": -int(rev * 0.1),
        "laba_rugi_sebelum_pajak_penghasilan": int(net * 1.3),
        "pendapatan_beban_pajak": -int(net * 0.3),
        "laba_rugi": net,
    }
    if eps is not None:
        data["laba_rugi_per_saham"] = {"detail": {"total": eps}}
    return {"year": str(year), "quarter": str(quarter), "label": f"Q{quarter} {year}", "data": data}


def _bs(equity, liab, assets, extra=None):
    data = {
        "aset": {"total": assets, "aset": assets},
        "liabilitas_dan_ekuitas": {
            "liabilitas": {"total": liab, "liabilitas": liab},
            "ekuitas": {"total": equity, "ekuitas": equity},
        },
    }
    if extra:
        data.update(extra)
    return {"year": "2026", "quarter": "1", "label": "Q1 2026", "data": data}


def _cf_row(op, capex):
    return {"year": "2026", "quarter": "1", "label": "Q1 2026", "data": {
        "arus_kas_dari_aktivitas_operasi": {"total": op},
        "arus_kas_dari_aktivitas_investasi": {"total": -10.0, "pembayaran_untuk_perolehan_aset_tetap": capex},
        "arus_kas_dari_aktivitas_pendanaan": {"total": 5.0},
    }}


class FakeProvider:
    def __init__(self, income, balance, cashflow, mcap):
        self._income = income
        self._balance = balance
        self._cashflow = cashflow
        self._mcap = mcap

    async def fetch_financial_statements(self, code, report_type=None, period=None, limit=None):
        table = {"INCOME_STATEMENT": self._income, "BALANCE_SHEET": self._balance, "CASH_FLOW_REPORT": self._cashflow}
        rows = table.get(report_type or "", [])
        return {"items": rows[: limit or len(rows)]}

    async def fetch_market_cap(self, page=1, per_page=50, codes=None):
        return {"data": [self._mcap]}

    async def fetch_history(self, code, frame="daily", limit=160):
        year = date.today().year
        return [{"date": f"{year}-01-{i + 1:02d}", "open": 100, "high": 105, "low": 99, "close": 100 + i, "volume": 10} for i in range(30)]


def _bank_provider(growth_ok=True):
    base = 1000.0 if growth_ok else 1000.0
    income = [
        _inc_bank(2025, 1, base, op=1200.0, rev_total=1500.0, eps_detail=10.0),
        _inc_bank(2025, 2, base, op=1200.0, rev_total=1500.0, eps_detail=10.0),
        _inc_bank(2025, 3, base, op=1200.0, rev_total=1500.0, eps_detail=10.0),
        _inc_bank(2025, 4, base, op=1200.0, rev_total=1500.0, eps_detail=10.0),
        _inc_bank(2026, 1, base * (1.2 if growth_ok else 0.8), op=1400.0, rev_total=1700.0, eps_detail=12.0),
    ]
    return FakeProvider(
        income,
        [_bs(5000.0, 9000.0, 14000.0)],
        [_cf_row(800.0, -100.0) for _ in range(4)],
        {"code": "BANK", "market_cap": 40000.0, "listed_shares": 1000.0},
    )


def _nonbank_provider():
    income = [
        _inc_nonbank(2025, 1, 5000.0, 500.0, eps=5.0),
        _inc_nonbank(2025, 2, 5000.0, 500.0, eps=5.0),
        _inc_nonbank(2025, 3, 5000.0, 500.0, eps=5.0),
        _inc_nonbank(2025, 4, 5000.0, 500.0, eps=5.0),
        _inc_nonbank(2026, 1, 5500.0, 600.0, eps=6.0),
    ]
    return FakeProvider(
        income,
        [_bs(3000.0, 1500.0, 4500.0)],
        [_cf_row(400.0, -50.0) for _ in range(4)],
        {"code": "NB", "market_cap": 12000.0, "listed_shares": 500.0},
    )


def test_seek_group_total_and_exclude():
    d = {
        "piutang_usaha": {"piutang_usaha_pihak_ketiga": 100.0, "total": 120.0},
        "liabilitas": {"utang_usaha": {"total": 50.0}},
    }
    assert _seek(d, "piutang_usaha") == 120.0
    assert _seek(d, "utang_usaha") == 120.0  # grup piutang cocok dulu -> totalnya
    assert _seek(d, "utang_usaha", exclude="piutang") == 50.0


def test_eps_and_op_extraction():
    assert _eps_of({"laba_per_saham_dasar": 7.0}) == 7.0
    assert _eps_of({"laba_rugi_per_saham": {"detail": 9.0, "total": 9.0}}) == 9.0
    assert _op_of({"laba_operasional": 100.0}) == 100.0
    assert _op_of({"laba_bruto": 300.0, "beban_umum_dan_administrasi": -100.0}) == 200.0
    assert _op_of({"laba_bruto": 300.0, "beban_umum_dan_administrasi": 100.0}) == 200.0
    assert _op_of({"laba_bruto": 300.0}) is None
    assert _rev_of({"pendapatan": 500.0}) == 500.0
    assert _rev_of({"pendapatan_dan_beban_operasional": {"total": 700.0}}) == 700.0


def test_growth_n():
    items = [
        {"year": "2023", "quarter": "1", "data": {"laba_rugi": 100.0}},
        {"year": "2024", "quarter": "1", "data": {"laba_rugi": 110.0}},
        {"year": "2025", "quarter": "1", "data": {"laba_rugi": 121.0}},
        {"year": "2026", "quarter": "1", "data": {"laba_rugi": 133.1}},
    ]
    assert abs((_growth_n(items, "net_income", 1) or 0) - 10.0) < 0.01
    assert abs((_growth_n(items, "net_income", 3) or 0) - 33.1) < 0.01
    assert _growth_n(items[:1], "net_income", 1) is None


def _run(code: str, provider, full: bool) -> dict:
    d = asyncio.run(build_fundamentals(code, provider=provider, full=full))
    assert isinstance(d, dict)
    return d


def test_build_bank_full():
    d = _run("BANK", _bank_provider(), True)
    assert d["income"]["revenue"] == 1500.0 * 3 + 1700.0
    assert d["income"]["operating_profit"] == 1200.0 * 3 + 1400.0
    assert d["balance"]["total_equity"] == 5000.0
    assert d["solvency"]["debt_to_equity"] == 1.8
    assert d["solvency"]["financial_leverage"] == 2.8
    assert d["effectiveness"]["roe"] == 4200.0 / 5000.0 * 100
    assert d["effectiveness"]["roa"] == 4200.0 / 14000.0 * 100
    assert d["growth"]["revenue_yoy"] == (1700.0 - 1500.0) / 1500.0 * 100
    assert d["quarterly"][-1]["revenue"] == 1700.0
    assert d["valuation"]["pbv"] == 8.0
    assert d["valuation"]["peg"] is not None and d["valuation"]["peg"] > 0
    assert d["solvency"]["interest_coverage"] is not None
    assert len(d["quarterly"]) == 5
    assert d["quarterly"][-1]["eps"] == 12.0
    assert d["quarterly_meta"]["shares"] == 1000.0
    assert any(p["period"] == "YTD" for p in d["performance"])


def test_build_bank_lean_unchanged_shape():
    d = _run("BANK", _bank_provider(), False)
    assert set(d["valuation"]) == {"market_cap", "pe", "pbv", "psr", "earnings_yield"}
    assert "effectiveness" not in d and "quarterly" not in d and "income_q" not in d


def test_build_nonbank_full():
    d = _run("NB", _nonbank_provider(), True)
    assert d["income"]["operating_profit"] == 1000.0 * 3 + 1100.0
    assert d["income"]["revenue"] == 5000.0 * 3 + 5500.0
    assert d["per_share"]["eps"] == 5.0 * 3 + 6.0
    assert d["profitability"]["net_margin"] == 600.0 / 5500.0 * 100
    assert d["solvency"]["current_ratio"] is None  # fixture tanpa aset lancar
    assert d["growth"]["gross_yoy"] == 10.0
    assert d["effectiveness"]["roe"] == 2100.0 / 3000.0 * 100
    assert d["quarterly"][-1]["revenue"] == 5500.0


def test_build_negative_growth_guards():
    d = _run("BANK", _bank_provider(growth_ok=False), True)
    assert d["valuation"]["peg"] is None  # growth negatif -> disembunyikan
    assert d["valuation"]["pe"] is not None


def main():
    test_seek_group_total_and_exclude()
    test_eps_and_op_extraction()
    test_growth_n()
    test_build_bank_full()
    test_build_bank_lean_unchanged_shape()
    test_build_nonbank_full()
    test_build_negative_growth_guards()
    print("OK: test_fundamentals lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
