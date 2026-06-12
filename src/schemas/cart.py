from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreateRequest(BaseModel):
    sku_id: UUID
    quantity: int = Field(..., ge=1)


class CartItemQuantityRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CartImageResponse(BaseModel):
    id: UUID | None = None
    url: str | None = None
    alt: str | None = None
    ordering: int = 0
    is_main: bool = False

    model_config = ConfigDict(extra="ignore")


class CartItemResponse(BaseModel):
    sku_id: UUID
    product_id: UUID | None = None
    name: str
    sku_code: str | None = None
    quantity: int
    unit_price: int
    unit_price_at_add: int
    line_total: int
    available_quantity: int
    is_available: bool
    unavailable_reason: str | None = None
    image: CartImageResponse | None = None


class CartResponse(BaseModel):
    id: UUID
    items: list[CartItemResponse]
    items_count: int
    subtotal: int
    is_valid: bool
    updated_at: datetime
