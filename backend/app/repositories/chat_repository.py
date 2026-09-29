"""Repository chat threads — satu pintu akses percakapan (tanpa business logic).

Menyimpan thread & pesan di DB, di-scope per `device_id` (identitas anonim
perangkat). Semua fungsi mengembalikan dict polos (bukan objek ORM) agar aman
dipakai lintas layer.
"""

from typing import Any, Optional

from sqlalchemy import delete, desc, func, select

from app.database import async_session
from app.database.models import ChatMessage, ChatThread


def _thread_dict(t: ChatThread) -> dict:
    return {
        "id": t.id,
        "title": t.title,
        "model": t.model,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _message_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "reasoning": m.reasoning,
        "tool_calls": m.tool_calls,
        "model": m.model,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


async def create_thread(
    device_id: str, title: Optional[str] = None, model: Optional[str] = None
) -> dict:
    async with async_session() as session:
        thread = ChatThread(
            device_id=device_id,
            title=(title or "Percakapan baru")[:255],
            model=model,
        )
        session.add(thread)
        await session.commit()
        await session.refresh(thread)
        return _thread_dict(thread)


async def list_threads(device_id: str, limit: int = 50) -> list[dict]:
    async with async_session() as session:
        rows = await session.execute(
            select(ChatThread)
            .where(ChatThread.device_id == device_id)
            .order_by(desc(ChatThread.updated_at))
            .limit(limit)
        )
        return [_thread_dict(t) for t in rows.scalars().all()]


async def get_thread(device_id: str, thread_id: int) -> Optional[dict]:
    async with async_session() as session:
        thread = await session.get(ChatThread, thread_id)
        if thread is None or thread.device_id != device_id:
            return None
        msgs = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.id)
        )
        data = _thread_dict(thread)
        data["messages"] = [_message_dict(m) for m in msgs.scalars().all()]
        return data


async def update_thread(
    device_id: str,
    thread_id: int,
    title: Optional[str] = None,
    model: Optional[str] = None,
) -> Optional[dict]:
    async with async_session() as session:
        thread = await session.get(ChatThread, thread_id)
        if thread is None or thread.device_id != device_id:
            return None
        if title is not None:
            thread.title = title[:255]
        if model is not None:
            thread.model = model
        await session.commit()
        await session.refresh(thread)
        return _thread_dict(thread)


async def delete_thread(device_id: str, thread_id: int) -> bool:
    async with async_session() as session:
        thread = await session.get(ChatThread, thread_id)
        if thread is None or thread.device_id != device_id:
            return False
        await session.execute(
            delete(ChatMessage).where(ChatMessage.thread_id == thread_id)
        )
        await session.delete(thread)
        await session.commit()
        return True


async def add_message(
    thread_id: int,
    role: str,
    content: str,
    reasoning: Optional[str] = None,
    tool_calls: Optional[Any] = None,
    model: Optional[str] = None,
) -> dict:
    async with async_session() as session:
        msg = ChatMessage(
            thread_id=thread_id,
            role=role,
            content=content or "",
            reasoning=reasoning,
            tool_calls=tool_calls,
            model=model,
        )
        session.add(msg)
        thread = await session.get(ChatThread, thread_id)
        if thread is not None:
            thread.updated_at = func.now()
        await session.commit()
        await session.refresh(msg)
        return _message_dict(msg)
