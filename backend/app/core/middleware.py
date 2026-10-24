import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        structlog.contextvars.bind_contextvars(request_id=request_id)
        logger = structlog.get_logger("http")
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            status = getattr(response, "status_code", 500)
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=status,
                duration_ms=round(duration_ms, 2),
            )
            structlog.contextvars.clear_contextvars()


LIMITED_PATHS = ("/analyze", "/query")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter) -> None:
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request, call_next):
        if request.method == "POST" and any(
            p in request.url.path for p in LIMITED_PATHS
        ):
            if not self.limiter.allow():
                return JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后再试"},
                )
        return await call_next(request)


