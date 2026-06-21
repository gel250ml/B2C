from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EventProductRef(BaseModel):
    product_id: UUID
    sku_ids: list[UUID] = Field(default_factory=list)
    reason: str | None = None


class EventSkuStock(BaseModel):
    sku_id: UUID
    product_id: UUID | None = None
    quantity: int | None = None
    available_quantity: int | None = None
    reason: str | None = None


class EventPriceChanged(BaseModel):
    sku_id: UUID
    product_id: UUID | None = None
    old_price: int | None = None
    new_price: int | None = None


class B2BEventCreateRequest(BaseModel):
    event_type: Literal[
        "PRODUCT_BLOCKED",
        "PRODUCT_DELETED",
        "SKU_OUT_OF_STOCK",
        "PRICE_CHANGED",
    ]
    idempotency_key: UUID
    occurred_at: datetime
    payload: EventProductRef | EventSkuStock | EventPriceChanged


class B2BEventCreateResponse(BaseModel):
    accepted: bool = True
