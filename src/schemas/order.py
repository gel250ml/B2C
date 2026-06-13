from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.order import OrderStatus
from src.models.payment_method import PaymentMethodType




class CheckoutItemRequest(BaseModel):
    sku_id: UUID
    quantity: int
    unit_price: int | None = None


class CreateOrderRequest(BaseModel):
    address_id: UUID | None = None
    payment_method_id: UUID | None = None
    comment: str | None = None
    items_snapshot: list[CheckoutItemRequest] | None = None

    idempotency_key: UUID | None = None
    items: list[CheckoutItemRequest] | None = None
    delivery_address: str | None = None

    def checkout_items(self) -> list[CheckoutItemRequest]:
        if self.items_snapshot is not None:
            return self.items_snapshot
        return self.items or []


class CancelOrderRequest(BaseModel):
    reason: str | None = None


class OrderStatusHistoryResponse(BaseModel):
    status: str
    changed_at: datetime
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderItemResponse(BaseModel):
    sku_id: UUID
    product_id: UUID
    name: str
    sku_code: str | None = None
    quantity: int
    unit_price: int
    line_total: int
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrderAddressResponse(BaseModel):
    country: str
    region: str | None = None
    city: str
    street: str
    building: str
    apartment: str | None = None
    postal_code: str | None = None
    recipient_name: str | None = None
    recipient_phone: str | None = None
    is_default: bool = False
    comment: str | None = None
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderPaymentMethodResponse(BaseModel):
    type: PaymentMethodType
    card_last4: str | None = None
    card_brand: str | None = None
    is_default: bool = False
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderResponse(BaseModel):
    id: UUID
    number: str
    buyer_id: UUID
    status: OrderStatus
    status_history: list[OrderStatusHistoryResponse] = []
    items: list[OrderItemResponse] = []
    subtotal: int
    delivery_cost: int
    total: int
    address: OrderAddressResponse | None = None
    payment_method: OrderPaymentMethodResponse | None = None
    comment: str | None = None
    cancel_reason: str | None = None
    created_at: datetime
    paid_at: datetime | None = None
    delivered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
