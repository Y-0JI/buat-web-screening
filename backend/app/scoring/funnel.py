import pandas as pd
from app.schemas.stock import IndicatorData, ScoreBreakdown, Verdict, StockReport
from app.indicators.engine import compute_all
from app.scoring.profiles import get_profile
from app.scoring.layers import (
    score_closing_strength,
    score_gap_classification,
    score_vwap_bias,
    score_opening_range,
)
from app.scoring.backtest import estimate_confidence


def score_liquidity(df: pd.DataFrame, min_vol: int = 1_000_000) -> tuple[float, str]:
    avg_vol = df["Volume"].tail(20).mean()
    if avg_vol < min_vol:
        return 0, f"Volume terlalu rendah (< {min_vol})"
    if avg_vol < 5_000_000:
        return 40, "Likuiditas rendah"
    if avg_vol < 20_000_000:
        return 70, "Likuiditas cukup"
    return 100, "Likuiditas tinggi"


def score_trend(ind: IndicatorData) -> tuple[float, str]:
    if not ind.ema or len(ind.ema) < 3:
        return 50, "Data tren tidak cukup"
    ema20 = ind.ema.get("EMA_20", 0)
    ema50 = ind.ema.get("EMA_50", 0)
    if ema20 > ema50:
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


def compute_stop_loss(df: pd.DataFrame, ind: IndicatorData, verdict: Verdict) -> float | None:
    if ind.atr is None or df.empty:
        return None
    close = df["Close"].iloc[-1]
    if verdict in (Verdict.BUY, Verdict.HOLD):
        return round(close - (ind.atr * 1.5), 2)
    return None


def evaluate_confluence(
    profile: dict, df: pd.DataFrame, ind: IndicatorData, veto: bool, scores: dict
) -> tuple[Verdict, float, list[str]]:
    buy_rules = profile["confluence"]["buy_conditions"]
    sell_rules = profile["confluence"]["sell_conditions"]

    flags = []
    uptrend = scores.get("Tren", 50) > 50 if "Tren" in scores else False
    strong_close = scores.get("ClosingStrength", 50) >= 65 if "ClosingStrength" in scores else False
    vol_ok = scores.get("Volume", 50) >= 65 if "Volume" in scores else False
    gap_cont = scores.get("GapClassification", 50) >= 70 if "GapClassification" in scores else False
    gap_exh = scores.get("GapClassification", 50) <= 40 if "GapClassification" in scores else False

    cond_buy = []
    cond_sell = []

    for rule in buy_rules:
        if rule == "uptrend_or_strong_close":
            c = uptrend or strong_close
            cond_buy.append(c)
            flags.append(c)
        elif rule == "volume_confirmed":
            c = vol_ok
            cond_buy.append(c)
            flags.append(c)
        elif rule == "no_veto":
            c = not veto
            cond_buy.append(c)
            flags.append(c)
        elif rule == "gap_continuation":
            c = gap_cont
            cond_buy.append(c)
            flags.append(c)

    for rule in sell_rules:
        if rule == "downtrend_or_reject":
            c = not uptrend or not strong_close
            cond_sell.append(c)
            flags.append(c)
        elif rule == "volume_confirmed":
            c = vol_ok
            cond_sell.append(c)
            flags.append(c)
        elif rule == "gap_exhaustion":
            c = gap_exh
            cond_sell.append(c)
            flags.append(c)

    buy_met = all(cond_buy) if cond_buy else False
    sell_met = all(cond_sell) if cond_sell else False

    if veto or not cond_buy:
        buy_met = False

    if veto:
        sell_met = False

    if buy_met:
        verdict = Verdict.BUY
    elif sell_met:
        verdict = Verdict.SELL
    else:
        verdict = Verdict.HOLD

    confidence = estimate_confidence(df, flags, verdict)

    return verdict, confidence, flags


def calculate_score(df: pd.DataFrame, ticker: str, mode: str = "BSJP", is_simulated: bool = False) -> StockReport:
    ind = compute_all(df)
    profile = get_profile(mode)
    close = float(df["Close"].iloc[-1]) if not df.empty else 0
    change = (
        float(((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]) * 100)
        if len(df) > 1
        else 0
    )

    is_bpjs = mode.upper() == "BPJS"
    min_vol = profile["veto"]["min_avg_volume"]

    layer_scores = {}
    veto = False

    for layer_def in profile["layers"]:
        name = layer_def["name"]

        if name == "Likuiditas":
            sc, note = score_liquidity(df, min_vol)
        elif name == "ClosingStrength":
            sc, note = score_closing_strength(df)
        elif name == "GapClassification":
            sc, note = score_gap_classification(df)
        elif name == "Momentum":
            sc, note = score_momentum(ind)
        elif name == "Volume":
            sc, note = score_volume(ind)
        elif name == "Struktur":
            sc, note = score_structure(ind)
        elif name == "VwapBias":
            sc, note = score_vwap_bias(df)
        else:
            sc, note = 50, "Layer tidak dikenal"

        layer_scores[name] = (sc, note)
        if sc == 0:
            veto = True

    if veto:
        total = 0
    else:
        total = sum(
            layer_scores[d["name"]][0] * d["weight"]
            for d in profile["layers"]
            if d["name"] in layer_scores
        )

    total = round(total, 1)
    layer_scores_num = {k: v[0] for k, v in layer_scores.items()}
    verdict, confidence, _ = evaluate_confluence(profile, df, ind, veto, layer_scores_num)

    if veto:
        verdict = Verdict.SELL if not is_bpjs else Verdict.AVOID

    stop_loss = compute_stop_loss(df, ind, verdict)

    breakdown = []
    for d in profile["layers"]:
        nm = d["name"]
        if nm in layer_scores:
            breakdown.append(ScoreBreakdown(
                funnel_layer=nm,
                score=layer_scores[nm][0],
                weight=d["weight"],
                note=layer_scores[nm][1],
            ))

    summary_parts = []
    if veto:
        summary_parts.append(f"Gagal filter awal ({profile['veto']['description']}).")
    for b in breakdown:
        summary_parts.append(f"{b.funnel_layer}: {b.score} (x{b.weight})")
    summary_parts.append(f"Mode: {profile['label']} | Verdict: {verdict.value} (confidence {confidence}%)")

    return StockReport(
        ticker=ticker.upper(),
        score=total,
        verdict=verdict,
        confidence=confidence,
        summary=" | ".join(summary_parts),
        indicators=ind,
        score_breakdown=breakdown,
        stop_loss=stop_loss,
        price=round(close, 2),
        change_percent=round(change, 2),
        is_simulated=is_simulated,
    )
