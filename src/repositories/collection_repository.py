from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Collection, CollectionProduct


class CollectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self, *, limit: int, offset: int) -> list[Collection]:
        query = (
            select(Collection)
            .where(*self._active_predicates())
            .order_by(Collection.priority.asc(), Collection.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        query = select(func.count(Collection.id)).where(*self._active_predicates())
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    async def get_by_id(self, collection_id: UUID) -> Collection | None:
        return await self.session.get(Collection, collection_id)

    async def list_product_ids(self, collection_id: UUID, *, limit: int, offset: int) -> list[UUID]:
        query = (
            select(CollectionProduct.product_id)
            .where(CollectionProduct.collection_id == collection_id)
            .order_by(CollectionProduct.ordering.asc(), CollectionProduct.product_id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_products(self, collection_id: UUID) -> int:
        query = select(func.count(CollectionProduct.product_id)).where(CollectionProduct.collection_id == collection_id)
        result = await self.session.execute(query)
        return int(result.scalar_one() or 0)

    @staticmethod
    def _active_predicates():
        today = datetime.now(timezone.utc).date()
        return (
            Collection.is_active.is_(True),
            or_(Collection.start_date.is_(None), Collection.start_date <= today),
        )
