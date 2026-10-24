import time

from fastapi import APIRouter

from ..core.metrics import metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def get_metrics() -> dict:
    return {
        "uptime_seconds": round(time.time() - metrics.started_at, 2),
        "counters": metrics.snapshot(),
    }

