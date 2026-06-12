from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_current_buyer_id, get_db
from src.schemas.order import CancelOrderRequest, OrderResponse
from src.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.get("/")
async def get_all_orders(db: AsyncSession = Depends(get_db)):
    return None


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: UUID,
    payload: CancelOrderRequest | None = Body(default=None),
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    return await service.cancel_order(
        order_id=order_id,
        buyer_id=buyer_id,
        reason=payload.reason if payload else None,
    )
