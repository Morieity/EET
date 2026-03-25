"""DiagnosisSession 聚合根与 ChatMessage 实体。

纯 Python dataclass，不依赖任何外部框架。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from Backend.Domain.Common.Enums.message_role import MessageRole
from Backend.Domain.Common.Enums.session_status import SessionStatus


@dataclass
class ChatMessage:
    """诊断会话中的单条消息。"""
    id: str
    role: MessageRole
    content: str
    created_at: datetime

    @staticmethod
    def create(role: MessageRole, content: str) -> "ChatMessage":
        if not content or not content.strip():
            raise ValueError("Message content MUST NOT be empty")
        return ChatMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
        )


@dataclass
class DiagnosisSession:
    """诊断会话聚合根。"""
    id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    fault_tree_id: Optional[str] = None
    messages: list[ChatMessage] = field(default_factory=list)

    # --- Factory ---

    @staticmethod
    def create() -> "DiagnosisSession":
        now = datetime.now(timezone.utc)
        return DiagnosisSession(
            id=str(uuid.uuid4()),
            status=SessionStatus.IN_PROGRESS,
            created_at=now,
            updated_at=now,
        )

    # --- Invariant enforcement ---

    def add_message(self, role: MessageRole, content: str) -> ChatMessage:
        """追加消息；已完成的会话不允许追加。"""
        if self.status == SessionStatus.COMPLETED:
            raise ValueError(
                f"Cannot add message to session in '{self.status.value}' state"
            )
        msg = ChatMessage.create(role, content)
        self.messages.append(msg)
        self.updated_at = datetime.now(timezone.utc)
        return msg

    def transition_to(self, target: SessionStatus) -> None:
        """执行合法的状态转换。"""
        if not self.status.can_transition_to(target):
            raise ValueError(
                f"Invalid transition: {self.status.value} → {target.value}"
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def link_fault_tree(self, fault_tree_id: str) -> None:
        """关联故障树 ID 并转换到 tree_generated 状态。"""
        self.fault_tree_id = fault_tree_id
        self.transition_to(SessionStatus.TREE_GENERATED)
