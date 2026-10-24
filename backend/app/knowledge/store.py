from typing import Any

from qdrant_client import AsyncQdrantClient, models

from ..core.config import get_settings
from .embedder import EMBED_DIM


class KnowledgeStore:
    """Qdrant 向量库访问入口。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncQdrantClient(url=settings.qdrant_url)
        self.collection = settings.qdrant_collection

    async def ping(self) -> bool:
        try:
            await self.client.get_collections()
            return True
        except Exception:
            return False

    async def ensure_collection(self) -> None:
        if await self.client.collection_exists(self.collection):
            return
        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config={
                "dense": models.VectorParams(
                    size=EMBED_DIM, distance=models.Distance.COSINE
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(),
            },
        )

    async def replace_datasource(
        self, datasource_id: int, chunks: list[dict[str, Any]]
    ) -> None:
        await self.ensure_collection()
        await self.client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[self._ds_filter(datasource_id)])
            ),
        )
        if chunks:
            await self.client.upsert(
                collection_name=self.collection,
                points=[self._to_point(c) for c in chunks],
            )

    @staticmethod
    def _ds_filter(datasource_id: int) -> models.FieldCondition:
        return models.FieldCondition(
            key="datasource_id", match=models.MatchValue(value=datasource_id)
        )

    @staticmethod
    def _to_point(chunk: dict[str, Any]) -> models.PointStruct:
        sparse = chunk["sparse"]
        items = sorted(sparse.items())
        return models.PointStruct(
            id=chunk["id"],
            vector={
                "dense": chunk["dense"],
                "sparse": models.SparseVector(
                    indices=[i for i, _ in items],
                    values=[v for _, v in items],
                ),
            },
            payload={
                "datasource_id": chunk["datasource_id"],
                "kind": chunk["kind"],
                "schema": chunk.get("schema"),
                "table": chunk.get("table"),
                "name": chunk["name"],
                "content": chunk["content"],
                "meta": chunk.get("meta"),
            },
        )

    async def search(
        self,
        dense: list[float],
        sparse: dict[int, float],
        datasource_id: int | None = None,
        limit: int = 10,
    ) -> list[models.ScoredPoint]:
        sparse_items = sorted(sparse.items())
        prefetch = [
            models.Prefetch(query=dense, using="dense", limit=20),
            models.Prefetch(
                query=models.SparseVector(
                    indices=[i for i, _ in sparse_items],
                    values=[v for _, v in sparse_items],
                ),
                using="sparse",
                limit=20,
            ),
        ]
        query_filter = None
        if datasource_id is not None:
            query_filter = models.Filter(must=[self._ds_filter(datasource_id)])

        result = await self.client.query_points(
            collection_name=self.collection,
            prefetch=prefetch,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            query_filter=query_filter,
            with_payload=True,
            limit=limit,
        )
        return list(result.points)

    async def close(self) -> None:
        await self.client.close()

