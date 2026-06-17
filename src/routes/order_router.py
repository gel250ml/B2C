from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Response, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_current_buyer_id, get_db, verify_b2b_service_key
from src.models import OrderStatus
from src.schemas.order import CancelOrderRequest, CreateOrderRequest, OrderResponse, OrderStatusUpdateRequest, \
    PaginatedOrdersResponse
from src.services.order_service import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


@router.get("", response_model=PaginatedOrdersResponse)
async def get_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: OrderStatus | None = Query(None),
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)

    return await service.get_orders(
        buyer_id=buyer_id,
        limit=limit,
        offset=offset,
        status=status,
    )

@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
async def get_order(
    order_id: UUID,
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)

    return await service.get_order(
        order_id=order_id,
        buyer_id=buyer_id,
    )

@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    payload: CreateOrderRequest,
    response: Response,
    idempotency_key_header: UUID | None = Header(None, alias="Idempotency-Key"),
    buyer_id: UUID = Depends(get_current_buyer_id),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    order_response, status_code = await service.create_order(
        buyer_id=buyer_id,
        payload=payload,
        idempotency_key_header=idempotency_key_header,
    )
    response.status_code = status_code
    return order_response


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

@router.post(
    "/{order_id}/status",
    response_model=OrderResponse,
    include_in_schema=False,
)
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdateRequest,
    _: None = Depends(verify_b2b_service_key),
    db: AsyncSession = Depends(get_db),
):
    service = OrderService(db)
    return await service.transition_order_status(
        order_id=order_id,
        new_status=payload.status,
    )

