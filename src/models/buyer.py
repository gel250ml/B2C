import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Index,
    Uuid,
    Date
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

from src.database.base import Base


class Buyer(AsyncAttrs, Base):
    __tablename__ = "buyers"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    phone = Column(String(20))
    date_of_birth = Column(Date)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), )

    addresses = relationship("Address", back_populates="buyer", cascade="all, delete-orphan", )
    payment_methods = relationship("PaymentMethod", back_populates="buyer", cascade="all, delete-orphan", )
    orders = relationship("Order", back_populates="buyer", )

    __table_args__ = (Index("idx_buyers_email", "email"),)
