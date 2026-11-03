import json
import logging
import sys
import time
from flask import has_request_context, request


class JsonFormatter(logging.Formatter):
    """Custom logging formatter outputting single-line JSON structured logs."""

    def format(self, rec):
        payload = {
            "ts": self.formatTime(rec, "%Y-%m-%dT%H:%M:%SZ"),
            "level": rec.levelname,
            "msg": rec.getMessage(),
        }
        if has_request_context():
            payload["rid"] = request.headers.get("X-Request-Id", "-")
            payload["method"] = request.method
            payload["path"] = request.path

        if hasattr(rec, "s"):
            payload["status"] = rec.s
        if hasattr(rec, "ms"):
            payload["latency_ms"] = rec.ms

        return json.dumps(payload, ensure_ascii=False)


def configure(app):
    """Configure structured logging and request latency monitoring."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))

    @app.before_request
    def _start_timer():
        request._t0 = time.perf_counter()

    @app.after_request
    def _log_request_done(resp):
        if hasattr(request, "_t0"):
            ms = int((time.perf_counter() - request._t0) * 1000)
            app.logger.info(
                "request_completed",
                extra={"s": resp.status_code, "ms": ms},
            )
        return resp

