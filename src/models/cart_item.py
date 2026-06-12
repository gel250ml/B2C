import uuid
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Uuid,
    DateTime,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    cart_id = Column(Uuid(as_uuid=True), ForeignKey("carts.id"), nullable=False, )
    product_id = Column(Uuid(as_uuid=True), nullable=True, )
    sku_id = Column(Uuid(as_uuid=True), nullable=False, )
    quantity = Column(Integer, nullable=False, )
    unit_price_at_add = Column(Integer, nullable=False, default=0, )
    created_at = Column(DateTime, server_default=func.now(), )
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), )

    cart = relationship("Cart", back_populates="items", )
