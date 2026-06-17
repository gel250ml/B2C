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


class CategoryTreeNodeResponse(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None = None
    level: int = 0
    path: list[str] = []
    children: list["CategoryTreeNodeResponse"] = []

    model_config = ConfigDict(extra="ignore")


class CategoryTreeResponse(BaseModel):
    items: list[CategoryTreeNodeResponse]

    model_config = ConfigDict(extra="ignore")


class CategoryParentResponse(BaseModel):
    id: UUID
    name: str
    slug: str | None = None

    model_config = ConfigDict(extra="ignore")


class CategorySeoResponse(BaseModel):
    title: str | None = None
    description: str | None = None
    keywords: list[str] = []

    model_config = ConfigDict(extra="ignore")


class CategoryDetailResponse(BaseModel):
    id: UUID
    name: str
    slug: str | None = None
    description: str | None = None
    parent: CategoryParentResponse | None = None
    product_count: int | None = None
    seo: CategorySeoResponse | dict[str, Any] | None = None
    meta_tags: dict[str, Any] = {}
    image_url: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    model_config = ConfigDict(extra="ignore")


class BreadcrumbItemResponse(BaseModel):
    id: UUID
    slug: str | None = None
    name: str
    url: str
    level: int
    is_current: bool

    model_config = ConfigDict(extra="ignore")


class BreadcrumbsMetaResponse(BaseModel):
    resolved_via: str
    category_id: UUID
    product_id: UUID | None = None

    model_config = ConfigDict(extra="ignore")


class BreadcrumbsResponse(BaseModel):
    data: list[BreadcrumbItemResponse]
    meta: BreadcrumbsMetaResponse

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
    description: str = ""
    attributes: dict[str, Any] = {}
    skus: list[ProductSkuResponse] = []

    model_config = ConfigDict(extra="ignore")


class CatalogProductListItemResponse(BaseModel):
    id: UUID
    name: str
    slug: str | None = None
    category: CatalogCategoryResponse | None = None
    min_price: int
    old_price: int | None = None
    has_stock: bool
    rating: float | int | None = None
    reviews_count: int = 0
    images: list[CatalogImageResponse] = []
    seller: CatalogSellerResponse | None = None

    model_config = ConfigDict(extra="ignore")


class CatalogProductCardResponse(BaseModel):
    id: UUID
    name: str
    min_price: int
    has_stock: bool
    images: list[CatalogImageResponse] = []

    model_config = ConfigDict(extra="ignore")


class PaginatedCatalogProductsResponse(BaseModel):
    items: list[CatalogProductListItemResponse]
    total_count: int
    limit: int
    offset: int

    model_config = ConfigDict(extra="ignore")


class FacetValueResponse(BaseModel):
    value: str
    count: int

    model_config = ConfigDict(extra="ignore")


class CatalogFacetResponse(BaseModel):
    name: str
    values: list[FacetValueResponse]

    model_config = ConfigDict(extra="ignore")


class CatalogFacetsResponse(BaseModel):
    category_id: UUID | None = None
    facets: list[CatalogFacetResponse]

    model_config = ConfigDict(extra="ignore")
