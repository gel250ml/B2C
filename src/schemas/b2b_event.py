from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel


class B2BEventCreateRequest(BaseModel):
    idempotency_key: UUID
    event: Literal[
        "PRODUCT_BLOCKED",
        "PRODUCT_DELETED",
        "SKU_OUT_OF_STOCK",
    ]
    product_id: UUID
    sku_ids: list[UUID]
    reason: str | None = None
    date: datetime


class B2BEventCreateResponse(BaseModel):
    accepted: bool = True
