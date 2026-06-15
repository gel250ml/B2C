from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.b2b_event_repository import B2bEventRepository
from src.schemas.b2b_event import B2BEventCreateRequest, B2BEventCreateResponse


class B2bEventService:
    def __init__(self, session: AsyncSession):
        self.repo = B2bEventRepository(session)
        self.session = session

    async def create_event(self, payload: B2BEventCreateRequest) -> B2BEventCreateResponse:
        existing = await self.repo.get_by_idempotency_key(payload.idempotency_key)
        if existing is not None:
            return B2BEventCreateResponse(ok=True, processed=bool(existing.processed))

        event = await self.repo.create(payload)
        await self.session.commit()
        return B2BEventCreateResponse(ok=True, processed=bool(event.processed))
