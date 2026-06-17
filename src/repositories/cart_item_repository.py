from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import CartItem


class CartItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def mark_unavailable(
        self,
        sku_ids: list,
        reason: str,
    ):
        await self.session.execute(
            update(CartItem)
            .where(CartItem.sku_id.in_(sku_ids))
            .values(unavailable_reason=reason)
        )