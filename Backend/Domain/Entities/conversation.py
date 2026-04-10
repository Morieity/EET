import uuid
from datetime import datetime


class ChatRound:
    def __init__(
        self,
        question: str,
        prompt: str = "",
        answer: str = "",
        sources: list[dict] | None = None,
        round_id: str | None = None,
        created_at: datetime | None = None,
    ):
        self.id = round_id or str(uuid.uuid4())
        self.question = question
        self.prompt = prompt
        self.answer = answer
        self.sources = sources or []
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "prompt": self.prompt,
            "answer": self.answer,
            "sources": self.sources,
            "created_at": self.created_at.isoformat(),
        }


class Conversation:
    def __init__(
        self,
        name: str,
        conversation_id: str | None = None,
        created_at: datetime | None = None,
        rounds: list[ChatRound] | None = None,
    ):
        self.id = conversation_id or str(uuid.uuid4())
        self.name = name
        self.created_at = created_at or datetime.now()
        self.rounds = rounds or []
        self.round_count = len(self.rounds)

    def add_round(self, chat_round: ChatRound) -> None:
        self.rounds.append(chat_round)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "rounds": [r.to_dict() for r in self.rounds],
            "round_count": getattr(self, 'round_count', len(self.rounds)),
        }
