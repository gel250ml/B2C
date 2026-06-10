import uuid
from sqlalchemy import (
    Column,
    Boolean,
    DateTime,
    ForeignKey,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class ProductSubscription(Base):
    __tablename__ = "product_subscriptions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )
    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=False, )
    product_id = Column(Uuid(as_uuid=True), nullable=False, )
    back_in_stock = Column(Boolean, nullable=False, default=True, )
    price_drop = Column(Boolean, nullable=False, default=True, )

    created_at = Column(DateTime, server_default=func.now(), )

    buyer = relationship("Buyer")

    __table_args__ = (
        UniqueConstraint(
            "buyer_id",
            "product_id",
            name="uq_product_subscription",
        ),
    )
