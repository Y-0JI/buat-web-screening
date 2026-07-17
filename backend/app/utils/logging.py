"""Logging terstruktur & middleware request.

- `configure_logging()` mengatur logger root agar mengeluarkan JSON (production)
  atau teks terbaca (development) — mudah di-parse oleh collector log.
- `LoggingMiddleware` mencatat tiap request API: method, path, status, duration.
- Provider diharapkan mencatat request/response/error/durasi via logger standar.
"""

import json
import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

_logger = logging.getLogger("bsjp")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    if settings.env == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            _logger.exception(
                "request_failed method=%s path=%s duration_ms=%.1f",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        _logger.info(
            "request method=%s path=%s status=%d duration_ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
