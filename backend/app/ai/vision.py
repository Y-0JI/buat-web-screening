import asyncio
from google import genai
from google.genai import types
from app.config import settings
import re


VISION_PROMPT = """Kamu adalah analis teknikal saham Indonesia.
Analisis chart/order book pada gambar ini. Jawab dalam Bahasa Indonesia.

Berikan analisis singkat (max 5 kalimat) yang mencakup:
1. Trend terlihat (uptrend/downtrend/sideways)
2. Level support & resistance kunci (sebutkan angka jika terlihat)
3. Volume: apakah ada lonjakan atau tidak
4. Pattern candle/chart yang terdeteksi (mis. doji, engulfing, breakout, dll)
5. Rekomendasi risiko singkat

Format jawaban:
TREND: <uptrend/downtrend/sideways>
SUPPORT: <angka atau tidak terlihat>
RESISTANCE: <angka atau tidak terlihat>
VOLUME: <normal/lonjakan/redop>
PATTERN: <daftar pattern atau tidak terdeteksi>
ANALISIS: <narasi singkat 3-5 kalimat>"""


def parse_vision_response(text: str) -> dict:
    result = {
        "trend": None,
        "support_level": None,
        "resistance_level": None,
        "patterns_detected": [],
    }

    _KNOWN_LABELS = ("TREND:", "SUPPORT:", "RESISTANCE:", "VOLUME:", "PATTERN:", "ANALISIS:")

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("TREND:"):
            result["trend"] = line.replace("TREND:", "").strip().lower()
        elif line.startswith("SUPPORT:"):
            val = line.replace("SUPPORT:", "").strip()
            try:
                result["support_level"] = float(re.search(r"[\d,]+\.?\d*", val.replace(",", "")).group())
            except (AttributeError, ValueError):
                pass
        elif line.startswith("RESISTANCE:"):
            val = line.replace("RESISTANCE:", "").strip()
            try:
                result["resistance_level"] = float(re.search(r"[\d,]+\.?\d*", val.replace(",", "")).group())
            except (AttributeError, ValueError):
                pass
        elif line.startswith("PATTERN:"):
            val = line.replace("PATTERN:", "").strip()
            if val.lower() not in ("tidak terdeteksi", "tidak ada", "none", "-"):
                result["patterns_detected"] = [p.strip() for p in val.split(",")]
        elif line.startswith("ANALISIS:"):
            first_line = line.replace("ANALISIS:", "").strip()
            analysis_parts = [first_line] if first_line else []
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if any(next_line.startswith(lbl) for lbl in _KNOWN_LABELS):
                    break
                if next_line:
                    analysis_parts.append(next_line)
                i += 1
            result["analysis_text"] = "\n".join(analysis_parts).strip()
            continue
        i += 1

    if "analysis_text" not in result:
        result["analysis_text"] = text

    return result


async def analyze_chart_image(image_bytes: bytes, filename: str) -> dict:
    if not settings.gemini_api_key:
        return {
            "file_name": filename,
            "analysis_text": "AI vision tidak tersedia (GEMINI_API_KEY tidak diisi)",
            "patterns_detected": [],
            "trend": None,
            "support_level": None,
            "resistance_level": None,
        }

    client = genai.Client(api_key=settings.gemini_api_key)

    mime_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"
    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

    def _call_gemini():
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[VISION_PROMPT, image_part],
        )
        return response.text.strip()

    try:
        raw_text = await asyncio.to_thread(_call_gemini)
        parsed = parse_vision_response(raw_text)
        parsed["file_name"] = filename
        return parsed
    except Exception as e:
        return {
            "file_name": filename,
            "analysis_text": f"Gagal menganalisis gambar: {str(e)}",
            "patterns_detected": [],
            "trend": None,
            "support_level": None,
            "resistance_level": None,
        }
