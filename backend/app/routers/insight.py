import asyncio
import logging
from datetime import datetime
from google import genai
from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings
from app.scheduler import get_cached_screening

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insight", tags=["insight"])

_insight_cache: dict = {}
_insight_ttl = 1800  # 30 minutes


class MarketInsightResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


async def _generate_market_insight(mode: str = "BSJP") -> dict:
    results, actual_mode = await get_cached_screening(mode)
    if not results or not actual_mode:
        return {
            "summary": "Data screening belum tersedia.",
            "sentiment": "neutral",
            "score_avg": None,
            "total_stocks": 0,
            "generated_at": datetime.now().isoformat(),
        }

    scores = [r.get("score", 0) for r in results]
    verdict_counts: dict[str, int] = {}
    for r in results:
        v = r.get("verdict", "")
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    if not settings.gemini_api_key:
        if verdict_counts.get("BUY", 0) > verdict_counts.get("SELL", 0):
            sentiment = "bullish"
        elif verdict_counts.get("SELL", 0) > verdict_counts.get("BUY", 0):
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            "summary": (
                f"Dari {len(results)} saham yang dipindai ({mode}), "
                f"rata-rata skor {avg_score}. "
                f"BUY: {verdict_counts.get('BUY', 0)}, "
                f"HOLD: {verdict_counts.get('HOLD', 0)}, "
                f"SELL: {verdict_counts.get('SELL', 0)}, "
                f"AVOID: {verdict_counts.get('AVOID', 0)}."
            ),
            "sentiment": sentiment,
            "score_avg": avg_score,
            "total_stocks": len(results),
            "mode": mode,
            "generated_at": datetime.now().isoformat(),
        }

    top = sorted(results, key=lambda r: r.get("score", 0), reverse=True)[:5]
    top_text = "\n".join(
        f"- {r.get('ticker')}: {r.get('score')} ({r.get('verdict')})"
        for r in top
    )

    prompt = f"""Kamu adalah analis pasar saham Indonesia.

Data screening {len(results)} saham IDX (mode {mode}):
- Rata-rata skor: {avg_score}
- BUY: {verdict_counts.get('BUY', 0)}
- HOLD: {verdict_counts.get('HOLD', 0)}
- SELL: {verdict_counts.get('SELL', 0)}
- AVOID: {verdict_counts.get('AVOID', 0)}

Top 5 saham:
{top_text}

Beri ringkasan kondisi pasar (max 3 kalimat dalam Bahasa Indonesia):
1. Sentimen pasar secara umum (bullish/bearish/neutral)
2. Satu peluang menarik dari top 5

Jawab dengan format:
SENTIMEN: bullish/bearish/neutral
RINGKASAN: <ringkasan>"""

    def _call() -> str:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        return response.text.strip()

    try:
        raw = await asyncio.wait_for(asyncio.to_thread(_call), timeout=15)
        sentiment = "neutral"
        summary_parts = []
        in_summary = False
        for line in raw.split("\n"):
            if line.startswith("SENTIMEN:"):
                sentiment = line.replace("SENTIMEN:", "").strip().lower()
                in_summary = False
            elif line.startswith("RINGKASAN:"):
                summary_parts.append(line.replace("RINGKASAN:", "").strip())
                in_summary = True
            elif in_summary and line.strip():
                summary_parts.append(line.strip())
        summary = " ".join(summary_parts) if summary_parts else raw
    except Exception as e:
        logger.error("Market insight AI gagal: %s", e, exc_info=True)
        sentiment = "neutral"
        summary = "Ringkasan AI tidak tersedia saat ini."

    return {
        "summary": summary,
        "sentiment": sentiment,
        "score_avg": avg_score,
        "total_stocks": len(results),
        "mode": mode,
        "generated_at": datetime.now().isoformat(),
    }


@router.get("/market", response_model=MarketInsightResponse)
async def market_insight(mode: str = "BSJP"):
    global _insight_cache
    now = datetime.now().timestamp()
    if _insight_cache and now - _insight_cache.get("ts", 0) < _insight_ttl:
        return MarketInsightResponse(success=True, data=_insight_cache["data"])

    try:
        data = await _generate_market_insight(mode)
        _insight_cache = {"data": data, "ts": now}
        return MarketInsightResponse(success=True, data=data)
    except Exception as e:
        logger.error("Market insight error: %s", e, exc_info=True)
        return MarketInsightResponse(success=False, error=str(e))
