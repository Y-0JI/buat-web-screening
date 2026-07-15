import asyncio
import logging
import google.generativeai as genai
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


SYSTEM_INSTRUCTION = (
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
    "error (ticker tidak ditemukan), sampaikan apa adanya ke user, jangan mengarang data."
)


def _run_chat(messages: list[ChatMessage]) -> str:
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        "gemini-3.5-flash",
        tools=[get_stock_data, get_company_news, get_fundamentals],
        system_instruction=SYSTEM_INSTRUCTION,
    )
    history = [{"role": m.role, "parts": [m.content]} for m in messages[:-1]]
    chat_session = model.start_chat(
        history=history,
        enable_automatic_function_calling=True,
    )
    response = chat_session.send_message(messages[-1].content)
    return response.text


@router.post("/chat")
async def chat(req: ChatRequest):
    if not settings.gemini_api_key:
        return {"success": False, "error": "GEMINI_API_KEY belum diisi"}
    if not req.messages:
        return {"success": False, "error": "Messages kosong"}
    try:
        reply = await asyncio.to_thread(_run_chat, req.messages)
        return {"success": True, "reply": reply}
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}
