import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Uuid,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, )

    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), nullable=False, )
    token_hash = Column(String(255), nullable=False, )

    expires_at = Column(DateTime, nullable=False, )
    revoked_at = Column(DateTime, nullable=True, )
    created_at = Column(DateTime, server_default=func.now(), )

    buyer = relationship("Buyer")

    __table_args__ = (
        Index("idx_refresh_tokens_buyer_id", "buyer_id"),
        Index("idx_refresh_tokens_token_hash", "token_hash"),
    )
