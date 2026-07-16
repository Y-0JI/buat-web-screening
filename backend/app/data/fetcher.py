import asyncio
import logging
import time
import random
import threading
import pandas as pd
from datetime import datetime, timedelta
from app.config import settings
from yfinance.exceptions import YFRateLimitError

logger = logging.getLogger(__name__)


_cache: dict[str, tuple[float, pd.DataFrame, bool]] = {}
_verify_cache: dict[str, tuple[float, bool]] = {}
_VERIFY_CACHE_TTL = 300  # 5 minutes
_cache_ttl = settings.cache_ttl_seconds
_cache_lock = threading.Lock()
_rate_lock = threading.Lock()
_last_request_time: float = 0
_MIN_REQUEST_INTERVAL = 1.0
_in_flight: dict[str, asyncio.Future] = {}
_in_flight_lock = threading.Lock()


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


def _get_cached(ticker: str) -> tuple[pd.DataFrame, bool] | None:
    entry = _cache.get(ticker)
    if entry:
        ts, df, is_simulated = entry
        if time.time() - ts < _cache_ttl:
            return df, is_simulated
        del _cache[ticker]
    return None


def _get_cached_verify(ticker: str) -> bool | None:
    entry = _verify_cache.get(ticker)
    if entry:
        ts, is_simulated = entry
        if time.time() - ts < _VERIFY_CACHE_TTL:
            return is_simulated
        del _verify_cache[ticker]
    return None


def _set_cache(ticker: str, df: pd.DataFrame, is_simulated: bool = False):
    _cache[ticker] = (time.time(), df, is_simulated)


def _set_verify_cache(ticker: str, is_simulated: bool):
    _verify_cache[ticker] = (time.time(), is_simulated)


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
    tf = yf.Ticker(symbol)
    df = tf.history(period=settings.yfinance_period)
    if df is not None and not df.empty:
        return _flatten_columns(df)
    return None


async def _rate_limit():
    global _last_request_time
    with _rate_lock:
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()


async def fetch_stock_data(symbol: str, fast_fail: bool = False) -> tuple[pd.DataFrame | None, bool]:
    ticker_str = resolve_ticker(symbol)

    with _cache_lock:
        cached = _get_cached(ticker_str)
        if cached is not None:
            return cached

    existing: asyncio.Future | None = None
    with _in_flight_lock:
        if ticker_str in _in_flight:
            existing = _in_flight[ticker_str]
        else:
            loop = asyncio.get_running_loop()
            _in_flight[ticker_str] = loop.create_future()

    if existing is not None:
        try:
            return await existing
        except Exception:
            return None, False

    try:
        await _rate_limit()

        timeouts = [5] if fast_fail else [8, 5, 4]
        yf_result = None
        for attempt, to in enumerate(timeouts):
            try:
                yf_result = await asyncio.wait_for(
                    asyncio.to_thread(_try_yfinance, ticker_str),
                    timeout=to,
                )
                if yf_result is not None:
                    break
            except YFRateLimitError as e:
                logger.warning(
                    "%s | yfinance rate-limit (attempt %d/%d) — %s",
                    ticker_str, attempt + 1, len(timeouts), e,
                )
                if not fast_fail and attempt < len(timeouts) - 1:
                    await asyncio.sleep(10)
                continue
            except asyncio.TimeoutError as e:
                logger.warning(
                    "%s | yfinance timeout (attempt %d/%d) — %s",
                    ticker_str, attempt + 1, len(timeouts), e,
                )
                if not fast_fail and attempt < len(timeouts) - 1:
                    await asyncio.sleep(1)
                continue
            except Exception as e:
                logger.warning(
                    "%s | yfinance error (attempt %d/%d) — %s",
                    ticker_str, attempt + 1, len(timeouts), e,
                )
                if not fast_fail and attempt < len(timeouts) - 1:
                    await asyncio.sleep(1)
                continue

        if yf_result is not None:
            with _cache_lock:
                _set_cache(ticker_str, yf_result, is_simulated=False)
            result = (yf_result, False)
        else:
            mock = _generate_mock_data(ticker_str, settings.yfinance_period)
            with _cache_lock:
                _set_cache(ticker_str, mock, is_simulated=True)
            result = (mock, True)

        with _in_flight_lock:
            fut = _in_flight.pop(ticker_str, None)
        if fut is not None and not fut.done():
            fut.set_result(result)

        return result
    except Exception as exc:
        with _in_flight_lock:
            fut = _in_flight.pop(ticker_str, None)
        if fut is not None and not fut.done():
            fut.set_exception(exc)
        raise


