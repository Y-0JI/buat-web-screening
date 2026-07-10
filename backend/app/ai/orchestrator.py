import asyncio
import google.generativeai as genai
from app.config import settings
from app.schemas.stock import StockReport, Verdict
from app.data.fetcher import fetch_company_info
import json


async def enhance_with_ai(report: StockReport) -> StockReport:
    if not settings.gemini_api_key:
        report.summary += " | AI reasoning tidak tersedia (GEMINI_API_KEY tidak diisi)"
        return report

    info = await fetch_company_info(report.ticker)
    company = info.get("name", report.ticker)

    prompt = f"""Kamu adalah analis saham Indonesia. Berikut data teknikal saham {company} ({report.ticker}):

Skor: {report.score}/100
Verdict: {report.verdict.value}
Keyakinan: {report.confidence}%
Indikator: {report.indicators.model_dump_json()}
Breakdown: {[b.model_dump() for b in report.score_breakdown]}

Beri narasi singkat (max 3 kalimat) dalam Bahasa Indonesia sebagai analisis riset.
Jangan buat rekomendasi investasi. Akhiri dengan disclaimer bahwa ini alat riset, bukan rekomendasi."""

    def _call_gemini():
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-3.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()

    try:
        ai_summary = await asyncio.wait_for(
            asyncio.to_thread(_call_gemini),
            timeout=30,
        )
        report.summary = ai_summary
    except asyncio.TimeoutError:
        report.summary += " | AI enhancement timeout"
    except Exception as e:
        report.summary += f" | Gagal memanggil AI: {str(e)}"

    return report
