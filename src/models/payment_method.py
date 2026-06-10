import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Enum,
    ForeignKey,
    DateTime,
    Uuid,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class PaymentMethodType(str, enum.Enum):
    CARD = "CARD"
    SBP = "SBP"
    WALLET = "WALLET"


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=False, )
    type = Column(Enum(PaymentMethodType), nullable=False, )
    card_last4 = Column(String(4))
    card_brand = Column(String(50))
    is_default = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())

    buyer = relationship("Buyer", back_populates="payment_methods", )
