from abc import ABC, abstractmethod

from Backend.Application.ContextManagement.ContextManagerTypes import (
    ContextManagerConfig,
    ContextPreparationResult,
)
from Backend.Application.ContextManagement.ContextTypes import GraphPath, ScoredDocument
from Backend.Domain.Entities.conversation import ChatRound


class IContextManager(ABC):
    @abstractmethod
    def prepare_context(
        self,
        question: str,
        conversation_rounds: list[ChatRound],
        seed_names: list[str],
        graph_paths: list[GraphPath],
        sources: list[ScoredDocument],
        config: ContextManagerConfig | None = None,
    ) -> ContextPreparationResult:
        """Build prompt artifacts in a deterministic orchestration order."""
        pass
