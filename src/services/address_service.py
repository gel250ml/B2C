from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.address_repository import AddressRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class AddressService:
    def __init__(self, session: AsyncSession):
        self.repo = AddressRepository(session)
        self.session = session