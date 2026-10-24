from typing import Any

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

SYSTEM_SCHEMAS = {
    "postgresql": {"information_schema", "pg_catalog", "pg_toast"},
    "mysql": {"information_schema", "mysql", "performance_schema", "sys"},
    "mariadb": {"information_schema", "mysql", "performance_schema", "sys"},
    "clickhouse": {"system", "INFORMATION_SCHEMA"},
}


async def crawl_schema(url: str, db_type: str = "postgresql") -> dict[str, Any]:
    """读取目标库的 Schema 元数据（表、字段、类型、注释、主键）。"""
    engine = create_async_engine(url, pool_pre_ping=True)
    excluded = SYSTEM_SCHEMAS.get(db_type, set())

    def _crawl(sync_conn: Any) -> dict[str, Any]:
        insp = inspect(sync_conn)
        schemas = [s for s in insp.get_schema_names() if s not in excluded]
        tables: list[dict[str, Any]] = []
        for schema in schemas:
            for table in insp.get_table_names(schema=schema):
                cols = insp.get_columns(table, schema=schema)
                pk_cols = set(
                    insp.get_pk_constraint(table, schema=schema).get(
                        "constrained_columns", []
                    )
                )
                table_comment = insp.get_table_comment(table, schema=schema).get("text")
                tables.append(
                    {
                        "schema": schema,
                        "name": table,
                        "comment": table_comment,
                        "columns": [
                            {
                                "name": c.get("name"),
                                "type": str(c.get("type")),
                                "nullable": c.get("nullable"),
                                "default": (
                                    str(c.get("default"))
                                    if c.get("default") is not None
                                    else None
                                ),
                                "comment": c.get("comment"),
                                "primary_key": c.get("name") in pk_cols,
                            }
                            for c in cols
                        ],
                    }
                )
        return {"tables": tables}

    try:
        async with engine.connect() as conn:
            return await conn.run_sync(_crawl)
    finally:
        await engine.dispose()

