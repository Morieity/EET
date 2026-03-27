"""fault_trees ORM 表模型（Data Mapper 模式），tree_data 使用 JSON。"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.types import JSON

from Backend.Infrastructure.persistence.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FaultTreeModel(Base):
    __tablename__ = "fault_trees"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    session_id = Column(
        String(36),
        ForeignKey("diagnosis_sessions.id"),
        nullable=False,
    )
    tree_data = Column(JSON, nullable=False)
    status = Column(String(30), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_fault_trees_session", "session_id"),
        Index("idx_fault_trees_status", "status"),
    )
