import logging

from Backend.Application.Chat.ChatConfig import DEFAULT_CONTEXT_CONFIG, MAX_HISTORY_ROUNDS
from Backend.Application.Chat.ChatModels import ChatContextBuildResult, RetrievalResult
from Backend.Application.ContextManagement.ContextManagerTypes import ContextManagerConfig
from Backend.Application.Interfaces.IContextManager import IContextManager
from Backend.Domain.Entities.conversation import ChatRound

logger = logging.getLogger(__name__)


class ChatContextBuilder:
    def __init__(
        self,
        context_manager: IContextManager | None = None,
        context_config: ContextManagerConfig | None = None,
    ):
        self._context_manager = context_manager
        self._context_config = context_config or DEFAULT_CONTEXT_CONFIG

    def build(
        self,
        question: str,
        conversation_rounds: list[ChatRound],
        system_content: str,
        retrieval: RetrievalResult,
    ) -> ChatContextBuildResult:
        context_result = None
        seed_names = retrieval.seed_names
        graph_paths = retrieval.graph_paths
        sources = retrieval.sources

        if self._context_manager:
            try:
                system_prompt_tokens = max(1, len(system_content) // 2)
                context_result = self._context_manager.prepare_context(
                    question=question,
                    conversation_rounds=conversation_rounds,
                    seed_names=seed_names,
                    graph_paths=graph_paths,
                    sources=sources,
                    config=self._context_config,
                    system_prompt_tokens=system_prompt_tokens,
                )
                seed_names = context_result.seed_names
                graph_paths = context_result.graph_paths
                sources = context_result.sources
                context = context_result.context
                logger.debug(
                    "Context prepared: actions=%s, tokens=%s, sources=%d, paths=%d",
                    ",".join(context_result.budget_actions) or "none",
                    context_result.prompt_token_estimate,
                    len(sources),
                    len(graph_paths),
                )
            except Exception:
                logger.exception("Context manager preparation failed, fallback to legacy flow")

        if context_result is None:
            context = self.build_enhanced_context(seed_names, graph_paths, sources)

        messages: list[dict] = [{"role": "system", "content": system_content}]
        if context_result is not None:
            messages.extend(context_result.history_messages)
            user_content = context_result.user_content or question
        else:
            recent_rounds = conversation_rounds[-MAX_HISTORY_ROUNDS:]
            for round_item in recent_rounds:
                messages.append({"role": "user", "content": round_item.question})
                messages.append({"role": "assistant", "content": round_item.answer})
            user_content = f"{question}\n\nContext:\n{context}" if context else question

        messages.append({"role": "user", "content": user_content})

        return ChatContextBuildResult(
            messages=messages,
            user_content=user_content,
            sources=sources,
            seed_names=seed_names,
            graph_paths=graph_paths,
            context=context,
            context_result=context_result,
        )

    @staticmethod
    def build_enhanced_context(
        seed_names: list[str],
        graph_paths: list[dict],
        sources: list[dict],
    ) -> str:
        parts = []

        if seed_names or graph_paths:
            if seed_names:
                parts.append(f"【关联实体】\n{', '.join(seed_names)}")
            if graph_paths:
                path_lines = "\n".join(
                    f"  - {p['from']} --[{p['relation']}]--> {p['to']}"
                    for p in graph_paths[:20]
                )
                parts.append(f"【知识图谱路径】\n{path_lines}")

        if sources:
            chunk_text = "\n\n".join(
                f"[{s.get('file_name', 'Unknown')}]\n{s['page_content']}" for s in sources
            )
            parts.append(f"【相关原文片段】\n{chunk_text}")

        return "\n\n".join(parts)
