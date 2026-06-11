from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CatalogCategoryResponse(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None = None
    level: int = 0
    path: list[str] = []

    model_config = ConfigDict(extra="ignore")


class CatalogImageResponse(BaseModel):
    id: UUID | None = None
    url: str
    alt: str | None = None
    ordering: int = 0
    is_main: bool = False

    model_config = ConfigDict(extra="ignore")


class CatalogSellerResponse(BaseModel):
    id: UUID
    display_name: str

    model_config = ConfigDict(extra="ignore")


class ProductSkuResponse(BaseModel):
    id: UUID
    name: str
    sku_code: str | None = None
    price: int
    old_price: int | None = None
    available_quantity: int
    attributes: dict[str, Any] = {}
    images: list[CatalogImageResponse] = []

    model_config = ConfigDict(extra="ignore")


class ProductCardResponse(BaseModel):
    id: UUID
    name: str
    slug: str | None = None
    category: CatalogCategoryResponse | None = None
    min_price: int
    old_price: int | None = None
    has_stock: bool
    rating: float | int = 0
    reviews_count: int = 0
    images: list[CatalogImageResponse] = []
    seller: CatalogSellerResponse | None = None
    description: str | None = None
    attributes: dict[str, Any] = {}
    skus: list[ProductSkuResponse] = []

    model_config = ConfigDict(extra="ignore")
