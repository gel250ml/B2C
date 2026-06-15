from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Banner, BannerEvent


class BannerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self) -> list[Banner]:
        now = datetime.now(timezone.utc)
        query = (
            select(Banner)
            .where(
                Banner.is_active.is_(True),
                or_(Banner.start_at.is_(None), Banner.start_at <= now),
                or_(Banner.end_at.is_(None), Banner.end_at >= now),
            )
            .order_by(Banner.priority.asc(), Banner.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def existing_banner_ids(self, banner_ids: set[UUID]) -> set[UUID]:
        if not banner_ids:
            return set()
        result = await self.session.execute(
            select(Banner.id).where(Banner.id.in_(banner_ids))
        )
        return set(result.scalars().all())

    async def add_events(self, events: list[BannerEvent]) -> None:
        self.session.add_all(events)
        await self.session.flush()
