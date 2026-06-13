from enum import Enum
from pydantic import BaseModel, field_validator


class SubscriptionEvent(str, Enum):
    BACK_IN_STOCK = "BACK_IN_STOCK"
    PRICE_DROP = "PRICE_DROP"


class ProductSubscriptionCreateRequest(BaseModel):
    events: list[SubscriptionEvent] = [
        SubscriptionEvent.BACK_IN_STOCK,
        SubscriptionEvent.PRICE_DROP,
    ]

    @field_validator('events')
    @classmethod
    def validate_events_not_empty(cls, v):
        if not v:
            raise ValueError('Events list cannot be empty')
        return v