from __future__ import annotations

from typing import Any, AsyncIterator

import instructor
import litellm
from pydantic import BaseModel


class LitellmProvider:
    """基于 LiteLLM 的多厂商适配实现。"""

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0,
    ) -> Any:
        return await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
        )

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in response:
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None) if delta else None
            if content:
                yield content

    async def structured(
        self,
        model: str,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        client = instructor.from_litellm(litellm.acompletion)
        return await client.chat.completions.create(
            response_model=response_model,
            messages=messages,
            model=model,
        )

    async def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        response = await litellm.aembedding(model=model, input=texts)
        result: list[list[float]] = []
        for item in response.data:
            vector = getattr(item, "embedding", None)
            if vector is None and isinstance(item, dict):
                vector = item.get("embedding")
            result.append(list(vector or []))
        return result

