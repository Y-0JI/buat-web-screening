"""Async Request Scheduler — pembatas rate global antar-provider.

Memastikan total request ke sumber eksternal (Yahoo Finance / IDX) tidak
melebihi `settings.rate_limit_per_minute` (sliding window 60 detik). Provider
memanggil `await request_scheduler.acquire()` sebelum tiap request; bila窗口
penuh, menunggu hingga slot bebas. Tanpa dependency baru.

Catatan: ini pembatas request lintas-provider, berbeda dengan `scheduler.py`
(di root app) yang hanya untuk batch daily scan.
"""

import asyncio
import time
from collections import deque
from typing import Deque

from app.config import settings


class RequestScheduler:
    def __init__(self, max_per_minute: int | None = None) -> None:
        self._max = max_per_minute or settings.rate_limit_per_minute or 15
        self._window: Deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if self._max <= 0:
            return
        while True:
            async with self._lock:
                now = time.time()
                # buang timestamp yang sudah lewat 60 detik
                while self._window and now - self._window[0] >= 60:
                    self._window.popleft()
                if len(self._window) < self._max:
                    self._window.append(now)
                    return
                # estimasi waktu tunggu hingga slot paling tua keluar窗口
                wait = 60 - (now - self._window[0]) + 0.05
            if wait > 0:
                await asyncio.sleep(wait)


request_scheduler = RequestScheduler()
