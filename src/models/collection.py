import uuid

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.sql import func

from src.database.base import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    target_url = Column(String(500), nullable=True)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    start_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "ix_collections_active_start_priority",
            "is_active",
            "start_date",
            "priority",
        ),
    )


class CollectionProduct(Base):
    __tablename__ = "collection_products"

    collection_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    product_id = Column(Uuid(as_uuid=True), primary_key=True)
    ordering = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index(
            "ix_collection_products_collection_ordering",
            "collection_id",
            "ordering",
        ),
    )
