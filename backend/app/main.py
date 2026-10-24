import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from .api import charts, conversations, dashboards, datasources, health, metrics
from .core.config import get_settings
from .core.logging import configure_logging
from .core.middleware import RateLimitMiddleware, RequestContextMiddleware
from .core.rate_limit import SlidingWindowLimiter


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.environment)
    app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(datasources.router, prefix=settings.api_prefix)
    app.include_router(dashboards.router, prefix=settings.api_prefix)
    app.include_router(conversations.router, prefix=settings.api_prefix)
    app.include_router(charts.router, prefix=settings.api_prefix)
    app.include_router(metrics.router, prefix=settings.api_prefix)

    limiter = SlidingWindowLimiter(
        max_requests=max(1, settings.rate_limit_per_minute)
    )
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    app.add_middleware(RequestContextMiddleware)

    logger = structlog.get_logger("app")

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled_error", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})

    return app


app = create_app()

