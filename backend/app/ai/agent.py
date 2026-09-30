"""Agen chat streaming — loop tool-calling di atas data IDX Edge PRO.

Menyediakan:
- `TOOLS`: definisi tool gaya OpenAI (semua read, dari IDX Edge PRO).
- `run_tool(name, args)`: eksekusi tool (aman, tidak pernah raise).
- `stream_agent(...)`: async generator event SSE (reasoning/token/tool/done/error).

Tidak ada action tool: UI chat-only, jadi agen hanya membaca & menganalisa.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Optional

from app.ai.client import get_async_client
from app.config import settings
from app.providers.idx_edge_provider import (
    IdxEdgeProvider,
    broker_summary_payload,
    history_series,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6
TOOL_TIMEOUT = 60

_PERIOD_LIMITS = {"1mo": 22, "3mo": 66, "6mo": 126, "1y": 252}


def _edge_provider() -> IdxEdgeProvider:
    return IdxEdgeProvider()


# --------------------------------------------------------------- tool functions

async def _get_analysis(ticker: str) -> dict:
    data = await _edge_provider().fetch_analysis(ticker.upper())
    if not data:
        return {"error": f"Analisa {ticker} tidak tersedia."}
    return data


async def _get_price_history(ticker: str, period: str = "3mo") -> dict:
    limit = _PERIOD_LIMITS.get(period, 66)
    rows = await _edge_provider().fetch_history(ticker.upper(), limit=limit)
    series = history_series(rows)
    if not series:
        return {"error": f"Riwayat harga {ticker} tidak tersedia."}
    return {"ticker": ticker.upper(), "period": period, "series": series}


async def _get_screener() -> dict:
    data = await _edge_provider().fetch_screener()
    if not data:
        return {"error": "Screener tidak tersedia."}
    return {
        "date": data.get("date"),
        "rows": data.get("rows") or [],
    }


async def _get_broker_summary(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    flow: str = "all",
    net: bool = False,
) -> dict:
    data = await _edge_provider().fetch_broker_summary(
        ticker.upper(),
        start_date=start_date,
        end_date=end_date,
        flow=flow,
        net=net,
        broker_limit=20,
        level_limit=5,
    )
    payload = broker_summary_payload(data)
    if not payload:
        return {"error": f"Broker summary {ticker} tidak tersedia."}
    return payload


async def _get_seasonality(ticker: str) -> dict:
    data = await _edge_provider().fetch_seasonal(ticker.upper())
    if not data:
        return {"error": f"Seasonality {ticker} tidak tersedia."}
    return data


async def _get_market_cap(codes: Optional[str] = None) -> dict:
    code_list = [c.strip().upper() for c in codes.split(",")] if codes else None
    data = await _edge_provider().fetch_market_cap(codes=code_list)
    if not data:
        return {"error": "Market cap tidak tersedia."}
    return {"date": data.get("date"), "data": data.get("data") or []}


async def _get_insiders(ticker: str, limit: int = 20) -> dict:
    data = await _edge_provider().fetch_insiders(ticker.upper(), limit=limit)
    if not data:
        return {"error": f"Data insider {ticker} tidak tersedia."}
    return {"stock_code": data.get("stock_code"), "items": data.get("items") or []}


async def _get_order_flow(ticker: str, date: Optional[str] = None) -> dict:
    data = await _edge_provider().fetch_done_details(ticker.upper(), date=date, per_page=100)
    if not data:
        return {"error": f"Order flow {ticker} tidak tersedia."}
    return {
        "code": data.get("code"),
        "date": data.get("date"),
        "total": data.get("total"),
        "data": (data.get("data") or [])[:100],
    }


async def _get_financial_statements(ticker: str, report_type: str = "INCOME_STATEMENT") -> dict:
    data = await _edge_provider().fetch_financial_statements(
        ticker.upper(), report_type=report_type, period="quarterly", limit=8
    )
    if not data:
        return {"error": f"Laporan keuangan {ticker} tidak tersedia."}
    return data


async def _search_stocks(q: str) -> dict:
    results = await _edge_provider().search(q)
    return {"query": q, "results": results[:10]}


# --------------------------------------------------------------- tool registry

TOOL_SPECS: list[dict] = [
    {
        "name": "get_analysis",
        "description": "Analisa teknikal & sinyal siap-pakai untuk satu saham (teks dari IDX Edge PRO).",
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
        "fn": _get_analysis,
    },
    {
        "name": "get_price_history",
        "description": "Riwayat harga OHLCV harian satu saham untuk menampilkan chart candlestick.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Kode saham IDX, mis. BBCA."},
                "period": {"type": "string", "enum": ["1mo", "3mo", "6mo", "1y"], "description": "Rentang waktu. Default 3mo."},
            },
            "required": ["ticker"],
        },
        "fn": _get_price_history,
    },
    {
        "name": "get_screener",
        "description": "Daftar kandidat screener saham terkini (teknikal + akumulasi broker).",
        "parameters": {"type": "object", "properties": {}},
        "fn": _get_screener,
    },
    {
        "name": "get_broker_summary",
        "description": "Broker summary & netflow (bandarmologi) satu saham. Bisa difilter rentang tanggal, investor (asing/domestik), dan net/gross.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD (opsional)."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD (opsional)."},
                "flow": {"type": "string", "enum": ["all", "F", "D"], "description": "all=semua, F=asing, D=domestik. Default all."},
                "net": {"type": "boolean", "description": "true=net, false=gross. Default false."},
            },
            "required": ["ticker"],
        },
        "fn": _get_broker_summary,
    },
    {
        "name": "get_seasonality",
        "description": "Seasonality win-rate bulanan satu saham.",
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
        "fn": _get_seasonality,
    },
    {
        "name": "get_market_cap",
        "description": "Market cap & saham beredar. Bisa untuk daftar kode tertentu.",
        "parameters": {
            "type": "object",
            "properties": {"codes": {"type": "string", "description": "Kode dipisah koma, mis. BBCA,BBRI. Kosong = halaman pertama."}},
        },
        "fn": _get_market_cap,
    },
    {
        "name": "get_insiders",
        "description": "Riwayat transaksi insider (direksi/komisaris) satu saham.",
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["ticker"],
        },
        "fn": _get_insiders,
    },
    {
        "name": "get_order_flow",
        "description": "Done details / order flow harian satu saham.",
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}, "date": {"type": "string", "description": "YYYY-MM-DD, opsional."}},
            "required": ["ticker"],
        },
        "fn": _get_order_flow,
    },
    {
        "name": "get_financial_statements",
        "description": "Laporan keuangan (laba rugi/neraca/arus kas) satu saham.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "report_type": {"type": "string", "enum": ["INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]},
            },
            "required": ["ticker"],
        },
        "fn": _get_financial_statements,
    },
    {
        "name": "search_stocks",
        "description": "Cari kode saham IDX berdasarkan kata kunci.",
        "parameters": {
            "type": "object",
            "properties": {"q": {"type": "string"}},
            "required": ["q"],
        },
        "fn": _search_stocks,
    },
]

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": spec["name"],
            "description": spec["description"],
            "parameters": spec["parameters"],
        },
    }
    for spec in TOOL_SPECS
]

_TOOL_MAP = {spec["name"]: spec["fn"] for spec in TOOL_SPECS}


async def run_tool(name: str, args: dict) -> dict:
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return {"error": f"Tool tidak dikenal: {name}"}
    try:
        return await asyncio.wait_for(fn(**(args or {})), timeout=TOOL_TIMEOUT)
    except asyncio.TimeoutError:
        return {"error": f"Tool {name} timeout."}
    except Exception as e:  # noqa: BLE001
        logger.warning("Tool %s gagal: %s", name, e)
        return {"error": f"Tool {name} gagal: {e}"}


# --------------------------------------------------------------- agent runtime

SYSTEM_PROMPT = (
    "Kamu adalah asisten riset saham IDX (Bursa Efek Indonesia). Jawab dalam "
    "Bahasa Indonesia yang santai tapi informatif. Gunakan tool yang tersedia "
    "untuk mengambil data NYATA sebelum menjawab pertanyaan tentang saham; jangan "
    "mengarang angka. Pilih tool sesuai kebutuhan (analisa, screener, broker, "
    "seasonality, market cap, insider, order flow, laporan keuangan, pencarian). "
    "Jika tool mengembalikan error, sampaikan apa adanya. Jangan memberi "
    "rekomendasi beli/jual; akhiri analisis dengan catatan singkat bahwa ini alat "
    "riset, bukan saran keuangan."
)


def _summarize(result: Any) -> str:
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])[:200]
    if isinstance(result, dict):
        return "ok: " + ", ".join(list(result.keys())[:6])
    return "ok"


def _build_messages(history: list[dict], context: Optional[dict]) -> list[dict]:
    system = SYSTEM_PROMPT
    if context and context.get("view"):
        system += f"\nKonteks: user sedang di halaman {context['view']}."
    msgs = [{"role": "system", "content": system}]
    for m in history:
        role = "user" if m.get("role") == "user" else "assistant"
        content = m.get("content") or ""
        if content:
            msgs.append({"role": role, "content": content})
    return msgs


async def stream_agent(
    history: list[dict],
    model: str,
    context: Optional[dict] = None,
) -> AsyncGenerator[dict, None]:
    if not settings.ai_api_key:
        yield {"type": "error", "message": "AI_API_KEY belum diisi."}
        return

    client = get_async_client()
    msgs = _build_messages(history, context)
    all_reasoning: list[str] = []
    all_tools: list[dict] = []
    final_content = ""

    try:
        for _round in range(MAX_TOOL_ROUNDS):
            content_parts: list[str] = []
            tool_slots: dict[int, dict] = {}
            stream = await client.chat.completions.create(
                model=model, messages=msgs, tools=TOOLS,
                tool_choice="auto", stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    all_reasoning.append(reasoning)
                    yield {"type": "reasoning", "delta": reasoning}
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "token", "delta": delta.content}
                for tc in (delta.tool_calls or []):
                    slot = tool_slots.setdefault(
                        tc.index, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["arguments"] += tc.function.arguments

            if not tool_slots:
                final_content = "".join(content_parts)
                break

            resolved = []
            for i in sorted(tool_slots):
                slot = tool_slots[i]
                resolved.append({
                    "id": slot["id"] or f"call_{i}",
                    "name": slot["name"],
                    "arguments": slot["arguments"] or "{}",
                })
            msgs.append({
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": [
                    {
                        "id": r["id"],
                        "type": "function",
                        "function": {"name": r["name"], "arguments": r["arguments"]},
                    }
                    for r in resolved
                ],
            })

            parsed: list[tuple[dict, dict]] = []
            for r in resolved:
                try:
                    args = json.loads(r["arguments"])
                except (json.JSONDecodeError, TypeError):
                    args = {}
                parsed.append((r, args))
                yield {"type": "tool_start", "name": r["name"], "args": args}

            outcomes = await asyncio.gather(
                *(run_tool(r["name"], args) for r, args in parsed)
            )

            for (r, args), result in zip(parsed, outcomes):
                ok = not (isinstance(result, dict) and result.get("error"))
                all_tools.append({"name": r["name"], "args": args, "ok": ok})
                yield {"type": "tool_result", "name": r["name"], "ok": ok, "summary": _summarize(result)}
                if r["name"] == "get_price_history" and ok and isinstance(result, dict):
                    yield {
                        "type": "chart",
                        "ticker": result.get("ticker"),
                        "period": result.get("period"),
                        "series": result.get("series") or [],
                    }
                if r["name"] == "get_broker_summary" and ok and isinstance(result, dict):
                    yield {"type": "broker", "data": result}
                msgs.append({
                    "role": "tool",
                    "tool_call_id": r["id"],
                    "content": json.dumps(result, default=str)[:8000],
                })
        else:
            final_content = "Maaf, analisis terlalu panjang. Coba pertanyaan yang lebih spesifik."

        yield {
            "type": "done",
            "content": final_content,
            "reasoning": "".join(all_reasoning),
            "tool_calls": all_tools,
        }
    except Exception as e:  # noqa: BLE001
        logger.error("stream_agent error: %s", e, exc_info=True)
        yield {"type": "error", "message": "Layanan AI sedang tidak tersedia. Coba lagi."}
