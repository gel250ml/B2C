from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.buyer_repository import BuyerRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class BuyerService:
    def __init__(self, session: AsyncSession):
        self.repo = BuyerRepository(session)
        self.session = session