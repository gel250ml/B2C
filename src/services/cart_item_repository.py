from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import CartItem


class CartItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def mark_unavailable(
        self,
        sku_ids: list[UUID],
        reason: str,
    ) -> None:
        if not sku_ids:
            return

        await self.session.execute(
            update(CartItem)
            .where(CartItem.sku_id.in_(sku_ids))
            .values(unavailable_reason=reason)
        )

    async def mark_unavailable_by_product_id(
        self,
        product_id: UUID,
        reason: str,
    ) -> None:
        await self.session.execute(
            update(CartItem)
            .where(CartItem.product_id == product_id)
            .values(unavailable_reason=reason)
        )
