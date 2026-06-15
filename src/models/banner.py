import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.sql import func

from src.database.base import Base


class Banner(Base):
    __tablename__ = "banners"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    image_url = Column(String(500), nullable=False)
    link = Column(String(500), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index(
            "ix_banners_active_schedule_priority",
            "is_active",
            "start_at",
            "end_at",
            "priority",
        ),
    )


class BannerEvent(Base):
    __tablename__ = "banner_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    banner_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("banners.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Uuid(as_uuid=True), nullable=True)
    event = Column(String(20), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("event IN ('impression', 'click')", name="ck_banner_events_event"),
        Index("ix_banner_events_banner_id", "banner_id"),
        Index("ix_banner_events_timestamp", "timestamp"),
    )
