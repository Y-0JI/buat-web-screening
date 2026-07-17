"""Definisi error terpusat untuk Data Layer.

Semua error di Data Layer diwakili oleh subclass dari `AppError` dengan
`error_code` tetap (string) agar mudah dipetakan ke response API yang konsisten
dan agar frontend bisa menangani kasus tertentu secara terprogram.
"""

from typing import Optional

ERROR_INVALID_TICKER: str = "INVALID_TICKER"
ERROR_PROVIDER_TIMEOUT: str = "PROVIDER_TIMEOUT"
ERROR_DATA_NOT_FOUND: str = "DATA_NOT_FOUND"
ERROR_RATE_LIMITED: str = "RATE_LIMITED"
ERROR_NETWORK_ERROR: str = "NETWORK_ERROR"
ERROR_UNKNOWN: str = "UNKNOWN_ERROR"


class AppError(Exception):
    """Base class untuk semua error terstruktur di aplikasi.

    Atribut:
        error_code: Kode error stabil (lihat konstanta ERROR_*).
        message: Pesan manusiawi yang aman dikirim ke client.
        status_code: HTTP status yang akan dikembalikan.
    """

    error_code: str = ERROR_UNKNOWN
    status_code: int = 500

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code
        self.message = message
        super().__init__(message)


class ProviderError(AppError):
    """Error dari sumber data eksternal (Yahoo Finance, dsb)."""


class ServiceError(AppError):
    """Error dari business logic / validasi di layer Service."""


class InvalidTickerError(ServiceError):
    error_code = ERROR_INVALID_TICKER
    status_code = 400


class DataNotFoundError(ServiceError):
    error_code = ERROR_DATA_NOT_FOUND
    status_code = 404


class ProviderTimeoutError(ProviderError):
    error_code = ERROR_PROVIDER_TIMEOUT
    status_code = 504


class RateLimitError(ProviderError):
    error_code = ERROR_RATE_LIMITED
    status_code = 429


class NetworkError(ProviderError):
    error_code = ERROR_NETWORK_ERROR
    status_code = 502
