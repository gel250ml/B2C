from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.schemas.catalog import (
    CatalogFacetsResponse,
    CatalogProductListItemResponse,
    CategoryTreeNodeResponse,
    PaginatedCatalogProductsResponse,
    ProductCardResponse,
)
from src.services.catalog_service import DEFAULT_CATALOG_SORT, CatalogService

router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
) -> None:
    return None


@router.get("/categories/tree", response_model=list[CategoryTreeNodeResponse])
async def get_categories_tree(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> list[CategoryTreeNodeResponse]:
    service = CatalogService(db)
    response.headers["Cache-Control"] = "max-age=3600"
    return await service.get_categories_tree()


@router.get(
    "/products",
    response_model=PaginatedCatalogProductsResponse,
    openapi_extra={
        "parameters": [
            {
                "name": "filter",
                "in": "query",
                "style": "deepObject",
                "explode": True,
                "required": False,
                "schema": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "description": "Динамические фильтры каталога: filter[category_id], filter[brand], filter[price_min], filter[price_max] и т.д.",
            }
        ]
    },
)
async def get_catalog_products(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None),
    sort: str = Query(DEFAULT_CATALOG_SORT),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCatalogProductsResponse:
    if search is not None:
        if len(search) < 3:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_REQUEST", "message": "Search query must be at least 3 characters"},
            )
        if len(search) > 255:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_REQUEST", "message": "Search query must be at most 255 characters"},
            )
    service = CatalogService(db)
    return await service.get_products(
        query_params=request.query_params,
        limit=limit,
        offset=offset,
        q=search,
        sort=sort,
    )


@router.get(
    "/facets",
    response_model=CatalogFacetsResponse,
    openapi_extra={
        "parameters": [
            {
                "name": "filter",
                "in": "query",
                "style": "deepObject",
                "explode": True,
                "required": False,
                "schema": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
                "description": "Текущие фильтры каталога для пересчёта фасетов: filter[category_id], filter[brand], filter[color] и т.д.",
            }
        ]
    },
)
async def get_catalog_facets(
    request: Request,
    sort: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> CatalogFacetsResponse:
    service = CatalogService(db)
    return await service.get_facets(request.query_params, sort=sort)


@router.get(
    "/products/{product_id}/similar",
    response_model=list[CatalogProductListItemResponse],
)
async def get_similar_products(
    product_id: UUID,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[CatalogProductListItemResponse]:
    service = CatalogService(db)
    return await service.get_similar_products(product_id, limit=limit)


@router.get(
    "/products/{product_id}",
    response_model=ProductCardResponse,
)
async def get_product_card(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProductCardResponse:
    service = CatalogService(db)
    return await service.get_product_card(product_id)
