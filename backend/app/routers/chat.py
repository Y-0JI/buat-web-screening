"""Router chat — agen streaming (SSE) + fallback non-streaming.

Kontrak: klien mengirim SATU pesan baru (+ opsional `thread_id`). Bila
`thread_id` ada, histori diambil dari DB; bila tidak, thread baru dibuat dan
id-nya dikirim lewat event `thread`. Pesan user & asisten disimpan ke thread
(identitas anonim via header `X-Device-Id`).
"""

import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ai.agent import stream_agent
from app.config import settings
from app.repositories import chat_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[int] = None
    model: Optional[str] = None
    mode: str = "BSJP"
    context: Optional[dict] = None


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


async def _prepare(req: ChatRequest, device: str) -> tuple[int, list[dict], Optional[dict]]:
    """Siapkan thread & histori. Return (thread_id, history, thread_event)."""
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Pesan kosong.")

    thread_event = None
    if req.thread_id is not None:
        thread = await chat_repository.get_thread(device, req.thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread tidak ditemukan.")
        tid = req.thread_id
        history = [{"role": m["role"], "content": m["content"]} for m in thread["messages"]]
        if not thread["messages"]:
            await chat_repository.update_thread(device, tid, title=message[:60])
    else:
        created = await chat_repository.create_thread(device, title=message[:60], model=req.model)
        tid = created["id"]
        history = []
        thread_event = {"type": "thread", "id": tid, "title": created["title"]}

    await chat_repository.add_message(tid, "user", message, model=req.model)
    history.append({"role": "user", "content": message})
    if req.model:
        await chat_repository.update_thread(device, tid, model=req.model)
    return tid, history, thread_event


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, x_device_id: Optional[str] = Header(default=None)
):
    if not x_device_id or not x_device_id.strip():
        raise HTTPException(status_code=400, detail="Header X-Device-Id wajib.")
    device = x_device_id.strip()[:64]

    tid, history, thread_event = await _prepare(req, device)

    async def gen() -> AsyncGenerator[str, None]:
        if thread_event:
            yield _sse(thread_event)
        assistant = {"content": "", "reasoning": "", "tool_calls": []}
        async for event in stream_agent(
            history, req.model or settings.ai_model, req.mode, req.context
        ):
            if event["type"] == "done":
                assistant = event
            yield _sse(event)
        try:
            await chat_repository.add_message(
                tid,
                "assistant",
                assistant.get("content", ""),
                reasoning=assistant.get("reasoning"),
                tool_calls=assistant.get("tool_calls") or None,
                model=req.model or settings.ai_model,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Gagal simpan pesan asisten: %s", e)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat")
async def chat(req: ChatRequest, x_device_id: Optional[str] = Header(default=None)):
    if not x_device_id or not x_device_id.strip():
        raise HTTPException(status_code=400, detail="Header X-Device-Id wajib.")
    device = x_device_id.strip()[:64]

    if not settings.ai_api_key:
        return {"success": False, "error": "AI_API_KEY belum diisi"}

    try:
        tid, history, _ = await _prepare(req, device)
    except HTTPException:
        raise

    content, reasoning, tools = "", "", []
    async for event in stream_agent(
        history, req.model or settings.ai_model, req.mode, req.context
    ):
        if event["type"] == "done":
            content = event.get("content", "")
            reasoning = event.get("reasoning", "")
            tools = event.get("tool_calls", [])
        elif event["type"] == "error":
            return {"success": False, "error": event.get("message"), "thread_id": tid}

    await chat_repository.add_message(
        tid, "assistant", content, reasoning=reasoning or None,
        tool_calls=tools or None, model=req.model or settings.ai_model,
    )
    return {
        "success": True,
        "thread_id": tid,
        "reply": content,
        "reasoning": reasoning,
        "tool_calls": tools,
    }
