"""diagnosis_sessions 和 chat_messages ORM 表模型（Data Mapper 模式）。"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from Backend.Infrastructure.persistence.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionModel(Base):
    __tablename__ = "diagnosis_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(30), nullable=False, default="in_progress")
    fault_tree_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "ChatMessageModel",
        back_populates="session",
        order_by="ChatMessageModel.created_at",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String(36),
        ForeignKey("diagnosis_sessions.id"),
        nullable=False,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    session = relationship("SessionModel", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session_created", "session_id", "created_at"),
    )
