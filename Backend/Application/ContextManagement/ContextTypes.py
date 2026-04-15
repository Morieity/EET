from typing import Any
from typing import TypedDict


class ScoredDocument(TypedDict, total=False):
    file_name: str
    page_content: str
    score: float
    metadata: dict[str, Any]


GraphPath = TypedDict(
    "GraphPath",
    {
        "from": str,
        "relation": str,
        "to": str,
        "score": float,
        "confidence": float,
        "source_file": str,
    },
    total=False,
)


class ConversationRoundRecord(TypedDict, total=False):
    question: str
    answer: str
    prompt: str
    created_at: str


class MessageRecord(TypedDict):
    role: str
    content: str
