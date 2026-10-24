from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..bi.echarts import apply_data_to_option
from ..bi.insights import compute_insights
from ..bi.narrator import build_narrative_messages
from ..gateway.router import ModelRouter
from ..knowledge.embedder import LocalHashEmbedder
from ..knowledge.store import KnowledgeStore
from ..models.datasource import Datasource
from ..services.datasource import build_url
from ..sql_exec.executor import execute_readonly
from ..sql_exec.validator import validate_read_only
from .prompts import build_messages
from .schema_chart import AnalysisPlan, NarrativeSpec


class AnalysisPipeline:
    """NL → 检索 → 生成 SQL/ECharts → 校验 → 执行的编排管线。"""

    def __init__(
        self,
        router: ModelRouter | None = None,
        embedder: LocalHashEmbedder | None = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.embedder = embedder or LocalHashEmbedder()

    async def run(
        self,
        question: str,
        ds: Datasource,
        session: AsyncSession,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        context = await self._retrieve_context(question, ds.id)
        messages = build_messages(question, context, history=history)
        plan: AnalysisPlan = await self.router.structured(
            messages, AnalysisPlan, task="analysis"
        )

        url = build_url(ds)
        results: dict[str, Any] = {}
        insights: dict[str, Any] = {}
        for chart in plan.charts:
            validate_read_only(chart.sql, db_type=ds.type)
            result = await execute_readonly(url, chart.sql)
            chart.echarts_option = apply_data_to_option(chart.echarts_option, result)
            results[chart.chart_id] = result
            insights[chart.chart_id] = compute_insights(result)

        chart_insights = self._collect_chart_insights(plan, insights)
        return {
            "plan": plan.model_dump(),
            "results": results,
            "insights": insights,
            "narrative": await self._narrate(question, chart_insights),
        }

    async def stream(
        self,
        question: str,
        ds: Datasource,
        session: AsyncSession,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        """按阶段产出 (event, data)，供 SSE 流式返回。"""
        yield ("start", {"question": question})
        try:
            context = await self._retrieve_context(question, ds.id)
            yield ("retrieved", {"context_preview": context[:800]})

            messages = build_messages(question, context, history=history)
            plan: AnalysisPlan = await self.router.structured(
                messages, AnalysisPlan, task="analysis"
            )

            url = build_url(ds)
            chart_insights: list[dict[str, Any]] = []
            for chart in plan.charts:
                yield (
                    "sql",
                    {
                        "chart_id": chart.chart_id,
                        "title": chart.title,
                        "sql": chart.sql,
                    },
                )
                validate_read_only(chart.sql, db_type=ds.type)
                yield ("executing", {"chart_id": chart.chart_id})
                result = await execute_readonly(url, chart.sql)
                option = apply_data_to_option(chart.echarts_option, result)
                yield (
                    "chart",
                    {
                        "chart_id": chart.chart_id,
                        "title": chart.title,
                        "chart_type": chart.chart_type,
                        "reasoning": chart.reasoning,
                        "echarts_option": option,
                        "data": result,
                    },
                )
                chart_insight_list = compute_insights(result)
                for insight in chart_insight_list:
                    insight["chart_id"] = chart.chart_id
                    yield ("insight", insight)
                chart_insights.append(
                    {
                        "chart_id": chart.chart_id,
                        "title": chart.title,
                        "chart_type": chart.chart_type,
                        "insights": chart_insight_list,
                    }
                )

            narrative = await self._narrate(question, chart_insights)
            if narrative:
                yield ("narrative", narrative)

            yield ("done", {"charts": [c.chart_id for c in plan.charts]})
        except Exception as exc:  # noqa: BLE001
            yield ("error", {"message": f"{type(exc).__name__}: {exc}"})

    async def _retrieve_context(self, question: str, datasource_id: int) -> str:
        dense, sparse = self.embedder.embed(question)
        store = KnowledgeStore()
        try:
            points = await store.search(
                dense, sparse, datasource_id=datasource_id, limit=10
            )
        finally:
            await store.close()
        return "\n".join(
            (p.payload or {}).get("content", "") for p in points
        )

    @staticmethod
    def _collect_chart_insights(
        plan: AnalysisPlan,
        insights: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "chart_id": chart.chart_id,
                "title": chart.title,
                "chart_type": chart.chart_type,
                "insights": insights.get(chart.chart_id, []),
            }
            for chart in plan.charts
        ]

    async def _narrate(
        self,
        question: str,
        chart_insights: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not chart_insights or not any(c["insights"] for c in chart_insights):
            return None
        try:
            narrative = await self.router.structured(
                build_narrative_messages(question, chart_insights),
                NarrativeSpec,
                task="narrative",
            )
            return narrative.model_dump()
        except Exception:  # noqa: BLE001
            return None

