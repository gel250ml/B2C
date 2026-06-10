import uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=True, )
    session_id = Column(Uuid(as_uuid=True), nullable=True, )

    created_at = Column(DateTime, server_default=func.now(), )
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), )

    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan", )