async def verify_ticker(candidate: str) -> bool:
    """Cek apakah candidate adalah ticker IDX yang benar-benar ada, lewat data live
    yfinance. TIDAK menerima hasil simulasi/mock sebagai bukti valid.
    Uses its own cache to avoid polluting the main data cache."""
    ticker_str = resolve_ticker(candidate)

    with _cache_lock:
        cached = _get_cached_verify(ticker_str)
        if cached is not None:
            return not cached  # is_simulated=False means valid

    def _try_verify() -> pd.DataFrame | None:
        try:
            import yfinance as yf
            tf = yf.Ticker(ticker_str)
            df = tf.history(period="5d")
            if df is not None and not df.empty:
                return _flatten_columns(df)
        except Exception:
            pass
        return None

    try:
        await _rate_limit()
        yf_result = await asyncio.wait_for(asyncio.to_thread(_try_verify), timeout=8)
    except Exception:
        yf_result = None

    is_simulated = yf_result is None

    with _cache_lock:
        _set_verify_cache(ticker_str, is_simulated)

    return yf_result is not None and not yf_result.empty


async def fetch_history(symbol: str, period: str = "6mo") -> tuple[pd.DataFrame | None, bool]:
    ticker_str = resolve_ticker(symbol)

    if period == settings.yfinance_period:
        return await fetch_stock_data(symbol)

    def _sync() -> pd.DataFrame | None:
        try:
            import yfinance as yf
            tf = yf.Ticker(ticker_str)
            df = tf.history(period=period)
            if df is not None and not df.empty:
                return _flatten_columns(df)
        except Exception:
            pass
        return None

    try:
        await _rate_limit()
        df = await asyncio.wait_for(asyncio.to_thread(_sync), timeout=8)
        if df is not None:
            return df, False
    except Exception:
        pass

    mock = _generate_mock_data(ticker_str, period)
    return mock, True


async def fetch_company_info(symbol: str) -> dict:
    clean = symbol.upper().replace(".JK", "")

    def _fetch() -> dict:
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

    return await asyncio.to_thread(_fetch)


# ── Modular data category caches ──────────────────────────────────────────────
# Each category has independent cache dict, TTL, and fetch function.
# Design: easy to add new categories (earnings, recommendations, etc.) later.

_NEWS_CACHE: dict[str, tuple[float, dict]] = {}
_NEWS_TTL = 900  # 15 minutes
_FUNDAMENTALS_CACHE: dict[str, tuple[float, dict]] = {}
_FUNDAMENTALS_TTL = 3600  # 1 hour


def _modular_cache_get(cache: dict, key: str, ttl: int) -> dict | None:
    entry = cache.get(key)
    if entry:
        ts, data = entry
        if time.time() - ts < ttl:
            return data
        del cache[key]
    return None


def _modular_cache_set(cache: dict, key: str, data: dict):
    cache[key] = (time.time(), data)


