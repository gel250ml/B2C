from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db
from src.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["/orders"],
)

@router.get(
    "/"
)
async def get_all_orders(
        db: AsyncSession = Depends(get_db)
):
    return None
    service = OrderService(db)
    return await service.get_all_orders()