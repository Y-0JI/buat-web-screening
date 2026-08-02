import asyncio
import json
import logging
from fastapi import APIRouter
from pydantic import BaseModel
from app.ai.client import get_client
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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_data",
            "description": get_stock_data.__doc__.split("\n\n")[0],
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Kode saham IDX, 2-5 huruf, contoh BBCA.",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["BSJP", "BPJS"],
                        "description": "Profil trading, BSJP atau BPJS. Default BSJP.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_news",
            "description": get_company_news.__doc__.split("\n\n")[0],
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Kode saham IDX, contoh BBCA.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Jumlah berita yang diambil (default 5).",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fundamentals",
            "description": get_fundamentals.__doc__.split("\n\n")[0],
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Kode saham IDX, contoh BBCA.",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
]


def _run_chat(messages: list[ChatMessage], mode: str, context: dict | None = None) -> str:
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

    msgs: list[dict] = [{"role": "system", "content": system_instruction}]
    for m in messages:
        role = "user" if m.role == "user" else "assistant"
        msgs.append({"role": role, "content": m.content})

    def _call() -> object:
        return get_client().chat.completions.create(
            model=settings.ai_model,
            messages=msgs,
            tools=TOOLS,
            tool_choice="auto",
        )

    response = _call()
    turn = 0
    while turn < 5:
        msg = response.choices[0].message
        tool_calls = msg.tool_calls
        if not tool_calls:
            return msg.content

        msgs.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            func = TOOL_MAP.get(tc.function.name)
            if func is None:
                result = {"error": f"Unknown function: {tc.function.name}"}
            else:
                try:
                    result = func(**json.loads(tc.function.arguments or "{}"))
                except Exception as e:
                    result = {"error": str(e)}
            msgs.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, default=str),
            })

        response = _call()
        turn += 1

    return response.choices[0].message.content


@router.post("/chat")
async def chat(req: ChatRequest):
    if not settings.ai_api_key:
        return {"success": False, "error": "AI_API_KEY belum diisi"}
    if not req.messages:
        return {"success": False, "error": "Messages kosong"}
    try:
        reply = await asyncio.to_thread(_run_chat, req.messages, req.mode, req.context)
        return {"success": True, "reply": reply}
    except Exception as e:
        logger.error("Chat error: %s", e, exc_info=True)
        return {"success": False, "error": "Layanan AI sedang tidak tersedia. Coba kirim pesan lagi nanti."}