"""Test CRUD thread + isolasi perangkat (tanpa jaringan).

Jalan: ./.venv/bin/python test_threads.py
"""

import asyncio
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import engine
from app.database.models import Base
from app.repositories import chat_repository
from app.routers.threads import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


async def _init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def test_crud_and_isolation():
    h1 = {"X-Device-Id": "dev-test-threads-1"}
    h2 = {"X-Device-Id": "dev-test-threads-2"}

    r = client.post("/api/threads", json={"title": "T1", "model": "coba9router"}, headers=h1)
    assert r.status_code == 200, r.text
    tid = r.json()["data"]["id"]

    asyncio.run(chat_repository.add_message(tid, "user", "halo"))
    asyncio.run(chat_repository.add_message(tid, "assistant", "hai", reasoning="..."))

    r = client.get(f"/api/threads/{tid}", headers=h1)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert len(data["messages"]) == 2, data
    assert data["messages"][1]["reasoning"] == "..."

    assert client.get(f"/api/threads/{tid}", headers=h2).status_code == 404
    assert client.patch(f"/api/threads/{tid}", json={"title": "X"}, headers=h2).status_code == 404
    assert client.delete(f"/api/threads/{tid}", headers=h2).status_code == 404

    r = client.get("/api/threads", headers=h1)
    assert any(t["id"] == tid for t in r.json()["data"])

    r = client.patch(f"/api/threads/{tid}", json={"title": "Renamed"}, headers=h1)
    assert r.json()["data"]["title"] == "Renamed"

    assert client.delete(f"/api/threads/{tid}", headers=h1).json()["success"]
    assert client.get(f"/api/threads/{tid}", headers=h1).status_code == 404
    assert client.get("/api/threads").status_code == 400


def main():
    asyncio.run(_init())
    test_crud_and_isolation()
    print("OK: test_threads lolos")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        print("FAIL:", e)
        sys.exit(1)
