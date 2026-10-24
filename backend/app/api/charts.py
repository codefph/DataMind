from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..models.chart import Chart
from ..schemas.chart import ChartUpdate

router = APIRouter(prefix="/charts", tags=["charts"])


@router.patch("/{chart_id}")
async def update_chart(
    chart_id: int,
    payload: ChartUpdate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    chart = await session.get(Chart, chart_id)
    if chart is None:
        raise HTTPException(status_code=404, detail="图表不存在")
    chart.chart_type = payload.chart_type
    chart.echarts_option = payload.echarts_option
    await session.commit()
    return {
        "id": chart.id,
        "chart_type": chart.chart_type,
        "echarts_option": chart.echarts_option,
    }

