from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_current_buyer_id, get_db
from src.schemas.product_subscription import ProductSubscriptionCreateRequest
from src.services.product_subscription_service import ProductSubscriptionService

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)


@router.post(
    "/{product_id}/subscribe",
    status_code=status.HTTP_201_CREATED,
)
async def subscribe_to_product(
    product_id: UUID,
    payload: ProductSubscriptionCreateRequest,
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = ProductSubscriptionService(db)
    subscription = await service.subscribe(
        buyer_id=buyer_id,
        product_id=product_id,
        events=payload.events,
    )

    notify_on: list[str] = []
    if subscription.back_in_stock:
        notify_on.append("BACK_IN_STOCK")
    if subscription.price_drop:
        notify_on.append("PRICE_DROP")

    return {
        "product_id": str(product_id),
        "notify_on": notify_on,
    }


@router.delete(
    "/{product_id}/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def unsubscribe_from_product(
    product_id: UUID,
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = ProductSubscriptionService(db)
    await service.unsubscribe(
        buyer_id=buyer_id,
        product_id=product_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
