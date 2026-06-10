from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.notification_repository import NotificationRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.repo = NotificationRepository(session)
        self.session = session