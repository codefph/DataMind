from typing import Any

from pydantic import BaseModel, Field


class ChartSpec(BaseModel):
    chart_id: str
    title: str
    chart_type: str = Field(description="ECharts 图表类型，不设枚举白名单")
    sql: str
    reasoning: str = Field(description="一句话说明该图的意图")
    echarts_option: dict[str, Any]


class InsightSpec(BaseModel):
    kind: str = Field(description="trend/composition/rank/anomaly/attribution 之一")
    title: str
    body: str
    metric_ref: str = Field(description="关联的指标或字段")


class NarrativeSpec(BaseModel):
    summary: str = Field(description="整体业务解读的一段话")
    highlights: list[str] = Field(description="3~5 条要点", default_factory=list)


class AnalysisPlan(BaseModel):
    charts: list[ChartSpec] = Field(default_factory=list)
    insights: list[InsightSpec] = Field(default_factory=list)

