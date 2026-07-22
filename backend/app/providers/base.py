"""Base & helper bersama untuk Yahoo Finance Provider.

Provider HANYA bertugas mengambil data mentah dari Yahoo Finance — tidak ada
business logic, validasi domain, atau transformasi response di sini. Semua
logic rate-limit, retry, timeout, dan fallback mock (ketika yfinance gagal)
disediakan sebagai helper bersama agar setiap provider konsisten.
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Callable, Optional

import pandas as pd
from app.utils.errors import (
    NetworkError,
    ProviderTimeoutError,
    RateLimitError,
)
from yfinance.exceptions import YFRateLimitError

logger = logging.getLogger(__name__)

# Dedup request yang sedang berjalan agar fetch paralel untuk ticker sama
# tidak memanggil yfinance berulang kali.
_in_flight: dict[str, asyncio.Future] = {}
_in_flight_lock = asyncio.Lock()


MOCK_DATA: dict[str, dict] = {
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
        price *= 1 + change
        vol = int(vol_avg * (0.3 + random.random() * 1.4))
        high = price * (1 + random.random() * 0.025)
        low = price * (1 - random.random() * 0.025)
        open_p = low + random.random() * (high - low)
        data.append(
            {
                "Date": d,
                "Open": round(open_p, 2),
                "High": round(high, 2),
                "Low": round(low, 2),
                "Close": round(price, 2),
                "Volume": vol,
            }
        )

    df = pd.DataFrame(data)
    df.set_index("Date", inplace=True)
    return df


async def _run_yf(fn: Callable[[], Optional[pd.DataFrame]], timeout: int) -> Optional[pd.DataFrame]:
    """Jalankan fungsi yfinance (sync) di thread dengan timeout.

    Mengubah exception yfinance menjadi ProviderError yang sesuai.
    Mengembalikan DataFrame atau None bila yfinance tidak memberi data.
    """
    try:
        result = await asyncio.wait_for(asyncio.to_thread(fn), timeout=timeout)
        return result
    except YFRateLimitError as e:
        raise RateLimitError(f"Yahoo Finance rate-limit: {e}") from e
    except asyncio.TimeoutError as e:
        raise ProviderTimeoutError("Yahoo Finance tidak merespons (timeout).") from e
    except Exception as e:
        raise NetworkError(f"Gagal menghubungi Yahoo Finance: {e}") from e


async def _retry(coro_factory, retries: int = 3, base_delay: float = 1.0) -> any:
    """Jalankan coroutine dengan exponential backoff.

    `coro_factory` dipanggil ulang tiap percobaan. `RateLimitError` di-backoff
    lebih lama (5x) karena butuh jeda sebelum retry. Raise error terakhir bila
    semua percobaan habis.
    """
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return await coro_factory()
        except RateLimitError as e:
            last_err = e
            if attempt < retries - 1:
                delay = base_delay * 5 * (2 ** attempt)
                await asyncio.sleep(delay + random.uniform(0, delay * 0.25))
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay + random.uniform(0, delay * 0.25))
    assert last_err is not None
    raise last_err


async def _dedup(key: str, coro_factory) -> any:
    """Jalankan coroutine dengan dedup. Jika concurrent pertama gagal, retry."""
    existing: Optional[asyncio.Future] = None
    async with _in_flight_lock:
        if key in _in_flight:
            existing = _in_flight[key]
        else:
            loop = asyncio.get_running_loop()
            _in_flight[key] = loop.create_future()

    if existing is not None:
        try:
            return await existing
        except Exception:
            logger.debug("dedup %s — previous failed, retrying", key)
            async with _in_flight_lock:
                _in_flight.pop(key, None)

    if existing is not None:
        async with _in_flight_lock:
            if key not in _in_flight:
                loop = asyncio.get_running_loop()
                _in_flight[key] = loop.create_future()

    try:
        result = await coro_factory()
        async with _in_flight_lock:
            fut = _in_flight.pop(key, None)
        if fut is not None and not fut.done():
            fut.set_result(result)
        return result
    except Exception as exc:
        async with _in_flight_lock:
            fut = _in_flight.pop(key, None)
        if fut is not None and not fut.done():
            fut.set_exception(exc)
        raise
