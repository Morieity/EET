import json
import logging
from datetime import datetime
from Backend.Domain.Entities.conversation import Conversation, ChatRound
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Infrastructure.persistence.database import get_connection

logger = logging.getLogger(__name__)


class SQLiteConversationRepository(IConversationRepository):

    def save(self, conversation: Conversation) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO conversations (id, name, created_at) VALUES (?, ?, ?)",
                (conversation.id, conversation.name, conversation.created_at.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, conversation_id: str) -> Conversation | None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, name, created_at FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            if row is None:
                return None

            rounds = self._load_rounds(conn, conversation_id)
            return Conversation(
                conversation_id=row["id"],
                name=row["name"],
                created_at=datetime.fromisoformat(row["created_at"]),
                rounds=rounds,
            )
        finally:
            conn.close()

    def get_all(self) -> list[Conversation]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, name, created_at FROM conversations ORDER BY created_at DESC"
            ).fetchall()
            return [
                Conversation(
                    conversation_id=row["id"],
                    name=row["name"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]
        finally:
            conn.close()

    def delete(self, conversation_id: str) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM chat_rounds WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
        finally:
            conn.close()

    def add_round(self, conversation_id: str, chat_round: ChatRound) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO chat_rounds (id, conversation_id, question, prompt, answer, sources, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    chat_round.id,
                    conversation_id,
                    chat_round.question,
                    chat_round.prompt,
                    chat_round.answer,
                    json.dumps(chat_round.sources, ensure_ascii=False),
                    chat_round.created_at.isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _load_rounds(conn, conversation_id: str) -> list[ChatRound]:
        rows = conn.execute(
            "SELECT id, question, prompt, answer, sources, created_at "
            "FROM chat_rounds WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        ).fetchall()
        return [
            ChatRound(
                round_id=row["id"],
                question=row["question"],
                prompt=row["prompt"],
                answer=row["answer"],
                sources=json.loads(row["sources"]) if row["sources"] else [],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]
