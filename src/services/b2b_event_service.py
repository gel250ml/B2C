from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.b2b_event_repository import B2bEventRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class B2bEventService:
    def __init__(self, session: AsyncSession):
        self.repo = B2bEventRepository(session)
        self.session = session