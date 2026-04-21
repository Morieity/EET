import logging
from Backend.Domain.Entities.fault_tree import FaultTree
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository

logger = logging.getLogger(__name__)


class FaultTreeUseCase:
    def __init__(self, fault_tree_repository: IFaultTreeRepository):
        self._repo = fault_tree_repository

    def get_by_id(self, tree_id: str) -> FaultTree | None:
        return self._repo.get_by_id(tree_id)

    def get_by_conversation_id(self, conversation_id: str) -> FaultTree | None:
        return self._repo.get_by_conversation_id(conversation_id)

    def get_all(self) -> list[FaultTree]:
        return self._repo.get_all()

    def delete(self, tree_id: str) -> None:
        existing = self._repo.get_by_id(tree_id)
        if existing is None:
            raise ValueError(f"Fault tree not found: {tree_id}")
        self._repo.delete(tree_id)
        logger.info("Fault tree deleted: %s", tree_id)

    def update(self, tree_id: str, data: dict) -> FaultTree:
        existing = self._repo.get_by_id(tree_id)
        if existing is None:
            raise ValueError(f"Fault tree not found: {tree_id}")
        updated = FaultTree.from_dict({**data, "id": tree_id})
        updated.created_at = existing.created_at
        updated.conversation_id = existing.conversation_id
        self._repo.update(updated)
        logger.info("Fault tree updated via API: %s", tree_id)
        return updated
