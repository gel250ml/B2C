import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    order_id = Column(Uuid(as_uuid=True), ForeignKey("orders.id"), nullable=False, )
    status = Column(String(50), nullable=False, )
    reason = Column(Text, nullable=True, )

    changed_at = Column(DateTime, server_default=func.now(), )

    order = relationship("Order", back_populates="status_history", )
