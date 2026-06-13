from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.favorite import Favorite


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_buyer_and_product(
        self,
        buyer_id: UUID,
        product_id: UUID,
    ) -> Favorite | None:
        stmt = select(Favorite).where(
            Favorite.buyer_id == buyer_id,
            Favorite.product_id == product_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_buyer_favorites(
        self,
        buyer_id: UUID,
        limit: int,
        offset: int,
    ) -> list[Favorite]:
        stmt = select(Favorite).where(
            Favorite.buyer_id == buyer_id
        ).order_by(Favorite.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_favorites_count(self, buyer_id: UUID) -> int:
        stmt = select(Favorite).where(Favorite.buyer_id == buyer_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def add(self, favorite: Favorite) -> Favorite:
        self.session.add(favorite)
        await self.session.flush()
        await self.session.refresh(favorite)
        return favorite

    async def delete(self, buyer_id: UUID, product_id: UUID) -> bool:
        stmt = delete(Favorite).where(
            Favorite.buyer_id == buyer_id,
            Favorite.product_id == product_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0