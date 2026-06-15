from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import BannerEvent
from src.repositories.banner_repository import BannerRepository
from src.schemas.banner import (
    BannerEventRequestItem,
    BannerEventsResponse,
    BannerResponse,
    BannerResponseItem,
    OpenAPIBannerResponseItem,
)


class BannerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BannerRepository(session)

    async def list_active_banners(self) -> BannerResponse:
        banners = await self.repo.list_active()
        items = [
            BannerResponseItem(
                id=banner.id,
                title=banner.title,
                image_url=banner.image_url,
                link=banner.link,
                priority=banner.priority,
            )
            for banner in banners
        ]
        return BannerResponse(items=items, total_count=len(items))

    async def list_active_openapi_banners(self) -> list[OpenAPIBannerResponseItem]:
        banners = await self.repo.list_active()
        return [
            OpenAPIBannerResponseItem(
                id=banner.id,
                title=banner.title,
                image_url=banner.image_url,
                link=banner.link,
                ordering=banner.priority,
                active_from=banner.start_at,
                active_to=banner.end_at,
            )
            for banner in banners
        ]

    async def record_banner_events(
        self,
        events: list[BannerEventRequestItem],
        user_id: UUID | None = None,
    ) -> BannerEventsResponse:
        if not events:
            raise HTTPException(
                status_code=400,
                detail={"code": "EMPTY_EVENTS", "message": "events must not be empty"},
            )

        requested_banner_ids = {event.banner_id for event in events}
        existing_banner_ids = await self.repo.existing_banner_ids(requested_banner_ids)
        if requested_banner_ids - existing_banner_ids:
            raise HTTPException(
                status_code=400,
                detail={"code": "BANNER_NOT_FOUND", "message": "Banner not found"},
            )

        now = datetime.now(timezone.utc)
        await self.repo.add_events(
            [
                BannerEvent(
                    banner_id=event.banner_id,
                    user_id=user_id,
                    event=event.event,
                    timestamp=event.timestamp or now,
                )
                for event in events
            ]
        )
        await self.session.commit()
        return BannerEventsResponse(accepted_count=len(events))
