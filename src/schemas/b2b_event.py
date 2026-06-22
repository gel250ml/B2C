from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventProductRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    # Поле sku_ids есть во входящих событиях команды B2B и нужно для эффективного
    # batch update корзины. Если список не пришёл, сервис fallback-ом обновит по product_id.
    sku_ids: list[UUID] = Field(default_factory=list)
    reason: str | None = None


class EventSkuStock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: UUID
    # По OpenAPI эти поля обязательны для stock-событий. quantity оставляем
    # необязательным для совместимости со старым канон-flow/тестами.
    product_id: UUID
    available_quantity: int
    quantity: int | None = None
    reason: str | None = None


class EventPriceChanged(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: UUID
    product_id: UUID | None = None
    old_price: int | None = None
    new_price: int | None = None


class B2BEventCreateRequest(BaseModel):
    event_type: Literal[
        "PRODUCT_BLOCKED",
        "PRODUCT_HARD_BLOCKED",
        "PRODUCT_DELETED",
        "SKU_OUT_OF_STOCK",
        "SKU_BACK_IN_STOCK",
        "PRICE_CHANGED",
    ]
    idempotency_key: UUID
    occurred_at: datetime
    payload: EventProductRef | EventSkuStock | EventPriceChanged


class B2BEventCreateResponse(BaseModel):
    accepted: bool = True
