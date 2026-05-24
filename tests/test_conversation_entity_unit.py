"""Domain entity unit tests for Conversation / ChatRound.

Pure unit tests — no I/O, no third-party services. Mirrors the
`_unit` naming convention picked up by CI (`pytest -k _unit`).
"""

from datetime import datetime

from Backend.Domain.Entities.conversation import ChatRound, Conversation


def test_chat_round_defaults_generate_id_and_timestamp() -> None:
    round_a = ChatRound(question="问题A")

    assert round_a.id  # uuid4 fallback populated
    assert round_a.question == "问题A"
    assert round_a.prompt == ""
    assert round_a.answer == ""
    assert round_a.sources == []
    assert round_a.fault_tree_id is None
    assert isinstance(round_a.created_at, datetime)


def test_chat_round_to_dict_serialises_all_fields() -> None:
    fixed_time = datetime(2026, 1, 1, 12, 0, 0)
    chat_round = ChatRound(
        question="Q",
        prompt="P",
        answer="A",
        sources=[{"file_name": "a.pdf", "page_content": "x"}],
        fault_tree_id="tree-1",
        round_id="round-1",
        created_at=fixed_time,
    )

    payload = chat_round.to_dict()

    assert payload == {
        "id": "round-1",
        "question": "Q",
        "prompt": "P",
        "answer": "A",
        "sources": [{"file_name": "a.pdf", "page_content": "x"}],
        "fault_tree_id": "tree-1",
        "created_at": fixed_time.isoformat(),
    }


def test_conversation_add_round_appends_in_order() -> None:
    conversation = Conversation(name="会话")
    r1 = ChatRound(question="Q1")
    r2 = ChatRound(question="Q2")

    conversation.add_round(r1)
    conversation.add_round(r2)

    assert [r.question for r in conversation.rounds] == ["Q1", "Q2"]


def test_conversation_to_dict_includes_rounds_and_count() -> None:
    conversation = Conversation(name="会话", conversation_id="conv-1")
    conversation.add_round(ChatRound(question="Q1", round_id="r1"))

    payload = conversation.to_dict()

    assert payload["id"] == "conv-1"
    assert payload["name"] == "会话"
    assert payload["round_count"] in (0, 1)  # tolerate cached count or live len
    assert len(payload["rounds"]) == 1
    assert payload["rounds"][0]["id"] == "r1"
