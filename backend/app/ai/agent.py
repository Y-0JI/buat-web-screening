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
from datetime import date, timedelta
from typing import Any, AsyncGenerator, Optional

from app.ai.client import get_async_client
from app.config import settings
from app.fundamentals import build_fundamentals
from app.providers.idx_edge_provider import (
    IdxEdgeProvider,
    broker_summary_payload,
    history_series,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6
TOOL_TIMEOUT = 60

_PERIOD_LIMITS = {"1mo": 22, "3mo": 66, "6mo": 126, "1y": 252}

# Tunggu satu tick running-trade sebalik sebelum fallback ke snapshot REST.
_LIVE_WAIT = 2.0


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


def _extract_live_quote(message: Any) -> Optional[dict]:
    """Ambil {price, change_pct, time} dari satu pesan LiveFeed.

    Bentuk yang datang: `{"type":"quote", price, change_pct, time}` atau
    `{"type":"trade", data:{price, change_pct, time}}` (dan snapshot).
    """
    if not isinstance(message, dict):
        return None
    raw_data = message.get("data")
    data: dict = raw_data if isinstance(raw_data, dict) else message
    price = data.get("price")
    if not isinstance(price, (int, float)):
        return None
    change_pct = data.get("change_pct")
    return {
        "price": float(price),
        "change_pct": float(change_pct) if isinstance(change_pct, (int, float)) else None,
        "time": data.get("time"),
    }


async def _live_tick(code: str, timeout: float = _LIVE_WAIT) -> Optional[dict]:
    """Tunggu satu tick running-trade untuk `code`; None bila tak ada/timeout."""
    from app.services.live_feed import get_feed

    try:
        feed = get_feed()
        queue = await feed.subscribe({code})
    except Exception as e:  # noqa: BLE001 — WS belum siap, biarkan fallback
        logger.info("Live feed tidak tersedia untuk %s: %s", code, e)
        return None
    try:
        raw = await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    except Exception as e:  # noqa: BLE001
        logger.info("Gagal baca tick live %s: %s", code, e)
        return None
    finally:
        try:
            await feed.unsubscribe({code}, queue)
        except Exception:  # noqa: BLE001 — unsubscribe gagal tidak berpengaruh ke AI
            pass
    try:
        message = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    return _extract_live_quote(message)


async def _get_live_price(ticker: str) -> dict:
    """Harga terakhir satu saham: stream running-trade, fallback snapshot REST."""
    code = (ticker or "").strip().upper()
    if not code:
        return {"error": "Kode saham wajib diisi."}

    live = await _live_tick(code)
    if live:
        return {
            "ticker": code,
            "price": live["price"],
            "change_pct": live["change_pct"],
            "as_of": live["time"],
            "source": "running-trade",
        }

    price = await _edge_provider().fetch_price(code)
    if not price:
        return {"error": f"Harga {code} tidak tersedia."}
    # Snapshot REST tidak punya change_pct; as_of = jam trade terakhir hari ini
    # (null saat tidak ada transaksi -> harga dari penutupan sebelumnya).
    out = {
        "ticker": code,
        "price": price.get("last_price"),
        "change_pct": None,
        "as_of": price.get("data_ts") or price.get("source_date"),
        "source": "rest-snapshot",
        "market_state": price.get("market_state"),
        "market_label": price.get("market_label"),
        "lot": price.get("lot"),
        "value": price.get("value"),
    }
    if price.get("no_trade_today"):
        out["no_trade_today"] = True
    return out


_TOP_WAIT = 3.0


def _norm_top_item(item: Any) -> Any:
    """Normalisasi item top-aktif dari pesan snapshot|top5 WS.

    Bentuk terverifikasi (market buka):
    {"ticker","metric","count","last_price","last_change_pct"}.
    Field mentah dipertahankan agar tidak ada info yang hilang.
    """
    if not isinstance(item, dict):
        return item
    out = dict(item)
    if "ticker" not in out and "t" in out:
        out["ticker"] = out["t"]
    if "price" not in out:
        for k in ("last_price", "p"):
            if k in out:
                out["price"] = out[k]
                break
    if "change_pct" not in out:
        for k in ("last_change_pct", "pc"):
            if k in out:
                out["change_pct"] = out[k]
                break
    return out


async def _get_top_active() -> dict:
    """5 saham teraktif (stream running-trade) + status pasar.

    Ini top-AKTIF (volume/nilai/frekuensi), BUKAN top gainer/loser. Vendor
    tidak membuka data top gainer/loser untuk API key.
    """
    from app.services.live_feed import get_feed

    feed = get_feed()
    try:
        await feed.ensure_running()
    except Exception as e:  # noqa: BLE001 — biarkan; mungkin tetap ada cache
        logger.info("Live feed tidak tersedia: %s", e)

    loop = asyncio.get_running_loop()
    deadline = loop.time() + _TOP_WAIT
    market = feed.latest_market()
    top = feed.latest_top()
    while not market and not top.get("top") and loop.time() < deadline:
        await asyncio.sleep(0.25)
        market = feed.latest_market()
        top = feed.latest_top()

    if not market and not top.get("top"):
        return {"error": "Data top-aktif belum tersedia (feed belum menerima snapshot)."}

    return {
        "as_of": market.get("label") or market.get("status"),
        "market": market,
        "window_seconds": top.get("window_seconds"),
        "top": [_norm_top_item(x) for x in top.get("top", [])],
        "note": (
            "Top 5 saham TERAKTIF dari stream running-trade (volume/nilai). Ini "
            "BUKAN top gainer/loser; data top gainer/loser tidak tersedia lewat "
            "API key vendor. Saat pasar tutup, daftar bisa kosong."
        ),
    }


async def _get_fundamentals(ticker: str) -> dict:
    data = await build_fundamentals(ticker.upper())
    if not data:
        return {"error": f"Data fundamental {ticker} tidak tersedia."}
    return data


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


_STALE_TRADING_DAYS = 3


def _trading_days_since(date_str: Optional[str]) -> Optional[int]:
    try:
        d = date.fromisoformat(str(date_str))
    except (TypeError, ValueError):
        return None
    today = date.today()
    if d >= today:
        return 0
    days = 0
    cur = d
    while cur < today:
        cur += timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


async def _get_accumulation_candidates(limit: int = 10) -> dict:
    """Baca hasil scan tersimpan (tanpa request jaringan)."""
    from app.repositories import accumulation_repository as acc_repo

    limit = max(1, min(int(limit or 10), 25))
    scan = await acc_repo.get_latest_scan(limit=limit)
    if not scan:
        return {"error": "Belum ada hasil scan akumulasi."}
    age = _trading_days_since(scan.get("scan_date"))
    stale = age is not None and age > _STALE_TRADING_DAYS
    candidates = []
    for s in (scan.get("signals") or [])[:limit]:
        raw = (s.get("components") or {}).get("raw") or {}
        foreign = raw.get("foreign") or {}
        candidates.append({
            "ticker": s.get("ticker"),
            "score": s.get("score"),
            "depth": s.get("depth"),
            "reasons": s.get("reasons"),
            "cmf": raw.get("cmf"),
            "obv_slope": raw.get("obv_slope"),
            "ad_slope": raw.get("ad_slope"),
            "foreign_net": s.get("foreign_net"),
            "foreign_ratio": foreign.get("ratio"),
            "runup": raw.get("runup"),
            "broker_checked": raw.get("broker_checked"),
            "broker_confirmed": raw.get("broker_confirmed"),
        })
    return {
        "scan_date": scan.get("scan_date"),
        "status": scan.get("status"),
        "stale": stale,
        "stale_trading_days": age,
        "candidates": candidates,
        "note": (
            "Hasil screening deskriptif dari aliran harga/arus asing/broker besar; "
            "belum terbukti prediktif (hasil backtest tidak menunjukkan edge). BUKAN "
            "label institusi, bukan saran investasi, bukan rekomendasi. "
            "depth=broker = dihitung dengan data broker, depth=foreign = hanya "
            "arus asing, depth=hv = hanya harga-volume."
        ),
    }


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
        "name": "get_live_price",
        "description": (
            "Harga terakhir satu saham beserta perubahan intraday (change_pct). Sumber "
            "utama: stream running-trade real-time (source=running-trade); bila tidak "
            "tersedia, fallback ke snapshot REST (source=rest-snapshot, change_pct "
            "mungkin null). Untuk pertanyaan harga SEKARANG/TERKINI gunakan tool ini, "
            "bukan get_price_history (yang OHLCV harian). Sebutkan waktu datanya (as_of)."
        ),
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Kode saham IDX, mis. BBCA."}},
            "required": ["ticker"],
        },
        "fn": _get_live_price,
    },
    {
        "name": "get_top_active",
        "description": (
            "5 saham paling AKTIF (teraktif) di pasar saat ini dari stream "
            "running-trade, plus status pasar (open/break/closed, label, next_open). "
            "Gunakan untuk pertanyaan 'saham teraktif/ramai hari ini'. Ini BUKAN "
            "top gainer/loser — data top gainer/loser tidak tersedia lewat API key "
            "vendor; sampaikan itu bila ditanya."
        ),
        "parameters": {"type": "object", "properties": {}},
        "fn": _get_top_active,
    },
    {
        "name": "get_fundamentals",
        "description": "Ringkasan fundamental satu saham: valuasi (PE/PBV/PSR/Earnings Yield), laba-rugi, neraca, arus kas, per-share, profitabilitas, solvabilitas, pertumbuhan, dan price performance.",
        "parameters": {
            "type": "object",
            "properties": {"ticker": {"type": "string"}},
            "required": ["ticker"],
        },
        "fn": _get_fundamentals,
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
        "name": "get_accumulation_candidates",
        "description": (
            "Daftar saham HASIL SCREENING DESKRIPTIF aliran harga/arus asing/broker "
            "besar (dari scan harian; hasil tersimpan, bukan hitung ulang). Hasil ini "
            "BELUM TERBUKTI PREDIKTIF (hasil backtest tidak menunjukkan edge); BUKAN "
            "label institusi, BUKAN saran investasi, BUKAN rekomendasi. Jangan "
            "menyatakan/menyiratkan prediksi, prospek, peluang kenaikan, atau "
            "'whale terkonfirmasi'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "1-25, default 10."}
            },
        },
        "fn": _get_accumulation_candidates,
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
    "riset, bukan saran keuangan. Untuk pertanyaan harga SEKARANG/TERKINI, "
    "WAJIB panggil tool get_live_price (bukan get_price_history yang OHLCV "
    "harian), dan sebutkan kapan datanya (as_of) serta sumbernya "
    "(running-trade = real-time, rest-snapshot = snapshot yang bisa tertinggal). "
    "Bila change_pct null dan sumber rest-snapshot, sampaikan harga itu "
    "snapshot/tertinggal. Untuk pertanyaan 'saham teraktif'/'ramai', panggil tool "
    "get_top_active (top-aktif, BUKAN top gainer). Top gainer/loser SELURUH PASAR "
    "TIDAK tersedia lewat API key vendor — katakan itu apa adanya lalu tawarkan "
    "alternatif (get_top_active, get_live_price per saham). Untuk data akumulasi "
    "(get_accumulation_candidates), WAJIB sebutkan tanggal datanya (scan_date) dan "
    "bila field stale=true katakan bahwa itu data lama, bukan data hari ini. "
    "Untuk broker summary, panggil get_broker_summary "
    "cukup SEKALI per saham (default semua investor) — jangan panggil berulang "
    "untuk asing/domestik, karena filter bisa diubah user di kartu. Untuk pertanyaan "
    "daftar saham dari tool get_accumulation_candidates, panggil tool itu dan jelaskan "
    "bahwa itu HASIL SCREENING DESKRIPTIF dari aliran harga/arus asing/broker besar "
    "yang BELUM TERBUKTI PREDIKTIF — BUKAN prediksi, BUKAN bukti institusi, BUKAN "
    "saran investasi, BUKAN rekomendasi; jangan menyatakan/menyiratkan prospek, "
    "peluang kenaikan, atau 'whale terkonfirmasi'; sebutkan bila scan partial "
    "atau data basi, dan tunjukkan sinyal yang bertentangan."
)


