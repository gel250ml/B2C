from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.product_subscription import ProductSubscription
from src.repositories.product_subscription_repository import (
    ProductSubscriptionRepository,
)
from src.core.exceptions import (
    ConflictException,
    NotFoundException,
)
from src.schemas.product_subscription import SubscriptionEvent
from src.services.catalog_service import CatalogService


class ProductSubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ProductSubscriptionRepository(session)
        self.catalog_service = CatalogService(session)

    async def check_product_exists(self, product_id: UUID) -> bool:
        try:
            await self.catalog_service.get_visible_product_payload(product_id)
            return True
        except NotFoundException:
            return False

    async def subscribe(
            self,
            buyer_id: UUID,
            product_id: UUID,
            events: list[SubscriptionEvent],
    ) -> ProductSubscription:
        product_exists = await self.check_product_exists(product_id)
        if not product_exists:
            raise NotFoundException("Product not found")

        existing = await self.repo.get_by_buyer_and_product(
            buyer_id,
            product_id,
        )

        if existing:
            raise ConflictException("Subscription already exists")

        subscription = ProductSubscription(
            buyer_id=buyer_id,
            product_id=product_id,
            back_in_stock=SubscriptionEvent.BACK_IN_STOCK in events,
            price_drop=SubscriptionEvent.PRICE_DROP in events,
        )

        await self.repo.create(subscription)
        await self.session.commit()

        return subscription

    async def unsubscribe(
            self,
            buyer_id: UUID,
            product_id: UUID,
    ) -> None:
        deleted = await self.repo.delete(
            buyer_id,
            product_id,
        )

        if not deleted:
            raise NotFoundException("Subscription not found")

        await self.session.commit()