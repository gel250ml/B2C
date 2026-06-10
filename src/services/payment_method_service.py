from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.payment_method_repository import PaymentMethodRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class PaymentMethodService:
    def __init__(self, session: AsyncSession):
        self.repo = PaymentMethodRepository(session)
        self.session = session