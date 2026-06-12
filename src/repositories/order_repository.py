from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Order, OrderStatus, OrderStatusHistory


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id_and_buyer(self, order_id: UUID, buyer_id: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .where(Order.id == order_id, Order.buyer_id == buyer_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
                selectinload(Order.address),
                selectinload(Order.payment_method),
            )
        )
        return result.scalar_one_or_none()

    async def get_cancel_pending_orders(self, limit: int = 100) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.status == OrderStatus.CANCEL_PENDING)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
                selectinload(Order.address),
                selectinload(Order.payment_method),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    def add_status_history(
        self,
        order: Order,
        status: OrderStatus,
        reason: str | None = None,
    ) -> OrderStatusHistory:
        history_item = OrderStatusHistory(
            order_id=order.id,
            status=status.value,
            reason=reason,
            changed_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self.session.add(history_item)
        order.status_history.append(history_item)
        return history_item
