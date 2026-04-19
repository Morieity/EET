from typing import Any, cast

from Backend.Application.ContextManagement.AlgorithmRegistry import ContextAlgorithmRegistry
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
from Backend.Application.ContextManagement.ContextManagerTypes import (
    ContextManagerConfig,
    ContextPreparationResult,
)
from Backend.Application.ContextManagement.ContextTypes import (
    ConversationRoundRecord,
    GraphPath,
    MessageRecord,
    ScoredDocument,
)
from Backend.Application.Interfaces.IContextManager import IContextManager
from Backend.Application.Interfaces.ILogger import ILogger
from Backend.Domain.Entities.conversation import ChatRound


class DefaultContextManager(IContextManager):
    """Rule-based context orchestrator built from step-1 algorithm modules."""

    def __init__(
        self,
        registry: ContextAlgorithmRegistry | None = None,
        default_config: ContextManagerConfig | None = None,
        context_logger: ILogger | None = None,
    ) -> None:
        self._registry = registry or ContextAlgorithmRegistry()
        self._default_config = default_config or ContextManagerConfig()
        self._context_logger = context_logger

        self._mmr = cast(
            MMRDeduplicationAlgorithm,
            self._registry.get("mmr_deduplication"),
        )
        self._reorder = cast(
            RetrievalReorderingAlgorithm,
            self._registry.get("retrieval_reordering"),
        )
        self._path_pruning = cast(
            PathPruningAlgorithm,
            self._registry.get("path_pruning"),
        )
        self._token_budget = cast(
            TokenBudgetingAlgorithm,
            self._registry.get("token_budgeting"),
        )
        self._history_tiering = cast(
            HistoryTieringAlgorithm,
            self._registry.get("history_tiering"),
        )
        self._query_placement = cast(
            QueryPlacementAlgorithm,
            self._registry.get("query_placement"),
        )
        self._query_compression = cast(
            QueryAwareCompressionAlgorithm,
            self._registry.get("query_aware_compression"),
        )

    def prepare_context(
        self,
        question: str,
        conversation_rounds: list[ChatRound],
        seed_names: list[str],
        graph_paths: list[GraphPath],
        sources: list[ScoredDocument],
        config: ContextManagerConfig | None = None,
        system_prompt_tokens: int = 0,
    ) -> ContextPreparationResult:
        """Prepare context by deterministic orchestration order.

        Order:
        1) Path pruning.
        2) MMR deduplication.
        3) Retrieval reordering.
        4) Token-budget evaluation.
        5) Conditional history/vector compression.
        6) Final context and query-at-end user content assembly.
        """
        cfg = config or self._default_config

        self._log_debug(
            "Context orchestration started",
            {
                "seed_count": len(seed_names),
                "path_count": len(graph_paths),
                "source_count": len(sources),
                "history_rounds": len(conversation_rounds),
                "max_context_tokens": cfg.max_context_tokens,
            },
        )

        clean_seed_names = [name for name in seed_names if name]
        working_paths = [dict(path) for path in graph_paths]
        working_sources = [dict(src) for src in sources]

        # 1) Graph path pruning.
        pruned_paths = self._path_pruning.prune(
            working_paths,
            min_confidence=cfg.min_path_confidence,
            max_paths=cfg.max_graph_paths,
            relation_diversity=True,
        )
        self._log_debug(
            "Path pruning finished",
            {
                "before": len(working_paths),
                "after": len(pruned_paths),
                "min_confidence": cfg.min_path_confidence,
                "max_paths": cfg.max_graph_paths,
            },
        )

        # 2) Source deduplication via MMR.
        mmr_sources = self._mmr.select(
            working_sources,
            top_k=cfg.mmr_top_k,
            relevance_weight=cfg.mmr_relevance_weight,
        )
        self._log_debug(
            "MMR deduplication finished",
            {
                "before": len(working_sources),
                "after": len(mmr_sources),
                "top_k": cfg.mmr_top_k,
                "relevance_weight": cfg.mmr_relevance_weight,
            },
        )

        # 3) Boundary-aware source reordering.
        reordered_sources = self._reorder.reorder(mmr_sources)
        self._log_debug(
            "Retrieval reordering finished",
            {
                "source_count": len(reordered_sources),
            },
        )

        # Build baseline history and context before budget decisions.
        history_messages = self._build_recent_history_messages(
            conversation_rounds,
            max_history_rounds=cfg.max_history_rounds,
        )
        context_text = self._build_context_text(
            seed_names=clean_seed_names,
            graph_paths=pruned_paths,
            sources=reordered_sources,
        )
        user_content = self._compose_user_content(question=question, context=context_text)

        # 4) Token-budget evaluation.
        # system_prompt_tokens 包含 SYSTEM_PROMPT + 故障树 skill prompt，
        # 这部分不可压缩，必须纳入总量估算。
        prompt_token_estimate = (
            system_prompt_tokens
            + self._estimate_messages_tokens(history_messages)
            + self._estimate_tokens(user_content)
        )
        budget_plan = self._token_budget.build_plan(cfg.max_context_tokens)
        budget_actions = self._token_budget.decide_actions(
            total_prompt_tokens=prompt_token_estimate,
            max_context_tokens=cfg.max_context_tokens,
        )
        self._log_debug(
            "Token budget evaluated",
            {
                "prompt_tokens": prompt_token_estimate,
                "utilization": round(
                    self._token_budget.utilization_rate(
                        prompt_token_estimate,
                        cfg.max_context_tokens,
                    ),
                    4,
                ),
                "actions": ",".join(budget_actions) or "none",
            },
        )

        final_paths = pruned_paths
        final_sources = reordered_sources

        # 5a) Conditional history tiering.
        if "compress_history_tier2" in budget_actions:
            history_messages = self._build_tiered_history_messages(
                conversation_rounds,
                hot_size=cfg.history_hot_size,
                warm_size=cfg.history_warm_size,
            )
            self._log_debug(
                "History tiering applied",
                {
                    "hot_size": cfg.history_hot_size,
                    "warm_size": cfg.history_warm_size,
                    "history_messages": len(history_messages),
                },
            )

        # 5b) Conditional vector compression.
        if "compress_vector_docs_keep_50pct" in budget_actions and final_sources:
            before_count = len(final_sources)
            final_sources = self._query_compression.compress_documents(
                final_sources,
                query=question,
                keep_rate=cfg.compression_keep_rate,
                min_chars=cfg.compression_min_chars,
            )
            self._log_debug(
                "Vector compression applied",
                {
                    "before": before_count,
                    "after": len(final_sources),
                    "keep_rate": cfg.compression_keep_rate,
                    "min_chars": cfg.compression_min_chars,
                },
            )

        if "vector_top_k_hard_cap" in budget_actions and final_sources:
            final_sources = final_sources[: min(3, len(final_sources))]
            self._log_debug(
                "Vector hard cap applied",
                {
                    "after": len(final_sources),
                    "hard_cap": 3,
                },
            )

        if "kg_one_hop_only" in budget_actions:
            before_path_count = len(final_paths)
            final_paths = self._restrict_to_one_hop_like(
                paths=final_paths,
                seed_names=clean_seed_names,
                max_paths=max(1, cfg.max_graph_paths // 2),
            )
            self._log_debug(
                "KG one-hop restriction applied",
                {
                    "before": before_path_count,
                    "after": len(final_paths),
                },
            )

        # 6) Final context and query placement.
        context_text = self._build_context_text(
            seed_names=clean_seed_names,
            graph_paths=final_paths,
            sources=final_sources,
        )
        user_content = self._compose_user_content(question=question, context=context_text)
        prompt_token_estimate = (
            self._estimate_messages_tokens(history_messages)
            + self._estimate_tokens(user_content)
        )
        self._log_debug(
            "Context orchestration completed",
            {
                "final_sources": len(final_sources),
                "final_paths": len(final_paths),
                "history_messages": len(history_messages),
                "final_prompt_tokens": prompt_token_estimate,
            },
        )

        return ContextPreparationResult(
            context=context_text,
            user_content=user_content,
            history_messages=history_messages,
            sources=final_sources,
            graph_paths=final_paths,
            seed_names=clean_seed_names,
            budget_actions=budget_actions,
            prompt_token_estimate=prompt_token_estimate,
            budget_plan=budget_plan.as_dict(),
        )

    def _build_recent_history_messages(
        self,
        rounds: list[ChatRound],
        max_history_rounds: int,
    ) -> list[MessageRecord]:
        if not rounds:
            return []

        recent = rounds[-max_history_rounds:]
        messages: list[MessageRecord] = []
        for round_item in recent:
            if round_item.question:
                messages.append({"role": "user", "content": round_item.question})
            if round_item.answer:
                messages.append({"role": "assistant", "content": round_item.answer})

        return messages

    def _build_tiered_history_messages(
        self,
        rounds: list[ChatRound],
        hot_size: int,
        warm_size: int,
    ) -> list[MessageRecord]:
        records: list[ConversationRoundRecord] = []
        for item in rounds:
            records.append(
                {
                    "question": item.question,
                    "answer": item.answer,
                    "prompt": item.prompt,
                    "created_at": item.created_at.isoformat(),
                    "fault_tree_id": item.fault_tree_id or "",
                }
            )

        tiering = self._history_tiering.split(
            rounds=records,
            hot_size=hot_size,
            warm_size=warm_size,
        )
        history_text = self._history_tiering.build_history_section(tiering)
        if not history_text:
            return []

        return [{"role": "assistant", "content": f"[Conversation Memory]\n{history_text}"}]

    def _build_context_text(
        self,
        seed_names: list[str],
        graph_paths: list[GraphPath],
        sources: list[ScoredDocument],
    ) -> str:
        parts: list[str] = []

        if seed_names or graph_paths:
            if seed_names:
                parts.append(f"【关联实体】\n{', '.join(seed_names)}")

            if graph_paths:
                path_lines = "\n".join(
                    f"  - {p.get('from', '')} --[{p.get('relation', '关联')}]--> {p.get('to', '')}"
                    for p in graph_paths
                )
                parts.append(f"【知识图谱路径】\n{path_lines}")

        if sources:
            chunk_text = "\n\n".join(
                f"[{s.get('file_name', 'Unknown')}]\n{s.get('page_content', '')}"
                for s in sources
            )
            parts.append(f"【相关原文片段】\n{chunk_text}")

        return "\n\n".join(parts)

    def _compose_user_content(self, question: str, context: str) -> str:
        query_messages = self._query_placement.append_query(
            messages=[],
            user_query=question,
            context_block=context,
        )
        query_messages = self._query_placement.ensure_query_last(query_messages)
        if not query_messages:
            return question

        return str(query_messages[-1].get("content", question))

    def _restrict_to_one_hop_like(
        self,
        paths: list[GraphPath],
        seed_names: list[str],
        max_paths: int,
    ) -> list[GraphPath]:
        if not paths:
            return []

        if not seed_names:
            return paths[:max_paths]

        seed_set = set(seed_names)
        selected: list[GraphPath] = []
        for path in paths:
            source = str(path.get("from", ""))
            target = str(path.get("to", ""))
            if source in seed_set or target in seed_set:
                selected.append(path)

        if not selected:
            return paths[:max_paths]

        return selected[:max_paths]

    def _estimate_messages_tokens(self, messages: list[MessageRecord]) -> int:
        total = 0
        for message in messages:
            total += self._estimate_tokens(str(message.get("content", "")))
        return total

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        normalized = " ".join(text.split())
        if not normalized:
            return 0
        return max(1, len(normalized) // 4)

    def _log_debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        if self._context_logger is None:
            return
        self._context_logger.debug(message, context)
