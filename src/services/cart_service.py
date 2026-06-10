from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.cart_repository import CartRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class CartService:
    def __init__(self, session: AsyncSession):
        self.repo = CartRepository(session)
        self.session = session