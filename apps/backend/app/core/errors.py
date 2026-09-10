"""Error handling foundation for AstraTrace.

Defines domain exceptions and global FastAPI exception handlers returning RFC 7807 problem details.
"""
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from apps.backend.app.core.logging import logger, request_id_ctx


class AstraTraceException(Exception):
    """Base exception for all AstraTrace domain errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AstraTraceException):
    """Raised when an asset or resource is not found."""
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND, details=details)


class ValidationError(AstraTraceException):
    """Raised when input fails domain validation rules."""
    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        code = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", status.HTTP_422_UNPROCESSABLE_ENTITY)
        super().__init__(message, status_code=code, details=details)


def register_error_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI app."""

    @app.exception_handler(AstraTraceException)
    async def handle_astratrace_exception(request: Request, exc: AstraTraceException) -> JSONResponse:
        req_id = request_id_ctx.get()
        logger.warning(f"Domain error [{exc.status_code}]: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "type": f"urn:astratrace:error:{exc.status_code}",
                "title": exc.message,
                "status": exc.status_code,
                "details": exc.details,
                "request_id": req_id,
            }
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        req_id = request_id_ctx.get()
        logger.error(f"Unhandled server error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "type": "urn:astratrace:error:500",
                "title": "Internal Server Error",
                "status": 500,
                "details": {"message": "An unexpected server error occurred."},
                "request_id": req_id,
            }
        )
