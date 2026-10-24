from fastapi import APIRouter, Response, status

from ..knowledge.store import KnowledgeStore

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, str]:
    store = KnowledgeStore()
    ok = await store.ping()
    await store.close()
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "qdrant": "unreachable"}
    return {"status": "ready", "qdrant": "reachable"}

