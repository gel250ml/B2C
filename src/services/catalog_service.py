from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.catalog_repository import CatalogRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.repo = CatalogRepository(session)
        self.session = session