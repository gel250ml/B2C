from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Address, Buyer, Order, OrderStatus, OrderStatusHistory, PaymentMethod


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


    async def get_by_idempotency_key(self, idempotency_key: UUID) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .where(Order.idempotency_key == idempotency_key)
            .options(
                selectinload(Order.items),
                selectinload(Order.status_history),
                selectinload(Order.address),
                selectinload(Order.payment_method),
            )
        )
        return result.scalar_one_or_none()

    async def get_address_for_buyer(self, address_id: UUID, buyer_id: UUID) -> Address | None:
        result = await self.session.execute(
            select(Address).where(Address.id == address_id, Address.buyer_id == buyer_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_method_for_buyer(self, payment_method_id: UUID, buyer_id: UUID) -> PaymentMethod | None:
        result = await self.session.execute(
            select(PaymentMethod).where(
                PaymentMethod.id == payment_method_id,
                PaymentMethod.buyer_id == buyer_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_buyer(self, buyer_id: UUID) -> Buyer | None:
        result = await self.session.execute(select(Buyer).where(Buyer.id == buyer_id))
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
