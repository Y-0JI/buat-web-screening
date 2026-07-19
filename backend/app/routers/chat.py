import asyncio
import logging
from google import genai
from google.genai import types
from fastapi import APIRouter
from pydantic import BaseModel
from app.config import settings
from app.ai.tools import get_stock_data, get_company_news, get_fundamentals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: str = "BSJP"
    context: dict | None = None


TOOL_MAP = {
    "get_stock_data": get_stock_data,
    "get_company_news": get_company_news,
    "get_fundamentals": get_fundamentals,
}


def _run_chat(messages: list[ChatMessage], mode: str, context: dict | None = None) -> str:
    client = genai.Client(api_key=settings.gemini_api_key)

    context_str = ""
    if context:
        view = context.get("view")
        ticker = context.get("ticker")
        tickers = context.get("tickers", [])
        if view:
            context_str += f"\n- View aktif user saat ini: {view.upper()}"
        if ticker:
            context_str += f"\n- Ticker yang sedang dilihat user: {ticker}"
        if tickers:
            context_str += f"\n- Ticker yang sedang dibandingkan: {', '.join(tickers)}"

    system_instruction = (
        "Kamu asisten riset saham IDX (Bursa Efek Indonesia). Jawab dalam Bahasa "
        "Indonesia santai tapi informatif. Kalau user tanya soal saham tertentu, "
        "panggil tool get_stock_data untuk data teknikal, lalu get_fundamentals "
        "untuk data fundamental, dan get_company_news untuk berita terkini. "
        "Kalau user tanya soal berita saham tertentu, panggil get_company_news. "
        "Kalau user tanya soal fundamental, PE, dividen, atau profil perusahaan, "
        "panggil get_fundamentals. "
        "Kalau user minta bandingkan beberapa saham, panggil tool untuk masing-masing "
        "lalu simpulkan. Jangan buat rekomendasi investasi langsung, selalu akhiri "
        "analisis dengan disclaimer bahwa ini alat bantu riset. Kalau tool balikin "
        "error (ticker tidak ditemukan), sampaikan apa adanya ke user, jangan mengarang data. "
        f"Mode analisis yang aktif: {mode}. "
        "Selalu sertakan parameter mode ini saat memanggil get_stock_data."
        f"{context_str}"
        "\n\nBerikan rekomendasi dalam bentuk yang bisa ditindaklanjuti. Kalau relevan, "
        "sebutkan ticker spesifik (format: singkatan huruf kapital 1-5 karakter, misal BBCA) "
        "supaya user bisa langsung membukanya. Jangan gunakan markdown link, cukup sebut ticker."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[get_stock_data, get_company_news, get_fundamentals],
    )

    # Build full conversation as contents list — single API call
    contents = []
    for m in messages:
        role = "user" if m.role == "user" else "model"
        contents.append(types.Content(
            role=role,
            parts=[types.Part.from_text(text=m.content)]
        ))

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=contents,
        config=config,
    )

    turn = 0
    while turn < 5:
        function_calls = [
            part.function_call
            for part in (response.candidates[0].content.parts or [])
            if part.function_call
        ]
        if not function_calls:
            break

        # Append model's function call parts to conversation history
        contents.append(response.candidates[0].content)

        # Process each function call and build response parts
        function_response_parts = []
        for fc in function_calls:
            func = TOOL_MAP.get(fc.name)
            if func is None:
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"error": f"Unknown function: {fc.name}"},
                    )
                )
                continue
            try:
                result = func(**dict(fc.args))
            except Exception as e:
                result = {"error": str(e)}
            function_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response=result,
                )
            )

        # Append function responses as user role (standard for Gemini function calling)
        contents.append(types.Content(
            role="user",
            parts=function_response_parts,
        ))

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config=config,
        )
        turn += 1

    return response.text


@router.post("/chat")
async def chat(req: ChatRequest):
    if not settings.gemini_api_key:
        return {"success": False, "error": "GEMINI_API_KEY belum diisi"}
    if not req.messages:
        return {"success": False, "error": "Messages kosong"}
    try:
        reply = await asyncio.to_thread(_run_chat, req.messages, req.mode, req.context)
        return {"success": True, "reply": reply}
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return {"success": False, "error": "Layanan AI sedang tidak tersedia. Coba kirim pesan lagi nanti."}
