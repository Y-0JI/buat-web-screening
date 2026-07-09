import time
import random
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime, timedelta
from app.config import settings
from yfinance.exceptions import YFRateLimitError


_last_request_time: float = 0
_cache: dict[str, tuple[float, pd.DataFrame]] = {}
_cache_ttl = settings.cache_ttl_seconds


MOCK_DATA = {
    "BBCA": {"base_price": 6150, "vol_avg": 180_000_000},
    "BBRI": {"base_price": 5200, "vol_avg": 350_000_000},
    "BMRI": {"base_price": 6800, "vol_avg": 220_000_000},
    "TLKM": {"base_price": 3200, "vol_avg": 150_000_000},
    "UNVR": {"base_price": 3800, "vol_avg": 40_000_000},
    "ASII": {"base_price": 5800, "vol_avg": 80_000_000},
    "MDKA": {"base_price": 3100, "vol_avg": 250_000_000},
    "ADRO": {"base_price": 3500, "vol_avg": 180_000_000},
    "RGAS": {"base_price": 1200, "vol_avg": 50_000_000},
    "AKRA": {"base_price": 1400, "vol_avg": 35_000_000},
    "GOTO": {"base_price": 85, "vol_avg": 5_000_000_000},
    "BBNI": {"base_price": 4800, "vol_avg": 100_000_000},
    "CPIN": {"base_price": 5500, "vol_avg": 30_000_000},
    "ICBP": {"base_price": 10500, "vol_avg": 15_000_000},
    "INDF": {"base_price": 7200, "vol_avg": 25_000_000},
}


def resolve_ticker(symbol: str) -> str:
    s = symbol.strip().upper()
    if not s.endswith(".JK"):
        s += ".JK"
    return s


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]) for col in df.columns]
    df.columns = [c.capitalize() for c in df.columns]
    keep = {"Open", "High", "Low", "Close", "Volume"}
    for c in list(df.columns):
        if c not in keep:
            df = df.drop(columns=[c])
    return df


def _get_cached(ticker: str) -> pd.DataFrame | None:
    entry = _cache.get(ticker)
    if entry:
        ts, df = entry
        if time.time() - ts < _cache_ttl:
            return df
        del _cache[ticker]
    return None


def _set_cache(ticker: str, df: pd.DataFrame):
    _cache[ticker] = (time.time(), df)


def _generate_mock_data(symbol: str, period: str = "6mo") -> pd.DataFrame:
    clean = symbol.upper().replace(".JK", "")
    base = MOCK_DATA.get(clean, {"base_price": 1000, "vol_avg": 100_000_000})
    base_price = base["base_price"]
    vol_avg = base["vol_avg"]

    days = 120 if "6mo" in period else (30 if "1mo" in period else 252)
    end_date = datetime.now()
    dates = [end_date - timedelta(days=i) for i in range(days)]
    dates.reverse()

    data = []
    price = base_price * (0.92 + random.random() * 0.08)
    for d in dates:
        if d.weekday() >= 5:
            continue
        change = (random.random() - 0.48) * 0.04
        price *= (1 + change)
        vol = int(vol_avg * (0.3 + random.random() * 1.4))
        high = price * (1 + random.random() * 0.025)
        low = price * (1 - random.random() * 0.025)
        open_p = low + random.random() * (high - low)
        data.append({
            "Date": d,
            "Open": round(open_p, 2),
            "High": round(high, 2),
            "Low": round(low, 2),
            "Close": round(price, 2),
            "Volume": vol,
        })

    df = pd.DataFrame(data)
    df.set_index("Date", inplace=True)
    return df


def _try_yfinance(symbol: str) -> pd.DataFrame | None:
    import yfinance as yf
    t = yf.Ticker(symbol)
    df = t.history(period=settings.yfinance_period)
    if df is not None and not df.empty:
        return _flatten_columns(df)
    return None


def fetch_stock_data(symbol: str) -> pd.DataFrame | None:
    ticker_str = resolve_ticker(symbol)

    cached = _get_cached(ticker_str)
    if cached is not None:
        return cached

    yf_result = None
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_try_yfinance, ticker_str)
            yf_result = future.result(timeout=20)
    except TimeoutError:
        yf_result = None
    except Exception:
        yf_result = None

    if yf_result is not None:
        _set_cache(ticker_str, yf_result)
        return yf_result

    mock = _generate_mock_data(ticker_str, settings.yfinance_period)
    _set_cache(ticker_str, mock)
    return mock


def fetch_company_info(symbol: str) -> dict:
    clean = symbol.upper().replace(".JK", "")
    company_name = f"PT {clean} Tbk"
    sector = None

    try:
        import yfinance as yf
        stock = yf.Ticker(resolve_ticker(symbol))
        info = stock.info
        n = info.get("longName", info.get("shortName", ""))
        if n:
            company_name = n
        sector = info.get("sector")
    except Exception:
        pass

    return {"name": company_name, "sector": sector, "market_cap": None}


def clear_cache():
    _cache.clear()
