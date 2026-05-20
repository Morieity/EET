from dataclasses import dataclass

from Backend.Application.ContextManagement.ContextManagerTypes import ContextManagerConfig

MAX_HISTORY_ROUNDS = 20
DEFAULT_CONTEXT_CONFIG = ContextManagerConfig(max_history_rounds=MAX_HISTORY_ROUNDS)


@dataclass(frozen=True)
class RagRetrievalConfig:
    graph_hops: int = 2
    graph_min_sources: int = 5
    max_sources: int = 15
    fallback_score_threshold: float = 0.1


@dataclass(frozen=True)
class FaultTreeGenerationConfig:
    wait_timeout_seconds: float = 120
