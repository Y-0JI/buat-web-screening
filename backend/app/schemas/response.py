"""Skema respons API standar untuk seluruh endpoint.

Semua endpoint harus mengembalikan `APIResponse` (atau subclass generic-nya)
agar format respons konsisten:

    sukses : {success: true,  message, data}
    error  : {success: false, message, error_code}
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = ""
    data: Optional[T] = None
    error_code: Optional[str] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, message: str = "OK") -> "APIResponse[T]":
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, error_code: Optional[str] = None) -> "APIResponse[T]":
        return cls(success=False, message=message, error_code=error_code)
