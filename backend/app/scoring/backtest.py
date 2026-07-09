import pandas as pd
import numpy as np


def estimate_confidence(df: pd.DataFrame, condition_flags: list[bool]) -> float:
    base = sum(condition_flags) / max(len(condition_flags), 1) * 100

    if len(df) < 10:
        return round(min(base * 0.9 + 10, 95), 1)

    lookback = min(len(df), 60)
    recent = df.tail(lookback).copy()
    recent["return"] = recent["Close"].pct_change().shift(-1)

    up_days = (recent["return"] > 0).sum()
    consistency = up_days / max(len(recent) - 1, 1)

    adjusted = base * (0.5 + 0.5 * consistency)
    return round(min(adjusted, 95), 1)
