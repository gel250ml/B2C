from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.address_service import AddressService

router = APIRouter(
    prefix="/buyers/me/addresses",
    tags=["/buyers/me/addresses"],
)

@router.get(
    ""
)
async def get_addresses(
        db: AsyncSession = Depends(get_db)
) -> None:
    return None
    service = AuthService(db)
    return await service.get_addresses()