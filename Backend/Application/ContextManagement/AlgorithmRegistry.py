from Backend.Application.ContextManagement.Algorithms.HistoryTieringAlgorithm import (
    HistoryTieringAlgorithm,
)
from Backend.Application.ContextManagement.Algorithms.MMRDeduplicationAlgorithm import (
    MMRDeduplicationAlgorithm,
)
from Backend.Application.ContextManagement.Algorithms.PathPruningAlgorithm import (
    PathPruningAlgorithm,
)
from Backend.Application.ContextManagement.Algorithms.QueryAwareCompressionAlgorithm import (
    QueryAwareCompressionAlgorithm,
)
from Backend.Application.ContextManagement.Algorithms.QueryPlacementAlgorithm import (
    QueryPlacementAlgorithm,
)
from Backend.Application.ContextManagement.Algorithms.RetrievalReorderingAlgorithm import (
    RetrievalReorderingAlgorithm,
)
from Backend.Application.ContextManagement.Algorithms.TokenBudgetingAlgorithm import (
    TokenBudgetingAlgorithm,
)


class ContextAlgorithmRegistry:
    """用于管理第 1 步创建的算法模块注册表。

    该注册表本身不执行业务流程。
    它只暴露算法实例，供后续步骤装配到用例中。
    """

    def __init__(self) -> None:
        self._algorithms: dict[str, object] = {
            "retrieval_reordering": RetrievalReorderingAlgorithm(),
            "mmr_deduplication": MMRDeduplicationAlgorithm(),
            "token_budgeting": TokenBudgetingAlgorithm(),
            "history_tiering": HistoryTieringAlgorithm(),
            "path_pruning": PathPruningAlgorithm(),
            "query_placement": QueryPlacementAlgorithm(),
            "query_aware_compression": QueryAwareCompressionAlgorithm(),
        }

    def get(self, name: str) -> object:
        if name not in self._algorithms:
            raise KeyError(f"Unknown context algorithm: {name}")
        return self._algorithms[name]

    def names(self) -> list[str]:
        return sorted(self._algorithms.keys())

    def as_dict(self) -> dict[str, object]:
        return dict(self._algorithms)
