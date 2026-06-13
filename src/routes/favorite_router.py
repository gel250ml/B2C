from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db, get_current_buyer_id
from src.services.favorite_service import FavoriteService
from src.schemas.catalog import PaginatedCatalogProductsResponse

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
async def get_favorites(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
) -> PaginatedCatalogProductsResponse:
    service = FavoriteService(db)
    return await service.get_favorites(buyer_id, limit, offset)


@router.put(
    "/{product_id}",
    status_code=status.HTTP_200_OK,
)
async def add_to_favorites(
    product_id: UUID,
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = FavoriteService(db)
    await service.add_favorite(buyer_id, product_id)
    return Response(status_code=status.HTTP_200_OK)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_from_favorites(
    product_id: UUID,
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = FavoriteService(db)
    await service.remove_favorite(buyer_id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)