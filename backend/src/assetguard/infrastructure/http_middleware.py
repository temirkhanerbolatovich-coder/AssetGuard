from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from assetguard.infrastructure.config import get_settings

logger = logging.getLogger("assetguard.http")


class SecurityAndRateLimitMiddleware(BaseHTTPMiddleware):
    """Small single-instance limiter; production proxy should enforce a second layer."""

    def __init__(self, app):
        super().__init__(app)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        started = time.monotonic()
        protected = request.url.path.startswith(("/admin", "/internal", "/auth/login", "/glpi-agent"))
        if protected and self._limited(request):
            logger.warning("rate_limit_exceeded path=%s client=%s", request.url.path, self._client(request))
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded."}, headers={"Retry-After": "60"})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store" if protected else response.headers.get("Cache-Control", "no-cache")
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%d",
            request.method, request.url.path, response.status_code,
            int((time.monotonic() - started) * 1000),
        )
        return response

    def _client(self, request: Request) -> str:
        return request.client.host if request.client else "unknown"

    def _limited(self, request: Request) -> bool:
        now = time.monotonic()
        key = f"{self._client(request)}:{request.url.path.split('/')[1]}"
        limit = get_settings().rate_limit_per_minute
        with self._lock:
            bucket = self._requests[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                return True
            bucket.append(now)
            return False
