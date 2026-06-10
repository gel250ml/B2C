from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.catalog_service import CatalogService

router = APIRouter(
    prefix="/catalog",
    tags=["/catalog"],
)

@router.get(
    "/categories"
)
async def get_categories(
        db: AsyncSession = Depends(get_db)
) -> None:
    return None
    service = CatalogService(db)
    return service.get_categories()