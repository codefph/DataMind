from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator

from pydantic import BaseModel

from ..core.config import get_settings
from ..core.metrics import metrics
from .provider import LitellmProvider

logger = logging.getLogger("datamind.gateway")


class GatewayError(Exception):
    """模型网关调用失败。"""


class ModelRouter:
    """模型路由、降级与计量入口。"""

    def __init__(self, provider: LitellmProvider | None = None) -> None:
        self.settings = get_settings()
        self.provider = provider or LitellmProvider()

    def chain_for(self, task: str) -> list[str]:
        fallbacks = [
            item.strip()
            for item in self.settings.model_fallbacks.split(",")
            if item.strip()
        ]
        return [self.settings.model_default, *fallbacks]

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        task: str = "default",
        **kwargs: Any,
    ) -> dict[str, Any]:
        async def call(model: str) -> dict[str, Any]:
            response = await self.provider.complete(model, messages, **kwargs)
            return _normalize_response(response)

        return await self._with_fallback(task, call)

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        *,
        task: str = "default",
    ) -> AsyncIterator[str]:
        chain = self.chain_for(task)
        last_err: Exception | None = None
        for model in chain:
            started = False
            try:
                async for delta in self.provider.complete_stream(model, messages):
                    started = True
                    yield delta
                self._record(model, task, ok=True)
                return
            except Exception as exc:  # noqa: BLE001
                self._record(model, task, ok=False, err=str(exc))
                last_err = exc
                if started:
                    raise GatewayError(str(exc)) from exc
        raise GatewayError(str(last_err)) from last_err

    async def structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[BaseModel],
        *,
        task: str = "default",
    ) -> BaseModel:
        async def call(model: str) -> BaseModel:
            return await self.provider.structured(model, messages, response_model)

        return await self._with_fallback(task, call)

    async def embed(
        self,
        texts: list[str],
        *,
        task: str = "embedding",
    ) -> list[list[float]]:
        model = self.settings.embedding_default
        try:
            start = time.perf_counter()
            result = await self.provider.embed(model, texts)
            self._record(model, task, ok=True, latency=time.perf_counter() - start)
            return result
        except Exception as exc:  # noqa: BLE001
            self._record(model, task, ok=False, err=str(exc))
            raise GatewayError(str(exc)) from exc

    async def _with_fallback(self, task: str, fn: Any) -> Any:
        chain = self.chain_for(task)
        last_err: Exception | None = None
        for model in chain:
            try:
                start = time.perf_counter()
                result = await fn(model)
                self._record(model, task, ok=True, latency=time.perf_counter() - start)
                return result
            except Exception as exc:  # noqa: BLE001
                self._record(model, task, ok=False, err=str(exc))
                last_err = exc
        raise GatewayError(str(last_err)) from last_err

    def _record(
        self,
        model: str,
        task: str,
        *,
        ok: bool,
        latency: float | None = None,
        err: str | None = None,
    ) -> None:
        metrics.inc(f"gateway_calls:{task}:{'ok' if ok else 'error'}")
        logger.info(
            "gateway_call model=%s task=%s ok=%s latency=%s err=%s",
            model,
            task,
            ok,
            round(latency, 3) if latency is not None else None,
            err,
        )


def _normalize_response(response: Any) -> dict[str, Any]:
    choices = getattr(response, "choices", None)
    content = ""
    if choices:
        message = getattr(choices[0], "message", None)
        if message is not None:
            content = getattr(message, "content", None) or ""
    usage = {}
    usage_obj = getattr(response, "usage", None)
    if usage_obj is not None:
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
            "completion_tokens": getattr(usage_obj, "completion_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
    return {"content": content, "usage": usage}

