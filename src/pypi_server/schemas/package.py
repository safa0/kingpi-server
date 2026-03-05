from typing import Any

from pydantic import BaseModel


class PackageResponse(BaseModel):
    name: str
    info: dict[str, Any] = {}
    releases: dict[str, Any] = {}
    events: dict[str, Any] = {}
