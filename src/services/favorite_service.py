from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.favorite_repository import FavoriteRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class FavoriteService:
    def __init__(self, session: AsyncSession):
        self.repo = FavoriteRepository(session)
        self.session = session