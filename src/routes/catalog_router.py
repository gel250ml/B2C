from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.schemas.catalog import ProductCardResponse
from src.services.catalog_service import CatalogService

router = APIRouter(
    prefix="/catalog",
    tags=["Catalog"],
)


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
) -> None:
    return None


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
