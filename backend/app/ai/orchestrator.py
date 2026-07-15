import asyncio
from google import genai
from app.config import settings
from app.schemas.stock import StockReport
from app.data.fetcher import fetch_company_info


def _format_news_context(news: list[dict] | None) -> str | None:
    if not news:
        return None
    lines = []
    for n in news:
        title = n.get("title", "")
        publisher = n.get("publisher", "")
        summary = n.get("summary", "")
        if not title:
            continue
        lines.append(f"- **{title}** ({publisher})")
        if summary:
            lines.append(f"  {summary[:200]}")
    if not lines:
        return None
    return "\n".join(lines)


def _format_fundamentals_context(fundamentals: dict | None) -> str | None:
    if not fundamentals or fundamentals.get("error"):
        return None
    parts = []
    mc = fundamentals.get("market_cap")
    if mc:
        parts.append(f"Market Cap: Rp {mc:,.0f}" if isinstance(mc, (int, float)) else f"Market Cap: {mc}")
    pe = fundamentals.get("pe")
    if pe:
        parts.append(f"P/E: {pe:.1f}" if isinstance(pe, (int, float)) else f"P/E: {pe}")
    fpe = fundamentals.get("forward_pe")
    if fpe:
        parts.append(f"Forward P/E: {fpe:.1f}" if isinstance(fpe, (int, float)) else f"Forward P/E: {fpe}")
    pb = fundamentals.get("pb")
    if pb:
        parts.append(f"P/B: {pb:.1f}" if isinstance(pb, (int, float)) else f"P/B: {pb}")
    dy = fundamentals.get("dividend_yield")
    if dy:
        parts.append(f"Dividend Yield: {dy*100:.2f}%" if isinstance(dy, (int, float)) else f"Dividend Yield: {dy}")
    beta = fundamentals.get("beta")
    if beta:
        parts.append(f"Beta: {beta:.2f}" if isinstance(beta, (int, float)) else f"Beta: {beta}")
    high = fundamentals.get("fifty_two_week_high")
    low = fundamentals.get("fifty_two_week_low")
    if high or low:
        high_str = f"Rp {high:,.0f}" if isinstance(high, (int, float)) else str(high)
        low_str = f"Rp {low:,.0f}" if isinstance(low, (int, float)) else str(low)
        parts.append(f"52w range: {low_str} – {high_str}")
    sector = fundamentals.get("sector")
    industry = fundamentals.get("industry")
    if sector or industry:
        parts.append(f"Sektor: {sector or '-'} | Industri: {industry or '-'}")
    if not parts:
        return None
    return "\n".join(parts)


async def enhance_with_ai(report: StockReport) -> StockReport:
    if not settings.gemini_api_key:
        report.summary += " | AI reasoning tidak tersedia (GEMINI_API_KEY tidak diisi)"
        return report

    info = await fetch_company_info(report.ticker)
    company = info.get("name", report.ticker)

    breakdown_text = "\n".join(
        f"- {b.funnel_layer}: {b.score}/100 → {b.note}"
        for b in report.score_breakdown
    )

    prompt = f"""Kamu adalah analis saham Indonesia. Berikut data teknikal saham {company} ({report.ticker}):

Skor: {report.score}/100
Verdict: {report.verdict.value}
Keyakinan: {report.confidence}%

Breakdown per layer:
{breakdown_text}

Indikator: {report.indicators.model_dump_json()}"""

    news_text = _format_news_context(report.news)
    if news_text:
        prompt += f"\n\nBerita terbaru:\n{news_text}"

    fund_text = _format_fundamentals_context(report.fundamentals)
    if fund_text:
        prompt += f"\n\nData fundamental:\n{fund_text}"

    prompt += """

Beri narasi (max 5-7 kalimat) dalam Bahasa Indonesia:
1. Jelaskan alasan utama di balik verdict berdasarkan data di atas.
2. Jika ada berita atau data fundamental, jelaskan dampaknya terhadap analisis teknikal ini.
3. Sebutkan kondisi atau skenario yang bisa membatalkan/mengubah analisis ini.

Jangan buat rekomendasi investasi. Akhiri dengan disclaimer bahwa ini alat riset, bukan rekomendasi."""

    def _call_gemini():
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
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
