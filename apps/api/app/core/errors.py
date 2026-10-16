from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel


class ErrorCode(str, Enum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    TARGET_BLOCKED = "TARGET_BLOCKED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TARGET_TIMEOUT = "TARGET_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorEnvelope(BaseModel):
    error: "ErrorBody"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = {}


def http_status_for(code: ErrorCode) -> int:
    return {
        ErrorCode.UNAUTHENTICATED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.TARGET_BLOCKED: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.CONFLICT: 409,
        ErrorCode.VALIDATION_ERROR: 422,
        ErrorCode.TARGET_TIMEOUT: 504,
        ErrorCode.INTERNAL_ERROR: 500,
    }[code]


class AppError(Exception):
    """Structured application error."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        *,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self._status_code = status_code

    @property
    def status_code(self) -> int:
        return self._status_code if self._status_code is not None else http_status_for(self.code)

    def to_envelope(self) -> Dict[str, Any]:
        return {"error": {"code": self.code.value, "message": self.message, "details": self.details}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:  # type: ignore[misc]
        return JSONResponse(status_code=exc.status_code, content=exc.to_envelope())

    async def _http_exc_handler(_: Request, exc: StarletteHTTPException | HTTPException) -> JSONResponse:  # type: ignore[misc]
        code_map = {401: ErrorCode.UNAUTHENTICATED, 403: ErrorCode.FORBIDDEN, 404: ErrorCode.NOT_FOUND, 409: ErrorCode.CONFLICT, 422: ErrorCode.VALIDATION_ERROR, 504: ErrorCode.TARGET_TIMEOUT}
        code = code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code.value, "message": str(exc.detail) if getattr(exc, "detail", None) else code.value, "details": {}}},
        )

    app.add_exception_handler(StarletteHTTPException, _http_exc_handler)
    app.add_exception_handler(HTTPException, _http_exc_handler)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[misc]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": "The request is invalid.",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        # Never leak stack traces or exception text publicly.
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR.value,
                    "message": "An unexpected internal error occurred.",
                    "details": {},
                }
            },
        )
