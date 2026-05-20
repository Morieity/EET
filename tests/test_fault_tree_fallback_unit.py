from collections.abc import Generator

from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill
from Backend.Application.UseCases.ChatUseCase import ChatUseCase
from Backend.Domain.Entities.conversation import ChatRound, Conversation
from Backend.Domain.Entities.fault_tree import FaultTree


class _InMemoryConversationRepo(IConversationRepository):
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}

    def save(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation

    def get_by_id(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def get_all(self) -> list[Conversation]:
        return list(self._conversations.values())

    def delete(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)

    def add_round(self, conversation_id: str, chat_round: ChatRound) -> None:
        conversation = self._conversations[conversation_id]
        conversation.add_round(chat_round)

    def link_latest_round_fault_tree(self, conversation_id: str, fault_tree_id: str) -> bool:
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            return False
        for round_item in reversed(conversation.rounds):
            if not round_item.fault_tree_id:
                round_item.fault_tree_id = fault_tree_id
                return True
        return False


class _InMemoryFaultTreeRepo(IFaultTreeRepository):
    def __init__(self) -> None:
        self._trees: dict[str, FaultTree] = {}

    def save(self, fault_tree: FaultTree) -> None:
        self._trees[fault_tree.id] = fault_tree

    def get_by_id(self, tree_id: str) -> FaultTree | None:
        return self._trees.get(tree_id)

    def get_by_conversation_id(self, conversation_id: str) -> FaultTree | None:
        for tree in reversed(list(self._trees.values())):
            if tree.conversation_id == conversation_id:
                return tree
        return None

    def get_all(self) -> list[FaultTree]:
        return list(self._trees.values())

    def update(self, fault_tree: FaultTree) -> None:
        self._trees[fault_tree.id] = fault_tree

    def delete(self, tree_id: str) -> None:
        self._trees.pop(tree_id, None)


class _VectorStoreNoop(IVectorStoreRepository):
    def add_documents(self, file_name: str, documents: list) -> None:
        return None

    def delete_by_file_name(self, file_name: str) -> None:
        return None

    def search(self, query: str, k: int = 5, score_threshold: float = 0.1) -> list[dict]:
        return []

    def add_entity(self, name: str, entity_type: str, source_file: str = "") -> None:
        return None

    def search_entities(self, query: str, top_k: int = 20, score_threshold: float = 0.85) -> list[dict]:
        return []

    def delete_entities_by_file(self, file_name: str) -> None:
        return None

    def add_relation(self, head: str, relation: str, tail: str, source_file: str = "") -> None:
        return None

    def search_relations(self, query: str, top_k: int = 20, score_threshold: float = 0.5) -> list[dict]:
        return []

    def search_by_sources(self, source_keys: list[dict], query: str, k: int = 15) -> list[dict]:
        return []

    def delete_relations_by_file(self, file_name: str) -> None:
        return None


class _FailingStreamLLM(ILLMService):
    def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        raise RuntimeError("stream failed")
        yield ""  # pragma: no cover

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        return {
            "type": "tool_call",
            "name": "generate_fault_tree",
            "arguments": {
                "name": "测试故障树",
                "nodes": [
                    {"id": "n1", "label": "顶事件", "node_type": "event"},
                    {"id": "g1", "label": "", "node_type": "gate", "gate_type": "OR"},
                    {"id": "n2", "label": "子事件", "node_type": "event"},
                ],
                "edges": [
                    {"id": "e1", "source_id": "n1", "target_id": "g1"},
                    {"id": "e2", "source_id": "g1", "target_id": "n2"},
                ],
            },
        }


def test_fault_tree_skill_can_link_latest_unbound_round() -> None:
    conversation_repo = _InMemoryConversationRepo()
    fault_tree_repo = _InMemoryFaultTreeRepo()
    skill = FaultTreeSkill(fault_tree_repo, conversation_repository=conversation_repo)

    conversation = Conversation(name="测试会话")
    conversation_repo.save(conversation)
    conversation_repo.add_round(conversation.id, ChatRound(question="先聊一轮", answer="ok"))
    assert conversation.rounds[-1].fault_tree_id is None

    generated = skill.execute(
        function_name="generate_fault_tree",
        arguments={
            "name": "补链路测试",
            "nodes": [{"id": "n1", "label": "顶事件", "node_type": "event"}],
            "edges": [],
        },
        conversation_id=conversation.id,
    )

    assert conversation.rounds[-1].fault_tree_id == generated.id


def test_chat_use_case_stream_error_still_persists_round_with_fault_tree_id() -> None:
    conversation_repo = _InMemoryConversationRepo()
    fault_tree_repo = _InMemoryFaultTreeRepo()
    skill = FaultTreeSkill(fault_tree_repo, conversation_repository=conversation_repo)

    use_case = ChatUseCase(
        conversation_repository=conversation_repo,
        vector_store_repository=_VectorStoreNoop(),
        llm_service=_FailingStreamLLM(),
        fault_tree_skill=skill,
        graph_repository=None,
        context_manager=None,
    )

    events = list(use_case.execute("请生成故障树"))
    event_types = [event["type"] for event in events]
    assert event_types[0] == "conversation"
    assert "error" in event_types

    conversation_id = events[0]["conversation_id"]
    conversation = conversation_repo.get_by_id(conversation_id)
    assert conversation is not None
    assert len(conversation.rounds) == 1

    saved_round = conversation.rounds[0]
    assert saved_round.fault_tree_id is not None
    assert fault_tree_repo.get_by_id(saved_round.fault_tree_id) is not None
