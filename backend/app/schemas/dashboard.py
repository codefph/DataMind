from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DashboardCreate(BaseModel):
    title: str
    layout: dict[str, Any]


class DashboardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    layout: dict[str, Any] | None
    created_at: datetime

