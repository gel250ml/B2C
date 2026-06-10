import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    scope = Column(String(50), nullable=False, )
    key = Column(Uuid(as_uuid=True), nullable=False, unique=True, )
    request_hash = Column(String(64), nullable=False, )
    response = Column(JSONB, nullable=True, )

    expires_at = Column(DateTime, nullable=False, )
    created_at = Column(DateTime, server_default=func.now(), )
