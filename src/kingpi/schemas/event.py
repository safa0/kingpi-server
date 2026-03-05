"""
Pydantic schemas for event request/response validation.

WHY separate schemas from domain models?
-----------------------------------------
Schemas define the *API contract* — what the client sends and receives.
Domain models (in `models/`) represent internal business objects. Keeping
them separate means:

1. **API stability** — you can refactor internals without breaking the API.
2. **Validation at the boundary** — Pydantic validates and coerces incoming
   JSON automatically; invalid requests get a 422 response with details.
3. **Documentation** — FastAPI uses these schemas to generate OpenAPI docs,
   so each field's type and constraints appear in /docs.

Pydantic patterns used here:
- `BaseModel` — the foundation for all Pydantic schemas.
- `Field(...)` — adds validation constraints (min_length, max_length).
- `StrEnum` — Python 3.11+ enum whose members are strings; Pydantic serializes
  them as their string values in JSON automatically.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    """Allowed event types — using StrEnum so values serialize as plain strings."""

    INSTALL = "install"
    UNINSTALL = "uninstall"


class EventIn(BaseModel):
    """Schema for incoming event payloads (request body).

    FastAPI automatically validates request JSON against this schema.
    If validation fails, the client receives a 422 Unprocessable Entity
    response with details about which fields failed and why.
    """

    timestamp: datetime
    package: str = Field(min_length=1, max_length=200)
    type: EventType


class EventSummary(BaseModel):
    """Schema for event summary responses (e.g., aggregated stats)."""

    count: int = 0
    last: datetime | None = None
