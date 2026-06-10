from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.cart_service import CartService

router = APIRouter(
    prefix="/cart",
    tags=["/cart"],
)


@router.get(
    ""
)
async def get_cart(
    db: AsyncSession = Depends(get_db),
) -> None:
    return None
    service = CartService(db)
    return await service.get_cart()