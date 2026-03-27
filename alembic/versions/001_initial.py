"""initial schema: diagnosis_sessions, chat_messages, fault_trees

Revision ID: 001_initial
Revises:
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diagnosis_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="in_progress"),
        sa.Column("fault_tree_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("diagnosis_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_messages_session_created", "chat_messages", ["session_id", "created_at"])

    op.create_table(
        "fault_trees",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("diagnosis_sessions.id"), nullable=False),
        sa.Column("tree_data", sa.JSON, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("confirmed_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_fault_trees_session", "fault_trees", ["session_id"])
    op.create_index("idx_fault_trees_status", "fault_trees", ["status"])


def downgrade() -> None:
    op.drop_table("fault_trees")
    op.drop_table("chat_messages")
    op.drop_table("diagnosis_sessions")
