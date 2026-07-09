import pandas as pd
from app.schemas.stock import IndicatorData, ScoreBreakdown, Verdict, StockReport
from app.indicators.engine import compute_all


def score_liquidity(df: pd.DataFrame) -> tuple[float, str]:
    avg_vol = df["Volume"].tail(20).mean()
    if avg_vol < 1_000_000:
        return 0, "Volume terlalu rendah"
    if avg_vol < 5_000_000:
        return 40, "Likuiditas rendah"
    if avg_vol < 20_000_000:
        return 70, "Likuiditas cukup"
    return 100, "Likuiditas tinggi"


def score_trend(ind: IndicatorData) -> tuple[float, str]:
    if ind.ema is None or len(ind.ema) < 3:
        return 50, "Data tren tidak cukup"
    price_vs_ema20 = ind.ema.get("EMA_20", 0)
    price_vs_ema50 = ind.ema.get("EMA_50", 0)
    if price_vs_ema20 > price_vs_ema50:
        return 80, "Uptrend (EMA20 > EMA50)"
    return 30, "Downtrend (EMA20 <= EMA50)"


def score_momentum(ind: IndicatorData) -> tuple[float, str]:
    if ind.rsi is None:
        return 50, "RSI tidak tersedia"
    if ind.rsi > 70:
        return 20, "Overbought (RSI > 70)"
    if ind.rsi < 30:
        return 80, "Oversold (RSI < 30) — potensi reversal"
    if ind.rsi > 50:
        return 65, "Momentum positif (RSI > 50)"
    return 40, "Momentum negatif (RSI <= 50)"


def score_volume(ind: IndicatorData) -> tuple[float, str]:
    if ind.volume_ratio is None:
        return 50, "Data volume tidak cukup"
    if ind.volume_ratio > 2:
        return 85, "Volume melonjak (>2x rata-rata)"
    if ind.volume_ratio > 1.2:
        return 65, "Volume di atas rata-rata"
    return 40, "Volume normal/redup"


def score_structure(ind: IndicatorData) -> tuple[float, str]:
    sr = ind.support_resistance
    if not sr:
        return 50, "Data struktur tidak cukup"
    return 60, f"Support {sr.get('support')} / Resistance {sr.get('resistance')}"


def compute_verdict(total_score: float) -> Verdict:
    if total_score >= 75:
        return Verdict.BUY
    if total_score >= 55:
        return Verdict.HOLD
    if total_score >= 35:
        return Verdict.SELL
    return Verdict.AVOID


def compute_confidence(total_score: float) -> float:
    return round(min(total_score * 0.9 + 10, 95), 1)


def compute_stop_loss(df: pd.DataFrame, ind: IndicatorData, verdict: Verdict) -> float | None:
    if ind.atr is None or df.empty:
        return None
    close = df["Close"].iloc[-1]
    if verdict in (Verdict.BUY, Verdict.HOLD):
        return round(close - (ind.atr * 1.5), 2)
    return None


def calculate_score(df: pd.DataFrame, ticker: str) -> StockReport:
    ind = compute_all(df)
    close = float(df["Close"].iloc[-1]) if not df.empty else 0
    change = (
        float(((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100)
        if len(df) > 1
        else 0
    )

    layers = [
        ("Likuiditas", *score_liquidity(df)),
        ("Tren", *score_trend(ind)),
        ("Momentum", *score_momentum(ind)),
        ("Volume", *score_volume(ind)),
        ("Struktur", *score_structure(ind)),
    ]

    weights = {"Likuiditas": 0.30, "Tren": 0.25, "Momentum": 0.20, "Volume": 0.15, "Struktur": 0.10}

    veto = False
    for name, score, note in layers:
        if score == 0:
            veto = True

    if veto:
        total = 0
    else:
        total = sum(score * weights[name] for name, score, note in layers)

    total = round(total, 1)
    verdict = compute_verdict(total)
    confidence = compute_confidence(total)
    stop_loss = compute_stop_loss(df, ind, verdict)

    breakdown = [
        ScoreBreakdown(funnel_layer=name, score=score, weight=weights.get(name, 0), note=note)
        for name, score, note in layers
    ]

    summary_lines = []
    if veto:
        summary_lines.append("Gagal filter awal (veto).")
    for b in breakdown:
        summary_lines.append(f"{b.funnel_layer}: {b.note} (skor {b.score})")
    summary_lines.append(f"Total skor: {total}/100 → {verdict.value} (keyakinan {confidence}%)")

    return StockReport(
        ticker=ticker.upper(),
        score=total,
        verdict=verdict,
        confidence=confidence,
        summary=" | ".join(summary_lines),
        indicators=ind,
        score_breakdown=breakdown,
        stop_loss=stop_loss,
        price=round(close, 2),
        change_percent=round(change, 2),
    )
