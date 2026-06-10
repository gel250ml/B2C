from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.order_repository import OrderRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class OrderService:
    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.session = session