from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.catalog import CatalogProductCardResponse


class CollectionResponseItem(BaseModel):
    id: UUID
    name: str
    products: list[CatalogProductCardResponse] = Field(default_factory=list)
    description: str | None = None
    cover_image_url: str | None = None
    target_url: str | None = None
    priority: int

    model_config = ConfigDict(extra="ignore")


class CollectionProductsResponse(BaseModel):
    collection_id: UUID
    collection_name: str
    collection_title: str
    items: list[CatalogProductCardResponse]
    unavailable_ids: list[UUID]
    total_products: int
    limit: int
    offset: int
