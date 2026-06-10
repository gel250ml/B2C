from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.auth_repository import AuthRepository
from src.core.exceptions import ConflictException, NotFoundException, NotOwnerException, ValidationException


class AuthService:
    def __init__(self, session: AsyncSession):
        self.repo = AuthRepository(session)
        self.session = session