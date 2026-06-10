from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.buyer_service import BuyerService

router = APIRouter(
    prefix="/buyers/me",
    tags=["buyers/me"],
)

@router.get(
    ""
)
async def get_me(
        db: AsyncSession = Depends(get_db)
) -> None:
    return None
    service = BuyerService(db)
    return await service.get_me()
