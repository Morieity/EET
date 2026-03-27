"""SessionRepositoryImpl — SQLite 会话仓储实现。"""
from datetime import datetime, timezone
from typing import Optional

from Backend.Domain.Common.Enums.message_role import MessageRole
from Backend.Domain.Common.Enums.session_status import SessionStatus
from Backend.Domain.Entities.diagnosis_session import ChatMessage, DiagnosisSession
from Backend.Infrastructure.persistence.database import ScopedSession
from Backend.Infrastructure.persistence.models.session_model import (
    ChatMessageModel,
    SessionModel,
)


class SessionRepositoryImpl:
    """基于 SQLAlchemy 的 SessionRepository 实现。"""

    def save(self, session: DiagnosisSession) -> None:
        db = ScopedSession()
        try:
            existing = db.get(SessionModel, session.id)
            if existing is None:
                model = self._to_model(session)
                db.add(model)
            else:
                existing.status = session.status.value
                existing.fault_tree_id = session.fault_tree_id
                existing.updated_at = session.updated_at

                existing_msg_ids = {m.id for m in existing.messages}
                for msg in session.messages:
                    if msg.id not in existing_msg_ids:
                        existing.messages.append(self._message_to_model(msg, session.id))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            ScopedSession.remove()

    def find_by_id(self, session_id: str) -> Optional[DiagnosisSession]:
        db = ScopedSession()
        try:
            model = db.get(SessionModel, session_id)
            if model is None:
                return None
            return self._to_entity(model)
        finally:
            ScopedSession.remove()

    # ---- Mappers ----

    @staticmethod
    def _to_model(session: DiagnosisSession) -> SessionModel:
        model = SessionModel(
            id=session.id,
            status=session.status.value,
            fault_tree_id=session.fault_tree_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
        model.messages = [
            SessionRepositoryImpl._message_to_model(m, session.id)
            for m in session.messages
        ]
        return model

    @staticmethod
    def _message_to_model(msg: ChatMessage, session_id: str) -> ChatMessageModel:
        return ChatMessageModel(
            id=msg.id,
            session_id=session_id,
            role=msg.role.value,
            content=msg.content,
            created_at=msg.created_at,
        )

    @staticmethod
    def _to_entity(model: SessionModel) -> DiagnosisSession:
        messages = [
            ChatMessage(
                id=m.id,
                role=MessageRole(m.role),
                content=m.content,
                created_at=m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=timezone.utc),
            )
            for m in model.messages
        ]
        created = model.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        updated = model.updated_at
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)

        return DiagnosisSession(
            id=model.id,
            status=SessionStatus(model.status),
            created_at=created,
            updated_at=updated,
            fault_tree_id=model.fault_tree_id,
            messages=messages,
        )
