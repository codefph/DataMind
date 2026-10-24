from hashlib import sha1
from typing import Any
from uuid import UUID


def _point_id(datasource_id: int, kind: str, key: str) -> str:
    digest = sha1(f"{datasource_id}:{kind}:{key}".encode("utf-8")).hexdigest()
    return str(UUID(hex=digest[:32]))


def build_chunks(datasource_id: int, schema: dict[str, Any]) -> list[dict[str, Any]]:
    """把 Schema 元数据切成表级 + 字段级 chunk。"""
    chunks: list[dict[str, Any]] = []

    for table in schema.get("tables", []):
        schema_name = table.get("schema")
        table_name = table.get("name")
        columns = table.get("columns", [])
        table_key = f"{schema_name}.{table_name}"

        col_summary = ", ".join(
            f"{c.get('name')}({c.get('type')})"
            + ("[主键]" if c.get("primary_key") else "")
            for c in columns
        )
        table_text = (
            f"表 {table_key}。表注释：{table.get('comment') or '无'}。"
            f"字段：{col_summary}"
        )
        chunks.append(
            {
                "id": _point_id(datasource_id, "table", table_key),
                "kind": "table",
                "schema": schema_name,
                "table": table_name,
                "name": table_key,
                "content": table_text,
                "meta": {"schema": schema_name, "table": table_name},
            }
        )

        for col in columns:
            col_name = col.get("name")
            col_key = f"{table_key}.{col_name}"
            col_text = (
                f"字段 {col_key}，类型 {col.get('type')}，"
                f"注释：{col.get('comment') or '无'}，"
                f"{'主键' if col.get('primary_key') else '非主键'}，"
                f"可空：{col.get('nullable')}"
            )
            chunks.append(
                {
                    "id": _point_id(datasource_id, "column", col_key),
                    "kind": "column",
                    "schema": schema_name,
                    "table": table_name,
                    "name": col_key,
                    "content": col_text,
                    "meta": {"schema": schema_name, "table": table_name, "column": col_name},
                }
            )

    return chunks

