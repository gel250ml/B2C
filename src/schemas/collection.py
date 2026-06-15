from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.schemas.catalog import CatalogProductCardResponse


class CollectionResponseItem(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    cover_image_url: str | None = None
    target_url: str | None = None
    priority: int

    model_config = ConfigDict(extra="ignore")


class CollectionsMetadataResponse(BaseModel):
    total_count: int
    limit: int
    offset: int


class CollectionsResponse(BaseModel):
    collections: list[CollectionResponseItem]
    metadata: CollectionsMetadataResponse


class CollectionProductsResponse(BaseModel):
    collection_id: UUID
    collection_title: str
    items: list[CatalogProductCardResponse]
    unavailable_ids: list[UUID]
    total_products: int
    limit: int
    offset: int
