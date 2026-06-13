from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.schemas.catalog import (
    BreadcrumbsResponse,
    CategoryDetailResponse,
)
from src.services.catalog_service import CatalogService

router = APIRouter(tags=["Catalog"])


@router.get("/categories/{category_id}", response_model=CategoryDetailResponse)
async def get_category_detail(
    category_id: UUID,
    include_product_count: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> CategoryDetailResponse:
    service = CatalogService(db)
    return await service.get_category_detail(
        category_id=category_id,
        include_product_count=include_product_count,
    )


@router.get("/breadcrumbs", response_model=BreadcrumbsResponse)
async def get_breadcrumbs(
    category_id: UUID | None = Query(None),
    product_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> BreadcrumbsResponse:
    service = CatalogService(db)
    return await service.get_breadcrumbs(category_id=category_id, product_id=product_id)
