from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import *


class FavoriteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
