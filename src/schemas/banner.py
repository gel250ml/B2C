from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class BannerResponseItem(BaseModel):
    id: UUID
    title: str
    image_url: str
    link: str
    priority: int


class BannerResponse(BaseModel):
    items: list[BannerResponseItem]
    total_count: int


class OpenAPIBannerResponseItem(BaseModel):
    id: UUID
    title: str | None = None
    image_url: str
    link: str
    ordering: int | None = None
    active_from: datetime | None = None
    active_to: datetime | None = None


class BannerEventRequestItem(BaseModel):
    banner_id: UUID
    event: Literal["impression", "click"]
    timestamp: datetime | None = None


class BannerEventsRequest(BaseModel):
    events: list[BannerEventRequestItem] = Field(default_factory=list)


class BannerEventsResponse(BaseModel):
    accepted_count: int
