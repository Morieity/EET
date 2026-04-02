import logging
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository

logger = logging.getLogger(__name__)


class DeleteConversationUseCase:
    def __init__(self, conversation_repository: IConversationRepository):
        self._conversation_repo = conversation_repository

    def execute(self, conversation_id: str) -> None:
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")

        self._conversation_repo.delete(conversation_id)
        logger.info("Conversation deleted: %s", conversation_id)
