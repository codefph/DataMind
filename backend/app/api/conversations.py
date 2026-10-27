import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.orchestrator import AnalysisPipeline
from ..core.database import get_session
from ..models.chart import Chart
from ..models.conversation import Conversation, Message
from ..schemas.conversation import (
    ConversationCreate,
    ConversationRead,
    ConversationUpdate,
    MessageRead,
    QueryRequest,
)
from ..services.datasource import get_datasource

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationRead, status_code=201)
async def create_conversation(
    payload: ConversationCreate, session: AsyncSession = Depends(get_session)
) -> Conversation:
    conv = Conversation(
        datasource_id=payload.datasource_id,
        title=payload.title or "新会话",
    )
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    session: AsyncSession = Depends(get_session),
) -> list[Conversation]:
    result = await session.execute(
        select(Conversation).order_by(Conversation.id.desc())
    )
    return list(result.scalars().all())


@router.patch("/{conv_id}", response_model=ConversationRead)
async def update_conversation(
    conv_id: int,
    payload: ConversationUpdate,
    session: AsyncSession = Depends(get_session),
) -> Conversation:
    conv = await session.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    conv.title = payload.title
    await session.commit()
    await session.refresh(conv)
    return conv


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    conv = await session.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    await session.execute(
        delete(Message).where(Message.conversation_id == conv_id)
    )
    await session.execute(delete(Chart).where(Chart.conversation_id == conv_id))
    await session.delete(conv)
    await session.commit()


@router.get("/{conv_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conv_id: int, session: AsyncSession = Depends(get_session)
) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.id)
    )
    return list(result.scalars().all())


@router.get("/{conv_id}/charts")
async def list_charts(
    conv_id: int, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Chart).where(Chart.conversation_id == conv_id).order_by(Chart.id)
    )
    return [
        {
            "chart_id": str(c.id),
            "title": c.title,
            "chart_type": c.chart_type,
            "sql": c.sql,
            "echarts_option": c.echarts_option,
            "insight": c.insight or {"items": []},
        }
        for c in result.scalars().all()
    ]


@router.post("/{conv_id}/query")
async def query_conversation(
    conv_id: int,
    payload: QueryRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    conv = await session.get(Conversation, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if conv.datasource_id is None:
        raise HTTPException(status_code=400, detail="会话未绑定数据源")
    ds = await get_datasource(session, conv.datasource_id)
    if ds is None:
        raise HTTPException(status_code=400, detail="数据源不存在")

    user_msg = Message(conversation_id=conv_id, role="user", content=payload.question)
    session.add(user_msg)
    await session.commit()

    history = await _build_history(session, conv_id)
    pipeline = AnalysisPipeline()

    async def event_stream():
        sql_map: dict[str, str] = {}
        chart_items: list[dict[str, Any]] = []
        insights_by_chart: dict[str, list[dict[str, Any]]] = {}
        narrative: dict[str, Any] | None = None
        success = False
        async for event, data in pipeline.stream(
            payload.question, ds, session, history=history
        ):
            if event == "sql":
                sql_map[data["chart_id"]] = data["sql"]
            elif event == "chart":
                data["sql"] = sql_map.get(data["chart_id"], "")
                chart_items.append(data)
            elif event == "insight":
                insights_by_chart.setdefault(data.get("chart_id", ""), []).append(data)
            elif event == "narrative":
                narrative = data
            elif event == "done":
                success = True
            yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        if success and chart_items:
            for ch in chart_items:
                session.add(
                    Chart(
                        conversation_id=conv_id,
                        title=ch["title"],
                        chart_type=ch["chart_type"],
                        sql=ch["sql"],
                        echarts_option=ch["echarts_option"],
                        insight={"items": insights_by_chart.get(ch["chart_id"], [])},
                    )
                )
            summary = "已生成：" + "、".join(
                f"{ch['title']}（{ch['chart_type']}）" for ch in chart_items
            )
            slim = [
                {
                    "chart_id": ch["chart_id"],
                    "title": ch["title"],
                    "chart_type": ch["chart_type"],
                    "sql": ch["sql"],
                    "echarts_option": ch["echarts_option"],
                }
                for ch in chart_items
            ]
            session.add(
                Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=summary,
                    meta={"charts": slim, "narrative": narrative},
                )
            )
        else:
            session.add(
                Message(conversation_id=conv_id, role="assistant", content="生成失败")
            )
        await session.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _build_history(
    session: AsyncSession, conv_id: int, limit: int = 8
) -> list[dict[str, str]]:
    result = await session.execute(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()

    history: list[dict[str, str]] = []
    for msg in messages:
        content = msg.content
        if msg.role == "assistant" and msg.meta and msg.meta.get("charts"):
            detail = "; ".join(
                f"{c['title']}({c['chart_type']}): {c['sql']}"
                for c in msg.meta["charts"]
            )
            content = f"{msg.content}\n{detail}"
        history.append({"role": msg.role, "content": content})
    return history
