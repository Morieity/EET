import logging
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository

logger = logging.getLogger(__name__)


class DeleteConversationUseCase:
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        fault_tree_repository: IFaultTreeRepository | None = None,
    ):
        self._conversation_repo = conversation_repository
        self._fault_tree_repo = fault_tree_repository

    def execute(self, conversation_id: str) -> None:
        conversation = self._conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # 删除关联的故障树（避免孤立数据）
        if self._fault_tree_repo:
            linked_tree = self._fault_tree_repo.get_by_conversation_id(conversation_id)
            if linked_tree:
                self._fault_tree_repo.delete(linked_tree.id)
                logger.info("Associated fault tree deleted: %s", linked_tree.id)

        self._conversation_repo.delete(conversation_id)
        logger.info("Conversation deleted: %s", conversation_id)