async def fetch_news(symbol: str, limit: int = 10) -> dict:
    """Fetch recent news for a ticker from Yahoo Finance.

    Returns:
        {\"items\": [...], \"fetched_at\": \"...\"} on success
        {\"error\": \"...\", \"fetched_at\": null} on failure
    """
    clean = symbol.upper().replace(".JK", "")
    cache_key = f"{clean}:{limit}"

    with _cache_lock:
        cached = _modular_cache_get(_NEWS_CACHE, cache_key, _NEWS_TTL)
        if cached is not None:
            return cached

    def _fetch() -> dict:
        try:
            import yfinance as yf
            stock = yf.Ticker(resolve_ticker(symbol))
            raw_news = stock.news
            if not raw_news:
                return {
                    "items": [],
                    "fetched_at": datetime.now().isoformat(),
                }
            items = []
            for n in raw_news[:limit]:
                content = n.get("content", {})
                items.append({
                    "title": content.get("title", n.get("title", "")),
                    "publisher": content.get("provider", {}).get("displayName", ""),
                    "link": content.get("canonicalUrl", {}).get("url", ""),
                    "published": content.get("pubDate", ""),
                    "summary": content.get("summary", ""),
                })
            return {
                "items": items,
                "fetched_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning("%s | fetch_news error: %s", clean, e)
            return {
                "error": f"Gagal mengambil berita: {e}",
                "fetched_at": None,
            }

    try:
        await _rate_limit()
        result = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=10)
    except asyncio.TimeoutError:
        logger.warning("%s | fetch_news timeout", clean)
        result = {"error": "Timeout mengambil berita", "fetched_at": None}
    except Exception as e:
        logger.warning("%s | fetch_news error: %s", clean, e)
        result = {"error": f"Gagal mengambil berita: {e}", "fetched_at": None}

    with _cache_lock:
        if not result.get("error"):
            _modular_cache_set(_NEWS_CACHE, cache_key, result)
    return result


async def fetch_fundamentals(symbol: str) -> dict:
    """Fetch fundamental data for a ticker from Yahoo Finance.

    Returns:
        {\"market_cap\": ..., \"pe\": ..., ...} on success
        {\"error\": \"...\", \"fetched_at\": null} on failure
    """
    clean = symbol.upper().replace(".JK", "")

    with _cache_lock:
        cached = _modular_cache_get(_FUNDAMENTALS_CACHE, clean, _FUNDAMENTALS_TTL)
        if cached is not None:
            return cached

    def _fetch() -> dict:
        try:
            import yfinance as yf
            stock = yf.Ticker(resolve_ticker(symbol))
            info = stock.info or {}

            fast = {}
            try:
                fi = stock.fast_info
                fast = {
                    "market_cap": getattr(fi, "market_cap", None),
                    "shares_outstanding": getattr(fi, "shares", None),
                    "previous_close": getattr(fi, "previous_close", None),
                    "last_price": getattr(fi, "last_price", None),
                }
            except Exception:
                pass

            return {
                "market_cap": fast.get("market_cap") or info.get("marketCap"),
                "previous_close": fast.get("previous_close") or info.get("previousClose"),
                "last_price": fast.get("last_price"),
                "shares_outstanding": fast.get("shares_outstanding") or info.get("sharesOutstanding"),
                "pe": info.get("trailingPE") or info.get("forwardPE"),
                "forward_pe": info.get("forwardPE"),
                "pb": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "trailing_annual_dividend_yield": info.get("trailingAnnualDividendYield"),
                "beta": info.get("beta"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "fifty_day_average": info.get("fiftyDayAverage"),
                "two_hundred_day_average": info.get("twoHundredDayAverage"),
                "avg_volume_10d": info.get("averageDailyVolume10Day"),
                "avg_volume_3m": info.get("averageDailyVolume3Month"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "description": info.get("longBusinessSummary", ""),
                "website": info.get("website"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "fetched_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning("%s | fetch_fundamentals error: %s", clean, e)
            return {
                "error": f"Gagal mengambil data fundamental: {e}",
                "fetched_at": None,
            }

    try:
        await _rate_limit()
        result = await asyncio.wait_for(asyncio.to_thread(_fetch), timeout=10)
    except asyncio.TimeoutError:
        logger.warning("%s | fetch_fundamentals timeout", clean)
        result = {"error": "Timeout mengambil data fundamental", "fetched_at": None}
    except Exception as e:
        logger.warning("%s | fetch_fundamentals error: %s", clean, e)
        result = {"error": f"Gagal mengambil data fundamental: {e}", "fetched_at": None}

    with _cache_lock:
        if not result.get("error"):
            _modular_cache_set(_FUNDAMENTALS_CACHE, clean, result)
    return result


def clear_cache():
    _cache.clear()
    _verify_cache.clear()
    _NEWS_CACHE.clear()
    _FUNDAMENTALS_CACHE.clear()
