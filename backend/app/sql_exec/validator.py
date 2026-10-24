import sqlglot
from sqlglot import exp

DIALECTS = {
    "postgresql": "postgres",
    "mysql": "mysql",
    "mariadb": "mysql",
    "clickhouse": "clickhouse",
    "sqlite": "sqlite",
}


class UnsafeSQL(ValueError):
    pass


def validate_read_only(sql: str, db_type: str = "postgresql") -> None:
    dialect = DIALECTS.get(db_type, "postgres")
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as exc:  # noqa: BLE001
        raise UnsafeSQL(f"SQL 解析失败: {exc}") from exc
    if not statements:
        raise UnsafeSQL("空语句")
    for stmt in statements:
        if isinstance(stmt, (exp.Select, exp.Union)):
            continue
        raise UnsafeSQL(f"仅允许只读 SELECT，不允许: {type(stmt).__name__}")

