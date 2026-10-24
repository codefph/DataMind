import asyncio
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from ..core.metrics import metrics


async def execute_readonly(
    url: str,
    sql: str,
    *,
    limit: int = 1000,
    timeout: float = 10.0,
) -> dict:
    """只读执行并强制行数上限。"""
    cleaned = sql.strip().rstrip(";")
    wrapped = f"SELECT * FROM ({cleaned}) AS _dm LIMIT {int(limit)}"
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            result = await asyncio.wait_for(conn.execute(text(wrapped)), timeout=timeout)
            rows = result.fetchall()
            return {
                "columns": list(result.keys()),
                "rows": [
                    {k: _serialize(v) for k, v in row._mapping.items()}
                    for row in rows
                ],
                "count": len(rows),
            }
    finally:
        await engine.dispose()
        metrics.inc("sql_executions")


def _serialize(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value