def _summarize(result: Any) -> str:
    if isinstance(result, dict) and result.get("error"):
        return str(result["error"])[:200]
    if isinstance(result, dict):
        return "ok: " + ", ".join(list(result.keys())[:6])
    return "ok"


def _build_messages(history: list[dict], context: Optional[dict]) -> list[dict]:
    system = SYSTEM_PROMPT
    if context:
        ticker = context.get("ticker")
        view = context.get("view")
        if ticker and view:
            system += f"\nKonteks: user sedang melihat saham {ticker} di halaman {view}."
        elif ticker:
            system += f"\nKonteks: user sedang melihat saham {ticker}."
        elif view:
            system += f"\nKonteks: user sedang di halaman {view}."
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
    broker_tickers: set[str] = set()
    fundamental_tickers: set[str] = set()
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
                    code = str(result.get("stock_code") or "").upper()
                    if code and code not in broker_tickers:
                        broker_tickers.add(code)
                        yield {"type": "broker", "ticker": code}
                if r["name"] == "get_fundamentals" and ok and isinstance(result, dict):
                    code = str(result.get("ticker") or "").upper()
                    if code and code not in fundamental_tickers:
                        fundamental_tickers.add(code)
                        yield {"type": "fundamental", "ticker": code, "data": result}
                if r["name"] == "get_accumulation_candidates" and ok and isinstance(result, dict):
                    yield {"type": "accumulation", "data": result}
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
