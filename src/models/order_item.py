import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Uuid,
    Text,
    Integer,
)
from sqlalchemy.orm import relationship

from src.database.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    order_id = Column(Uuid(as_uuid=True), ForeignKey("orders.id"), nullable=False, )
    product_id = Column(Uuid(as_uuid=True), nullable=False, )
    sku_id = Column(Uuid(as_uuid=True), nullable=False, )
    name = Column(String(500), nullable=False, )
    product_title = Column(String(500), nullable=True, )
    sku_name = Column(String(500), nullable=True, )
    sku_code = Column(String(100), )
    quantity = Column(Integer, nullable=False, )
    unit_price = Column(Integer, nullable=False, )
    line_total = Column(Integer, nullable=False, )
    image_url = Column(Text)

    order = relationship("Order", back_populates="items", )
