from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

DataSourceType = Literal["postgresql", "mysql", "mariadb", "clickhouse", "sqlite"]


class DatasourceCreate(BaseModel):
    name: str
    type: DataSourceType = "postgresql"
    host: str = "127.0.0.1"
    port: int = 5432
    database: str
    username: str
    password: str
    default_schema: str | None = None
    extra_params: dict[str, Any] | None = None


class DatasourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    host: str
    port: int
    database: str
    username: str
    default_schema: str | None


class TestResult(BaseModel):
    ok: bool
    message: str


class AnalyzeRequest(BaseModel):
    question: str

