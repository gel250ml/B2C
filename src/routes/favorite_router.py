from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_db, get_current_buyer_id
from src.schemas.product_subscription import (
    ProductSubscriptionCreateRequest, SubscriptionEvent,
)
from src.services.product_subscription_service import ProductSubscriptionService
from src.core.exceptions import ConflictException, NotFoundException

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)


@router.post(
    "/{product_id}/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def subscribe_to_product(
        product_id: UUID,
        payload: ProductSubscriptionCreateRequest | None = None,
        buyer_id: UUID = Depends(get_current_buyer_id),
        db: AsyncSession = Depends(get_db),
):
    service = ProductSubscriptionService(db)

    events = (
        payload.events
        if payload and payload.events
        else [
            SubscriptionEvent.BACK_IN_STOCK,
            SubscriptionEvent.PRICE_DROP,
        ]
    )

    product_exists = await service.check_product_exists(product_id)
    if not product_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    try:
        await service.subscribe(
            buyer_id=buyer_id,
            product_id=product_id,
            events=events,
        )
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{product_id}/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unsubscribe_from_product(
        product_id: UUID,
        buyer_id: UUID = Depends(get_current_buyer_id),
        db: AsyncSession = Depends(get_db),
):
    service = ProductSubscriptionService(db)

    try:
        await service.unsubscribe(
            buyer_id=buyer_id,
            product_id=product_id,
        )
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)