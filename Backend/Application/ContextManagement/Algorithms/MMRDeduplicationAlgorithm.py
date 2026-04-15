import re
from collections.abc import Sequence
from typing import Any

from Backend.Application.ContextManagement.ContextTypes import ScoredDocument


class MMRDeduplicationAlgorithm:
    """简要算法说明。

        论文来源:
        - Long-Context LLMs Meet RAG (ICLR 2025, arXiv:2410.05983)

        核心原理:
        - 使用 MMR 风格目标函数平衡相关性与新颖性。
        - 先保留最高分片段，再迭代选择使
            `relevance_weight * relevance - (1 - relevance_weight) * similarity`
            最大的片段。
        - 在 MMR 选择前先执行精确去重。

        参数含义:
        - documents: 输入的检索片段，需包含 score/page_content 等字段。
        - top_k: MMR 选择后最多保留的片段数量。
        - relevance_weight: [0, 1] 区间内的相关性权重。

        结果说明:
        - 返回有序且去重后的片段子集，供后续提示词构建。
        - 输出目标是在保持高相关性的同时降低冗余。

        证据键:
        - long_context_llms_meet_rag_2024
        """

    def select(
        self,
        documents: Sequence[ScoredDocument],
        top_k: int | None = None,
        relevance_weight: float = 0.7,
    ) -> list[ScoredDocument]:
        """使用 MMR 风格重排选择去重片段。

        参数:
            documents: 输入的检索片段。
            top_k: 输出长度上限（可选）。
            relevance_weight: 相关性与新颖性的权衡系数。

        返回:
            经精确去重与 MMR 选择后的有序片段列表。
        """
        if not documents:
            return []

        relevance_weight = max(0.0, min(1.0, relevance_weight))

        deduped = self._deduplicate_exact(documents)
        if not deduped:
            return []

        if top_k is None:
            top_k = len(deduped)
        top_k = max(1, min(top_k, len(deduped)))

        selected: list[ScoredDocument] = []
        remaining = [dict(doc) for doc in deduped]

        first = max(remaining, key=self._score)
        selected.append(first)
        remaining.remove(first)

        while remaining and len(selected) < top_k:
            best_doc = None
            best_value = float("-inf")

            for candidate in remaining:
                relevance = self._score(candidate)
                novelty_penalty = max(
                    self._similarity(candidate, chosen) for chosen in selected
                )
                mmr_value = relevance_weight * relevance - (1.0 - relevance_weight) * novelty_penalty

                if mmr_value > best_value:
                    best_value = mmr_value
                    best_doc = candidate

            if best_doc is None:
                break

            selected.append(best_doc)
            remaining.remove(best_doc)

        return selected

    def _deduplicate_exact(self, documents: Sequence[ScoredDocument]) -> list[ScoredDocument]:
        seen: set[tuple[str, str]] = set()
        unique: list[ScoredDocument] = []

        for doc in documents:
            file_name = str(doc.get("file_name", ""))
            content = str(doc.get("page_content", ""))
            dedup_key = (file_name, content.strip())
            if dedup_key in seen:
                continue

            seen.add(dedup_key)
            unique.append(dict(doc))

        return unique

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
        return set(tokens)

    def _similarity(self, a: dict[str, Any], b: dict[str, Any]) -> float:
        a_text = str(a.get("page_content", ""))
        b_text = str(b.get("page_content", ""))
        a_tokens = self._tokenize(a_text)
        b_tokens = self._tokenize(b_text)
        if not a_tokens or not b_tokens:
            return 0.0

        inter = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        if union == 0:
            return 0.0
        return inter / union

    @staticmethod
    def _score(document: dict[str, Any]) -> float:
        try:
            return float(document.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
