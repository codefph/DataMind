from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.knowledge import KnowledgeDoc
from ..services.datasource import build_url, get_datasource
from .chunker import build_chunks
from .crawler import crawl_schema
from .embedder import LocalHashEmbedder
from .store import KnowledgeStore


async def sync_datasource(session: AsyncSession, ds_id: int) -> dict:
    ds = await get_datasource(session, ds_id)
    if ds is None:
        raise LookupError("数据源不存在")

    schema = await crawl_schema(build_url(ds), db_type=ds.type)
    chunks = build_chunks(ds_id, schema)

    embedder = LocalHashEmbedder()
    for chunk in chunks:
        chunk["datasource_id"] = ds_id
        dense, sparse = embedder.embed(chunk["content"])
        chunk["dense"] = dense
        chunk["sparse"] = sparse

    store = KnowledgeStore()
    try:
        await store.replace_datasource(ds_id, chunks)
    finally:
        await store.close()

    await _persist_docs(session, ds_id, chunks)
    return {
        "datasource_id": ds_id,
        "tables": len(schema.get("tables", [])),
        "chunks": len(chunks),
    }


async def _persist_docs(
    session: AsyncSession, ds_id: int, chunks: list[dict]
) -> None:
    rows = [
        {
            "datasource_id": ds_id,
            "kind": c["kind"],
            "name": c["name"],
            "content": c["content"],
            "meta": c["meta"],
            "chunk_hash": c["id"],
        }
        for c in chunks
    ]
    if not rows:
        return

    stmt = pg_insert(KnowledgeDoc).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[KnowledgeDoc.chunk_hash],
        set_={
            "content": stmt.excluded.content,
            "meta": stmt.excluded.meta,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)
    await session.commit()

