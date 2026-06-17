from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import B2BEvent
from src.schemas.b2b_event import B2BEventCreateRequest


class B2bEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_idempotency_key(self, idempotency_key: UUID) -> B2BEvent | None:
        result = await self.session.execute(
            select(B2BEvent).where(B2BEvent.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def create(self, payload: B2BEventCreateRequest) -> B2BEvent:
        event = B2BEvent(
            event_type=payload.event,
            idempotency_key=payload.idempotency_key,
            payload={
                "product_id": str(payload.product_id),
                "sku_ids": [
                    str(x)
                    for x in payload.sku_ids
                ],
                "reason": payload.reason,
            },
            occurred_at=payload.date,
            processed=False,
        )
        self.session.add(event)
        await self.session.flush()
        return event
