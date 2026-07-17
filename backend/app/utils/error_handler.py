"""Global exception handlers untuk FastAPI.

Mendaftarkan handler agar setiap `AppError` (dan error tak terduga) selalu
dikembalikan sebagai `APIResponse` dengan format konsisten. Stack trace TIDAK
pernah dikirim ke client — hanya `message` + `error_code` yang aman.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.response import APIResponse
from app.utils.errors import AppError, ERROR_UNKNOWN

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(request: Request, exc: AppError):
        logger.warning(
            "AppError [%s] %s — %s %s",
            exc.error_code,
            exc.message,
            request.method,
            request.url.path,
        )
        payload = APIResponse.fail(message=exc.message, error_code=exc.error_code)
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError):
        logger.warning("Validation error — %s %s", request.method, request.url.path)
        payload = APIResponse.fail(
            message="Parameter request tidak valid.",
            error_code="VALIDATION_ERROR",
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception):
        logger.exception(
            "Unhandled error — %s %s", request.method, request.url.path
        )
        payload = APIResponse.fail(
            message="Terjadi kesalahan internal pada server.",
            error_code=ERROR_UNKNOWN,
        )
        return JSONResponse(status_code=500, content=payload.model_dump())
