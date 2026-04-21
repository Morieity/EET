from abc import ABC, abstractmethod
from Backend.Domain.Entities.conversation import Conversation, ChatRound


class IConversationRepository(ABC):
    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        pass

    @abstractmethod
    def get_by_id(self, conversation_id: str) -> Conversation | None:
        pass

    @abstractmethod
    def get_all(self) -> list[Conversation]:
        pass

    @abstractmethod
    def delete(self, conversation_id: str) -> None:
        pass

    @abstractmethod
    def add_round(self, conversation_id: str, chat_round: ChatRound) -> None:
        pass

    @abstractmethod
    def link_latest_round_fault_tree(self, conversation_id: str, fault_tree_id: str) -> bool:
        """回填故障树 ID 到最近一轮未绑定故障树的对话记录。"""
        pass
