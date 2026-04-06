"""
Structured request/response logging middleware.

Logs every HTTP request with:
  - method, path, status_code
  - duration_ms (wall-clock time for the handler)
  - client IP
  - request_id (injected into X-Request-ID response header)

Uses structlog for JSON-compatible output — compatible with Railway / Datadog / Loki.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that emits one structured log line per request.

    Skips noisy endpoints (/health, /docs, /redoc, /openapi.json) so
    infra health checks don't pollute production logs.
    """

    _SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        log.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
            request_id=request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response
