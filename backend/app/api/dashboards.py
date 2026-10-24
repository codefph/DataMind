from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_session
from ..models.chart import Dashboard
from ..schemas.dashboard import DashboardCreate, DashboardRead

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.post("", response_model=DashboardRead, status_code=201)
async def create_dashboard(
    payload: DashboardCreate, session: AsyncSession = Depends(get_session)
) -> Dashboard:
    dashboard = Dashboard(title=payload.title, layout=payload.layout)
    session.add(dashboard)
    await session.commit()
    await session.refresh(dashboard)
    return dashboard


@router.get("", response_model=list[DashboardRead])
async def list_dashboards(
    session: AsyncSession = Depends(get_session),
) -> list[Dashboard]:
    result = await session.execute(select(Dashboard).order_by(Dashboard.id.desc()))
    return list(result.scalars().all())


@router.get("/{dashboard_id}", response_model=DashboardRead)
async def get_dashboard(
    dashboard_id: int, session: AsyncSession = Depends(get_session)
) -> Dashboard:
    dashboard = await session.get(Dashboard, dashboard_id)
    if dashboard is None:
        raise HTTPException(status_code=404, detail="看板不存在")
    return dashboard

