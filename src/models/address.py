import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs

from src.database.base import Base


class Address(AsyncAttrs, Base):
    __tablename__ = "addresses"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=False, )
    country = Column(String(100), nullable=False)
    region = Column(String(200))
    city = Column(String(200), nullable=False)
    street = Column(String(200), nullable=False)
    building = Column(String(50), nullable=False)
    apartment = Column(String(50))
    postal_code = Column(String(20))
    recipient_name = Column(String(200))
    recipient_phone = Column(String(20))
    comment = Column(String(500))
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), )

    buyer = relationship("Buyer", back_populates="addresses", )
