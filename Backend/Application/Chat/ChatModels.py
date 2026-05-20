from dataclasses import dataclass, field

from Backend.Application.ContextManagement.ContextManagerTypes import ContextPreparationResult
from Backend.Application.ContextManagement.ContextTypes import GraphPath, MessageRecord, ScoredDocument


@dataclass
class RetrievalResult:
    seed_names: list[str] = field(default_factory=list)
    graph_paths: list[GraphPath] = field(default_factory=list)
    sources: list[ScoredDocument] = field(default_factory=list)


@dataclass
class ChatContextBuildResult:
    messages: list[MessageRecord]
    user_content: str
    sources: list[ScoredDocument]
    seed_names: list[str] = field(default_factory=list)
    graph_paths: list[GraphPath] = field(default_factory=list)
    context: str = ""
    context_result: ContextPreparationResult | None = None


@dataclass(frozen=True)
class FaultTreeIntent:
    is_generate: bool
    is_update: bool
    is_direct: bool
    is_request: bool


@dataclass
class ChatResponseState:
    full_answer: str = ""
    fault_tree_id: str | None = None
    error_message: str | None = None
