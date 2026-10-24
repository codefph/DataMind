import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.orchestrator import AnalysisPipeline
from ..core.database import get_session
from ..knowledge.crawler import crawl_schema
from ..knowledge.embedder import LocalHashEmbedder
from ..knowledge.store import KnowledgeStore
from ..knowledge.sync import sync_datasource
from ..models.datasource import Datasource
from ..schemas.datasource import (
    AnalyzeRequest,
    DatasourceCreate,
    DatasourceRead,
    TestResult,
)
from ..services.datasource import (
    build_url,
    create_datasource,
    delete_datasource,
    get_datasource,
    list_datasources,
    test_connection,
)

router = APIRouter(prefix="/datasources", tags=["datasources"])


async def _get_or_404(session: AsyncSession, ds_id: int) -> Datasource:
    ds = await get_datasource(session, ds_id)
    if ds is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ds


@router.get("", response_model=list[DatasourceRead])
async def list_ds(session: AsyncSession = Depends(get_session)) -> list[Datasource]:
    return await list_datasources(session)


@router.post("", response_model=DatasourceRead, status_code=201)
async def create_ds(
    payload: DatasourceCreate, session: AsyncSession = Depends(get_session)
) -> Datasource:
    return await create_datasource(session, payload)


@router.delete("/{ds_id}", status_code=204)
async def delete_ds(ds_id: int, session: AsyncSession = Depends(get_session)) -> None:
    await _get_or_404(session, ds_id)
    await delete_datasource(session, ds_id)


@router.get("/{ds_id}/test", response_model=TestResult)
async def test_ds(
    ds_id: int, session: AsyncSession = Depends(get_session)
) -> TestResult:
    ds = await _get_or_404(session, ds_id)
    return await test_connection(ds)


@router.get("/{ds_id}/schema")
async def schema_ds(ds_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    ds = await _get_or_404(session, ds_id)
    try:
        return await crawl_schema(build_url(ds), db_type=ds.type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{ds_id}/sync")
async def sync_ds(ds_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    await _get_or_404(session, ds_id)
    try:
        return await sync_datasource(session, ds_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{ds_id}/search")
async def search_ds(
    ds_id: int,
    q: str,
    limit: int = 5,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await _get_or_404(session, ds_id)
    embedder = LocalHashEmbedder()
    dense, sparse = embedder.embed(q)
    store = KnowledgeStore()
    try:
        points = await store.search(dense, sparse, datasource_id=ds_id, limit=limit)
    finally:
        await store.close()
    return {
        "query": q,
        "hits": [
            {"id": p.id, "score": p.score, "payload": p.payload} for p in points
        ],
    }


@router.post("/{ds_id}/analyze")
async def analyze_ds(
    ds_id: int,
    payload: AnalyzeRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    ds = await _get_or_404(session, ds_id)
    pipeline = AnalysisPipeline()
    return await pipeline.run(payload.question, ds, session)


@router.post("/{ds_id}/analyze/stream")
async def analyze_stream(
    ds_id: int,
    payload: AnalyzeRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    ds = await _get_or_404(session, ds_id)
    pipeline = AnalysisPipeline()

    async def event_stream():
        async for event, data in pipeline.stream(payload.question, ds, session):
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

