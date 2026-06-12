import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Uuid,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from src.database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=False, )
    type = Column(String(50), nullable=False, )
    title = Column(String(255), nullable=False, )
    body = Column(Text, nullable=True, )
    payload = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True, )
    is_read = Column(Boolean, nullable=False, default=False, )

    created_at = Column(DateTime, server_default=func.now(), )

    buyer = relationship("Buyer")
