"""Structured JSON logging foundation for AstraTrace.

Provides structured logging with correlation/request ID tracing and secret redaction.
"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

# Context variable for request correlation ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Sensitive keys to redact from logs
SENSITIVE_KEYS = {"password", "secret", "token", "authorization", "key", "access_key"}


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include request ID if set in current context
        req_id = request_id_ctx.get()
        if req_id:
            log_obj["request_id"] = req_id

        # Include exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Include extra fields if provided, redacting sensitive keys
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for k, v in record.extra.items():
                if k.lower() in SENSITIVE_KEYS:
                    log_obj[k] = "[REDACTED]"
                else:
                    log_obj[k] = v

        return json.dumps(log_obj)


def setup_logging(level: str = "INFO") -> None:
    """Configures root logger with JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # Suppress verbose noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("astratrace")


def get_logger(name: str = "astratrace") -> logging.Logger:
    """Returns a named logger for an AstraTrace subsystem."""
    return logging.getLogger(name)
