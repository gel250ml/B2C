from sqlalchemy import (
    Column,
    ForeignKey,
    DateTime,
    Uuid,
)
from sqlalchemy.sql import func

from src.database.base import Base


class Favorite(Base):
    __tablename__ = "favorites"

    buyer_id = Column(Uuid(as_uuid=True), ForeignKey("buyers.id"), primary_key=True, )
    product_id = Column(Uuid(as_uuid=True), primary_key=True, )

    created_at = Column(DateTime, server_default=func.now(), )
