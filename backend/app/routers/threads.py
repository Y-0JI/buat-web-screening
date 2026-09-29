"""Router threads — CRUD percakapan, di-scope per perangkat via `X-Device-Id`.

Tanpa auth: identitas anonim per perangkat. Header `X-Device-Id` wajib; thread
perangkat lain tidak dapat diakses.
"""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.repositories import chat_repository

router = APIRouter(prefix="/api", tags=["threads"])


def _device_id(x_device_id: Optional[str]) -> str:
    if not x_device_id or not x_device_id.strip():
        raise HTTPException(status_code=400, detail="Header X-Device-Id wajib diisi.")
    return x_device_id.strip()[:64]


class ThreadCreate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None


class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None


@router.get("/threads")
async def list_threads(x_device_id: Optional[str] = Header(default=None)):
    device = _device_id(x_device_id)
    return {"success": True, "data": await chat_repository.list_threads(device)}


@router.post("/threads")
async def create_thread(
    body: ThreadCreate, x_device_id: Optional[str] = Header(default=None)
):
    device = _device_id(x_device_id)
    thread = await chat_repository.create_thread(device, body.title, body.model)
    return {"success": True, "data": thread}


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: int, x_device_id: Optional[str] = Header(default=None)
):
    device = _device_id(x_device_id)
    thread = await chat_repository.get_thread(device, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread tidak ditemukan.")
    return {"success": True, "data": thread}


@router.patch("/threads/{thread_id}")
async def update_thread(
    thread_id: int,
    body: ThreadUpdate,
    x_device_id: Optional[str] = Header(default=None),
):
    device = _device_id(x_device_id)
    thread = await chat_repository.update_thread(
        device, thread_id, body.title, body.model
    )
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread tidak ditemukan.")
    return {"success": True, "data": thread}


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: int, x_device_id: Optional[str] = Header(default=None)
):
    device = _device_id(x_device_id)
    ok = await chat_repository.delete_thread(device, thread_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Thread tidak ditemukan.")
    return {"success": True}
