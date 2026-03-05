from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    INSTALL = "install"
    UNINSTALL = "uninstall"


class EventIn(BaseModel):
    timestamp: datetime
    package: str = Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9._-]+$")
    type: EventType


class EventSummary(BaseModel):
    count: int = 0
    last: datetime | None = None
