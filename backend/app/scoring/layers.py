import pandas as pd
import numpy as np


def score_closing_strength(df: pd.DataFrame) -> tuple[float, str]:
    if len(df) < 1:
        return 50, "Data tidak cukup"
    close = df["Close"].iloc[-1]
    high = df["High"].iloc[-1]
    low = df["Low"].iloc[-1]
    rng = high - low
    if rng == 0:
        return 50, "Range 0"
    ratio = (close - low) / rng
    if ratio >= 0.8:
        return 85, "Strong close dekat high"
    if ratio >= 0.6:
        return 65, "Close moderat di atas midpoint"
    if ratio >= 0.4:
        return 45, "Close di midpoint"
    if ratio >= 0.2:
        return 30, "Close lemah dekat low"
    return 15, "Reject dari atas (close dekat low)"


def score_gap_classification(df: pd.DataFrame) -> tuple[float, str]:
    if len(df) < 3:
        return 50, "Data tidak cukup"
    gap_pct = ((df["Open"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100
    prev_change = ((df["Close"].iloc[-2] - df["Close"].iloc[-3]) / df["Close"].iloc[-3]) * 100
    vol_ratio = _vol_ratio_simple(df)

    if gap_pct > 1:
        if prev_change > 0 and vol_ratio > 1.2:
            return 80, "Gap continuation naik (didukung tren & volume)"
        return 40, "Gap exhaustion — rawan fade"
    elif gap_pct < -1:
        if prev_change < 0 and vol_ratio > 1.2:
            return 75, "Gap continuation turun"
        return 35, "Gap exhaustion turun"
    return 50, "Gap minimal / tidak ada gap"


def score_vwap_bias(df: pd.DataFrame) -> tuple[float, str]:
    if df.empty:
        return 50, "Data tidak cukup"
    close = df["Close"].iloc[-1]
    vwap = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).sum() / df["Volume"].sum()
    if vwap == 0:
        return 50, "VWAP 0"
    bias = ((close - vwap) / vwap) * 100
    if bias > 1:
        return 70, "Harga di atas VWAP (bullish bias)"
    if bias < -1:
        return 30, "Harga di bawah VWAP (bearish bias)"
    return 50, "Harga di sekitar VWAP (netral)"


def score_opening_range(df: pd.DataFrame) -> tuple[float, str]:
    return 50, "Data intraday tidak tersedia (estimasi dari data harian)"


def _vol_ratio_simple(df: pd.DataFrame, window: int = 20) -> float:
    if len(df) < window + 1:
        return 1.0
    avg_vol = df["Volume"].iloc[-window - 1 : -1].mean()
    if avg_vol == 0:
        return 1.0
    return df["Volume"].iloc[-1] / avg_vol
