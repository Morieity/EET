import json

import pytest
from flask import Flask

from Backend.Web.Endpoints.ChatEndpoint import create_chat_blueprint


class _StubChatUseCase:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def execute(self, question: str, conversation_id: str | None = None):
        for event in self.events:
            yield event


class _StubDeleteConversationUseCase:
    def execute(self, conversation_id: str) -> None:
        return None


class _StubConversationRepository:
    def get_all(self) -> list:
        return []

    def get_by_id(self, conversation_id: str):
        return None


def _parse_sse_like_frontend(raw_stream: str) -> list[tuple[str, dict]]:
    """复用前端逐行解析策略，验证后端输出兼容性。"""
    parsed: list[tuple[str, dict]] = []
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
                parsed.append((event_type, payload))
            event_type = None

    return parsed


@pytest.fixture(scope="module")
def _app_and_chat_uc():
    chat_uc = _StubChatUseCase()
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(
        create_chat_blueprint(
            chat_use_case=chat_uc,
            delete_conversation_use_case=_StubDeleteConversationUseCase(),
            conversation_repository=_StubConversationRepository(),
        )
    )
    return app, chat_uc


@pytest.fixture()
def client(_app_and_chat_uc):
    app, _ = _app_and_chat_uc
    return app.test_client()


@pytest.fixture()
def chat_uc(_app_and_chat_uc):
    _, stub = _app_and_chat_uc
    stub.events = []
    return stub


def test_chat_sse_fault_tree_event_can_be_parsed_by_frontend(client, chat_uc):
    fault_tree = {
        "id": "ft-001",
        "name": "主泵故障树",
        "nodes": [
            {"id": "n1", "label": "主泵停机", "node_type": "event"},
            {"id": "g1", "label": "", "node_type": "gate", "gate_type": "OR"},
            {"id": "n2", "label": "电机故障", "node_type": "event"},
        ],
        "edges": [
            {"id": "e1", "source_id": "n1", "target_id": "g1"},
            {"id": "e2", "source_id": "g1", "target_id": "n2"},
        ],
        "created_at": "2026-04-15T11:00:00",
        "conversation_id": "conv-001",
    }
    chat_uc.events = [
        {"type": "conversation", "conversation_id": "conv-001", "name": "生成故障树"},
        {"type": "sources", "sources": []},
        {"type": "token", "content": "已完成分析。"},
        {"type": "fault_tree", "fault_tree": fault_tree},
        {
            "type": "done",
            "conversation_id": "conv-001",
            "answer": "已完成分析。",
            "fault_tree_id": "ft-001",
        },
    ]

    response = client.post("/api/chat", json={"question": "请生成故障树"})

    assert response.status_code == 200
    assert response.content_type.startswith("text/event-stream")

    events = _parse_sse_like_frontend(response.get_data(as_text=True))
    event_types = [event_type for event_type, _ in events]
    assert event_types == ["conversation", "sources", "token", "fault_tree", "done"]

    fault_tree_payload = events[3][1]["fault_tree"]
    done_payload = events[4][1]
    assert fault_tree_payload["id"] == "ft-001"
    assert fault_tree_payload["nodes"][0]["label"] == "主泵停机"
    assert done_payload["fault_tree_id"] == "ft-001"


def test_chat_sse_fault_tree_json_stays_single_line_for_data_field(client, chat_uc):
    fault_tree = {
        "id": "ft-002",
        "name": "换行兼容性验证",
        "nodes": [
            {"id": "n1", "label": "主泵温升异常\n二次确认 {A}", "node_type": "event"}
        ],
        "edges": [],
        "created_at": "2026-04-15T11:00:00",
        "conversation_id": "conv-002",
    }
    chat_uc.events = [
        {"type": "conversation", "conversation_id": "conv-002", "name": "换行测试"},
        {"type": "fault_tree", "fault_tree": fault_tree},
        {"type": "done", "conversation_id": "conv-002", "answer": "ok", "fault_tree_id": "ft-002"},
    ]

    response = client.post("/api/chat", json={"question": "生成故障树并包含换行"})
    raw = response.get_data(as_text=True)

    fault_tree_blocks = [block for block in raw.split("\n\n") if block.startswith("event: fault_tree")]
    assert len(fault_tree_blocks) == 1

    lines = fault_tree_blocks[0].splitlines()
    assert len(lines) == 2
    assert lines[1].startswith("data: ")

    payload = json.loads(lines[1][6:])
    assert payload["fault_tree"]["nodes"][0]["label"] == "主泵温升异常\n二次确认 {A}"


def test_chat_endpoint_does_not_mutate_original_use_case_event(client, chat_uc):
    original_fault_tree_event = {
        "type": "fault_tree",
        "fault_tree": {
            "id": "ft-003",
            "name": "不应被修改",
            "nodes": [],
            "edges": [],
            "created_at": "2026-04-15T11:00:00",
            "conversation_id": "conv-003",
        },
    }
    chat_uc.events = [
        {"type": "conversation", "conversation_id": "conv-003", "name": "副作用测试"},
        original_fault_tree_event,
        {"type": "done", "conversation_id": "conv-003", "answer": "ok", "fault_tree_id": "ft-003"},
    ]

    response = client.post("/api/chat", json={"question": "测试事件对象副作用"})

    assert response.status_code == 200
    assert original_fault_tree_event["type"] == "fault_tree"
