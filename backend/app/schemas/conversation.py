from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    datasource_id: int | None = None
    title: str | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    datasource_id: int | None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    meta: dict[str, Any] | None
    created_at: datetime


class QueryRequest(BaseModel):
    question: str

