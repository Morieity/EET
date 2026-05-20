import logging

from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Domain.Entities.conversation import ChatRound, Conversation

logger = logging.getLogger(__name__)


class ChatConversationService:
    def __init__(self, conversation_repository: IConversationRepository):
        self._conversation_repo = conversation_repository

    def get_or_create(
        self,
        question: str,
        conversation_id: str | None = None,
    ) -> tuple[Conversation | None, str | None]:
        if conversation_id:
            conversation = self._conversation_repo.get_by_id(conversation_id)
            if conversation is None:
                return None, f"Conversation not found: {conversation_id}"
            return conversation, None

        name = question[:30] if len(question) > 30 else question
        conversation = Conversation(name=name)
        self._conversation_repo.save(conversation)
        logger.info("New conversation created: %s", conversation.id)
        return conversation, None

    @staticmethod
    def to_event(conversation: Conversation) -> dict:
        return {
            "type": "conversation",
            "conversation_id": conversation.id,
            "name": conversation.name,
        }

    def persist_round(
        self,
        conversation_id: str,
        question: str,
        prompt: str,
        answer: str,
        sources: list[dict],
        fault_tree_id: str | None = None,
    ) -> None:
        chat_round = ChatRound(
            question=question,
            prompt=prompt,
            answer=answer,
            sources=sources,
            fault_tree_id=fault_tree_id,
        )
        self._conversation_repo.add_round(conversation_id, chat_round)
        logger.info("Chat round saved for conversation: %s", conversation_id)
