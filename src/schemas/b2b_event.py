from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class B2BEventCreateRequest(BaseModel):
    event_type: str
    idempotency_key: UUID
    payload: dict[str, Any]
    occurred_at: datetime

    model_config = ConfigDict(extra="ignore")


class B2BEventCreateResponse(BaseModel):
    ok: bool = True
    processed: bool = False
