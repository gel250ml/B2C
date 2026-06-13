from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def get(self, scope: str, key: UUID) -> IdempotencyKey | None:
        result = await self.session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == scope,
                IdempotencyKey.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def get_active(self, scope: str, key: UUID, now: datetime) -> IdempotencyKey | None:
        result = await self.session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == scope,
                IdempotencyKey.key == key,
                IdempotencyKey.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    def add(self, scope: str, key: UUID, request_hash: str, expires_at: datetime) -> IdempotencyKey:
        item = IdempotencyKey(
            scope=scope,
            key=key,
            request_hash=request_hash,
            expires_at=expires_at,
        )
        self.session.add(item)
        return item
