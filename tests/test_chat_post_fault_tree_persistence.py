import json
import threading
import time
from collections.abc import Generator

from flask import Flask

from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill
from Backend.Application.UseCases.ChatUseCase import ChatUseCase
from Backend.Domain.Entities.conversation import ChatRound, Conversation
from Backend.Domain.Entities.fault_tree import FaultTree
from Backend.Web.Endpoints.ChatEndpoint import create_chat_blueprint


class _InMemoryConversationRepo(IConversationRepository):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._conversations: dict[str, Conversation] = {}

    def save(self, conversation: Conversation) -> None:
        with self._lock:
            self._conversations[conversation.id] = conversation

    def get_by_id(self, conversation_id: str) -> Conversation | None:
        with self._lock:
            return self._conversations.get(conversation_id)

    def get_all(self) -> list[Conversation]:
        with self._lock:
            return list(self._conversations.values())

    def delete(self, conversation_id: str) -> None:
        with self._lock:
            self._conversations.pop(conversation_id, None)

    def add_round(self, conversation_id: str, chat_round: ChatRound) -> None:
        with self._lock:
            self._conversations[conversation_id].add_round(chat_round)

    def link_latest_round_fault_tree(self, conversation_id: str, fault_tree_id: str) -> bool:
        with self._lock:
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
        self._lock = threading.Lock()
        self._trees: dict[str, FaultTree] = {}

    def save(self, fault_tree: FaultTree) -> None:
        with self._lock:
            self._trees[fault_tree.id] = fault_tree

    def get_by_id(self, tree_id: str) -> FaultTree | None:
        with self._lock:
            return self._trees.get(tree_id)

    def get_by_conversation_id(self, conversation_id: str) -> FaultTree | None:
        with self._lock:
            trees = [t for t in self._trees.values() if t.conversation_id == conversation_id]
            if not trees:
                return None
            return max(trees, key=lambda t: t.created_at)

    def get_all(self) -> list[FaultTree]:
        with self._lock:
            return list(self._trees.values())

    def update(self, fault_tree: FaultTree) -> None:
        with self._lock:
            self._trees[fault_tree.id] = fault_tree

    def delete(self, tree_id: str) -> None:
        with self._lock:
            self._trees.pop(tree_id, None)


class _NoopVectorStore(IVectorStoreRepository):
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

    def delete_relations_by_file(self, file_name: str) -> None:
        return None


class _DelayedToolLLM(ILLMService):
    def __init__(self, tool_delay_sec: float = 0.2) -> None:
        self._tool_delay_sec = tool_delay_sec

    def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        yield "这是"
        yield "一条测试回复。"

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        time.sleep(self._tool_delay_sec)
        return {
            "type": "tool_call",
            "name": "generate_fault_tree",
            "arguments": {
                "name": "设备检查发现问题",
                "nodes": [
                    {"id": "n1", "label": "设备检查发现问题", "node_type": "event"},
                    {"id": "g1", "label": "", "node_type": "gate", "gate_type": "OR"},
                    {"id": "n2", "label": "通讯配置异常", "node_type": "event"},
                ],
                "edges": [
                    {"id": "e1", "source_id": "n1", "target_id": "g1"},
                    {"id": "e2", "source_id": "g1", "target_id": "n2"},
                ],
            },
        }


class _NoopDeleteConversationUseCase:
    def execute(self, conversation_id: str) -> None:
        return None


def _parse_sse_events(raw_stream: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    event_type = None
    for line in raw_stream.splitlines():
        if not line:
            event_type = None
            continue
        if line.startswith("event: "):
            event_type = line[7:].strip()
            continue
        if line.startswith("data: "):
            payload = json.loads(line[6:].strip())
            if event_type:
                events.append((event_type, payload))
            event_type = None
    return events


def test_post_chat_same_conversation_persists_round_and_fault_tree_after_async_delay():
    conversation_repo = _InMemoryConversationRepo()
    fault_tree_repo = _InMemoryFaultTreeRepo()
    llm = _DelayedToolLLM(tool_delay_sec=0.2)
    fault_tree_skill = FaultTreeSkill(
        fault_tree_repository=fault_tree_repo,
        conversation_repository=conversation_repo,
    )
    chat_use_case = ChatUseCase(
        conversation_repository=conversation_repo,
        vector_store_repository=_NoopVectorStore(),
        llm_service=llm,
        fault_tree_skill=fault_tree_skill,
        graph_repository=None,
        context_manager=None,
        fault_tree_wait_timeout_seconds=0.01,
    )

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(
        create_chat_blueprint(
            chat_use_case=chat_use_case,
            delete_conversation_use_case=_NoopDeleteConversationUseCase(),
            conversation_repository=conversation_repo,
        )
    )
    client = app.test_client()

    first_question = "你好，现在我要对设备做检查，我可能会遇到哪些主要的问题？给我一个分步排查的计划"
    first_response = client.post("/api/chat", json={"question": first_question})
    first_events = _parse_sse_events(first_response.get_data(as_text=True))
    first_conversation_event = next(payload for et, payload in first_events if et == "conversation")
    conversation_id = first_conversation_event["conversation_id"]
    assert any(et == "done" for et, _ in first_events)

    second_question = "请生成故障树，分析设备检查发现问题并给出结构化树"
    second_response = client.post(
        "/api/chat",
        json={"question": second_question, "conversation_id": conversation_id},
    )
    second_events = _parse_sse_events(second_response.get_data(as_text=True))
    assert any(et == "done" for et, _ in second_events)

    # 模拟前端刷新后加载历史：等待慢速工具线程完成并回填 fault_tree_id。
    time.sleep(0.35)

    conversation_detail = client.get(f"/api/conversations/{conversation_id}").get_json()
    rounds = conversation_detail["rounds"]
    assert len(rounds) == 2

    second_round = rounds[-1]
    assert second_round["question"] == second_question
    assert second_round["answer"]
    assert second_round["fault_tree_id"], "异步故障树应最终回填到同一轮对话"
    assert fault_tree_repo.get_by_id(second_round["fault_tree_id"]) is not None
