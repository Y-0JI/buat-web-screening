import pandas as pd
import numpy as np
from app.schemas.stock import IndicatorData


def compute_ema(df: pd.DataFrame, periods: list[int] = [9, 20, 50]) -> dict:
    result = {}
    for p in periods:
        col = f"EMA_{p}"
        result[col] = round(df["Close"].ewm(span=p, adjust=False).mean().iloc[-1], 2)
    return result


def compute_rsi(df: pd.DataFrame, period: int = 14) -> float | None:
    if len(df) < period + 1:
        return None
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    # Wilder's smoothing (exponential weighted with alpha=1/period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    # Flat prices: both gain and loss are 0 → neutral RSI
    if avg_gain.iloc[-1] == 0 and avg_loss.iloc[-1] == 0:
        return 50.0
    if avg_loss.iloc[-1] == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def compute_macd(df: pd.DataFrame) -> dict:
    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    histogram = macd_line - signal
    return {
        "macd": round(float(macd_line.iloc[-1]), 2),
        "signal": round(float(signal.iloc[-1]), 2),
        "histogram": round(float(histogram.iloc[-1]), 2),
    }


def compute_atr(df: pd.DataFrame, period: int = 14) -> float | None:
    if len(df) < period:
        return None
    high, low, close = df["High"], df["Low"], df["Close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period).mean()
    return round(atr.iloc[-1], 2)


def compute_vwap(df: pd.DataFrame, window: int = 20) -> float | None:
    if len(df) < window:
        window = len(df)
    if window == 0 or df["Volume"].iloc[-window:].sum() == 0:
        return None
    segment = df.iloc[-window:]
    typical = (segment["High"] + segment["Low"] + segment["Close"]) / 3
    vwap = (segment["Volume"] * typical).sum() / segment["Volume"].sum()
    return round(float(vwap), 2)


def compute_volume_ratio(df: pd.DataFrame, window: int = 20) -> float | None:
    if len(df) < window + 1:
        return None
    avg_vol = df["Volume"].iloc[-window - 1 : -1].mean()
    if avg_vol == 0:
        return None
    return round(df["Volume"].iloc[-1] / avg_vol, 2)


def compute_gap(df: pd.DataFrame) -> float | None:
    if len(df) < 2:
        return None
    prev_close = df["Close"].iloc[-2]
    if prev_close == 0:
        return None
    return round(((df["Open"].iloc[-1] - prev_close) / prev_close) * 100, 2)


def compute_support_resistance(df: pd.DataFrame, lookback: int = 60) -> dict:
    segment = df.tail(lookback)
    if segment.empty:
        return {}
    recent_high = segment["High"].max()
    recent_low = segment["Low"].min()
    pivot = (recent_high + recent_low) / 2
    return {
        "resistance": round(recent_high, 2),
        "support": round(recent_low, 2),
        "pivot": round(pivot, 2),
    }


def compute_all(df: pd.DataFrame) -> IndicatorData:
    return IndicatorData(
        ema=compute_ema(df),
        rsi=compute_rsi(df),
        macd=compute_macd(df),
        atr=compute_atr(df),
        vwap=compute_vwap(df),
        volume_ratio=compute_volume_ratio(df),
        gap_percent=compute_gap(df),
        support_resistance=compute_support_resistance(df),
    )
