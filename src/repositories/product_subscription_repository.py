from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product_subscription import ProductSubscription


class ProductSubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_buyer_and_product(
        self,
        buyer_id: UUID,
        product_id: UUID,
    ) -> ProductSubscription | None:
        stmt = select(ProductSubscription).where(
            ProductSubscription.buyer_id == buyer_id,
            ProductSubscription.product_id == product_id,
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, subscription: ProductSubscription):
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def delete(
        self,
        buyer_id: UUID,
        product_id: UUID,
    ) -> bool:
        stmt = delete(ProductSubscription).where(
            ProductSubscription.buyer_id == buyer_id,
            ProductSubscription.product_id == product_id,
        )

        result = await self.session.execute(stmt)
        return result.rowcount > 0