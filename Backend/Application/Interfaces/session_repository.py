from typing import Protocol, Optional

from Backend.Domain.Entities.diagnosis_session import DiagnosisSession


class SessionRepository(Protocol):
    """诊断会话仓储接口。"""

    def save(self, session: DiagnosisSession) -> None:
        """持久化会话（含消息列表）。"""
        ...

    def find_by_id(self, session_id: str) -> Optional[DiagnosisSession]:
        """根据 ID 加载会话及其消息；不存在时返回 None。"""
        ...
