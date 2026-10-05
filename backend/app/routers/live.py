"""Router WebSocket harga/running trade realtime untuk frontend.

Klien membuka `GET /ws/live?ticker=BBCA` lalu menerima JSON:
- `{"type":"quote","ticker","price","change_pct","time"}` per transaksi
- `{"type":"trade","ticker","data":{time,action,price,lot,value,...}}` per transaksi
- `{"type":"snapshot", ...}` saat awal sambung (recent ticker tsb)

Kunci API tetap di server (proxy ke WS provider lewat `live_feed`).
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.live_feed import get_feed

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live"])


def _code_of(q: Optional[str]) -> Optional[str]:
    if not q:
        return None
    code = q.strip().upper()
    return code or None


@router.websocket("/ws/live")
async def live_ticker(websocket: WebSocket) -> None:
    ticker = _code_of(websocket.query_params.get("ticker"))
    if not ticker:
        await websocket.close(code=4400)
        return
    await websocket.accept()
    await websocket.send_text(json.dumps({"type": "hello", "ticker": ticker}))
    feed = get_feed()
    queue = await feed.subscribe({ticker})
    try:
        while True:
            try:
                raw = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "ping"}))
                continue
            await websocket.send_text(raw)
    except (WebSocketDisconnect, ConnectionError, asyncio.CancelledError):
        pass
    except Exception as e:  # noqa: BLE001
        logger.warning("WS live error: %s", e)
    finally:
        await feed.unsubscribe({ticker}, queue)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001 — sudah putus
            pass
