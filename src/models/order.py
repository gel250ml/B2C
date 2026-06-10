import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    Enum,
    ForeignKey,
    DateTime,
    Uuid,
    Integer,
    Text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class OrderStatus(str, enum.Enum):
    CREATED = "CREATED"
    PAID = "PAID"
    ASSEMBLING = "ASSEMBLING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    CANCEL_PENDING = "CANCEL_PENDING"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=False, )
    address_id = Column(Uuid(as_uuid=True), ForeignKey("addresses.id"), nullable=False, )
    payment_method_id = Column(Uuid(as_uuid=True), ForeignKey("payment_methods.id"), nullable=False, )
    number = Column(String(50), unique=True, nullable=False, )
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.CREATED, )
    subtotal = Column(Integer, nullable=False)
    delivery_cost = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False)
    comment = Column(Text)
    cancel_reason = Column(Text)
    idempotency_key = Column(Uuid(as_uuid=True), nullable=False, )

    created_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime)
    delivered_at = Column(DateTime)

    buyer = relationship("Buyer", back_populates="orders", )
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", )
    status_history = relationship("OrderStatusHistory", back_populates="order", cascade="all, delete-orphan", )
