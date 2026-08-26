import json as _json
import logging
import sys
from typing import Any

from app.middleware.request_context import client_ip_var, request_id_var


class RequestContextFilter(logging.Filter):
    """Stamps every log record emitted during a request with that
    request's id, so lines from different concurrent requests can be
    told apart in aggregated logs without passing the id through every
    function call by hand."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.client_ip = client_ip_var.get()
        return True


class JSONFormatter(logging.Formatter):
    """Renders log records as single-line JSON so they can be ingested by
    any log aggregator without a parsing layer in between."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "client_ip", "user_id", "role", "path", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return _json.dumps(payload)


def configure_logging(debug: bool = False) -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(RequestContextFilter())
    root.addHandler(handler)

    # Quiet noisy third-party loggers unless we're actively debugging.
    for name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.DEBUG if debug else logging.WARNING)
