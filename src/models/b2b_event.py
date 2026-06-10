import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base


class B2BEvent(Base):
    __tablename__ = "b2b_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    event_type = Column(String(50), nullable=False, )
    idempotency_key = Column(Uuid(as_uuid=True), nullable=False, )
    payload = Column(JSONB, nullable=False, )
    occurred_at = Column(DateTime, nullable=False, )
    processed = Column(Boolean, nullable=False, default=False, )

    created_at = Column(DateTime, server_default=func.now(), )

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_b2b_event_idempotency_key",
        ),
    )
