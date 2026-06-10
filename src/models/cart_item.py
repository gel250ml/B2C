import uuid
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    Uuid,
)
from sqlalchemy.orm import relationship

from src.database.base import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    cart_id = Column(Uuid(as_uuid=True), ForeignKey("carts.id"), nullable=False, )
    product_id = Column(Uuid(as_uuid=True), nullable=False, )
    sku_id = Column(Uuid(as_uuid=True), nullable=False, )
    quantity = Column(Integer, nullable=False, )
    unit_price_at_add = Column(Integer, nullable=False, )

    cart = relationship("Cart", back_populates="items", )
