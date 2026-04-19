from dataclasses import dataclass, field

from Backend.Application.ContextManagement.ContextTypes import (
    GraphPath,
    MessageRecord,
    ScoredDocument,
)


@dataclass(frozen=True)
class ContextManagerConfig:
    """Runtime knobs for context orchestration."""

    max_context_tokens: int = 32000
    max_history_rounds: int = 10
    mmr_top_k: int = 15
    mmr_relevance_weight: float = 0.7
    # 最小致信度
    min_path_confidence: float = 0.4
    # 最大路径数
    max_graph_paths: int = 20
    # 历史消息中，hot指最新的，warm指较早的，这里控制轮数
    history_hot_size: int = 3
    history_warm_size: int = 7
    # 压缩率，即压缩后保留的字符数占原始字符数的比例
    compression_keep_rate: float = 0.5
    # 压缩后保留的最小字符数
    compression_min_chars: int = 160


@dataclass
class ContextPreparationResult:
    """Prepared context artifacts consumed by ChatUseCase."""

    context: str
    user_content: str
    history_messages: list[MessageRecord] = field(default_factory=list)
    sources: list[ScoredDocument] = field(default_factory=list)
    graph_paths: list[GraphPath] = field(default_factory=list)
    seed_names: list[str] = field(default_factory=list)
    budget_actions: list[str] = field(default_factory=list)
    prompt_token_estimate: int = 0
    budget_plan: dict[str, int] = field(default_factory=dict)
