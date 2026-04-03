from abc import ABC, abstractmethod
from Backend.Domain.Entities.fault_tree import FaultTree


class IFaultTreeRepository(ABC):
    @abstractmethod
    def save(self, fault_tree: FaultTree) -> None:
        pass

    @abstractmethod
    def get_by_id(self, tree_id: str) -> FaultTree | None:
        pass

    @abstractmethod
    def get_by_conversation_id(self, conversation_id: str) -> FaultTree | None:
        """获取某个对话关联的故障树（支持多轮对话修改同一棵树）。"""
        pass

    @abstractmethod
    def get_all(self) -> list[FaultTree]:
        pass

    @abstractmethod
    def update(self, fault_tree: FaultTree) -> None:
        pass

    @abstractmethod
    def delete(self, tree_id: str) -> None:
        pass
