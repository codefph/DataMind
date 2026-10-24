from typing import Any

from pydantic import BaseModel


class ChartUpdate(BaseModel):
    chart_type: str
    echarts_option: dict[str, Any]

