import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Order, OrderStatus
from src.repositories.order_repository import OrderRepository
from src.schemas.order import OrderResponse
from src.services.b2b_inventory_client import B2BInventoryClient, B2BUnavailableError

logger = logging.getLogger(__name__)


class OrderService:
    ALLOWED_CANCEL_STATUSES = {OrderStatus.CREATED, OrderStatus.PAID}

    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.session = session
        self.b2b_inventory_client = B2BInventoryClient()

    async def cancel_order(
        self,
        order_id: UUID,
        buyer_id: UUID,
        reason: str | None = None,
    ) -> OrderResponse:
        order = await self.repo.get_by_id_and_buyer(order_id, buyer_id)
        if order is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "ORDER_NOT_FOUND", "message": "Заказ не найден"},
            )

        if order.status not in self.ALLOWED_CANCEL_STATUSES:
            current_status = self._status_value(order.status)
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CANCEL_NOT_ALLOWED",
                    "message": f"Отмена невозможна: заказ в статусе {current_status}",
                    "current_status": current_status,
                },
            )

        order.cancel_reason = reason
        await self._set_status(order, OrderStatus.CANCEL_PENDING, reason)

        try:
            await self._unreserve_order(order)
        except B2BUnavailableError:
            logger.exception("Unreserve failed for order %s. Order left in CANCEL_PENDING", order.id)
            return self._to_response(order)

        await self._set_status(order, OrderStatus.CANCELLED, reason)
        return self._to_response(order)

    async def retry_pending_cancellations(self, limit: int = 100) -> int:
        orders = await self.repo.get_cancel_pending_orders(limit)
        cancelled_count = 0

        for order in orders:
            try:
                await self._unreserve_order(order)
            except B2BUnavailableError:
                logger.exception("Retry unreserve failed for order %s", order.id)
                continue

            await self._set_status(order, OrderStatus.CANCELLED, order.cancel_reason)
            cancelled_count += 1

        return cancelled_count

    async def _unreserve_order(self, order: Order) -> None:
        await self.b2b_inventory_client.unreserve(
            order_id=order.id,
            items=[
                {
                    "sku_id": str(item.sku_id),
                    "quantity": item.quantity,
                }
                for item in order.items
            ],
        )

    async def _set_status(
        self,
        order: Order,
        status: OrderStatus,
        reason: str | None = None,
    ) -> None:
        order.status = status
        self.repo.add_status_history(order, status, reason)
        await self.session.commit()

    @staticmethod
    def _status_value(status: OrderStatus | str) -> str:
        return status.value if isinstance(status, OrderStatus) else str(status)

    @staticmethod
    def _to_response(order: Order) -> OrderResponse:
        return OrderResponse.model_validate(order)
