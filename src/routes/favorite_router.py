from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.favorite_service import FavoriteService

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)

@router.get(
    ""
)
async def get_favorites(
        db: AsyncSession = Depends(get_db)
) -> None:
    return None
    service = FavoriteService(db)
    return await service.get_favorites()