"""GetSessionUseCase — 查询诊断会话详情（含完整对话历史）。"""
from Backend.Application.Interfaces.session_repository import SessionRepository


class GetSessionUseCase:
    def __init__(self, session_repository: SessionRepository):
        self._session_repo = session_repository

    def execute(self, session_id: str) -> dict:
        session = self._session_repo.find_by_id(session_id)
        if session is None:
            raise LookupError("Session not found")

        return {
            "session_id": session.id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "fault_tree_id": session.fault_tree_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role.value,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in session.messages
            ],
        }
