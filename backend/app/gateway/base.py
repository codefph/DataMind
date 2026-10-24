from typing import Any, AsyncIterator, Protocol


class ModelGateway(Protocol):
    """LLM / Embedding / Rerank 的统一抽象。"""

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        task: str = "default",
        response_format: type | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

    def chat_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        task: str = "default",
    ) -> AsyncIterator[str]: ...

    async def embed(
        self,
        texts: list[str],
        *,
        task: str = "default",
    ) -> list[list[float]]: ...

    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]: ...

