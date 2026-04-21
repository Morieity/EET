from collections.abc import Sequence
from typing import Any

from Backend.Application.ContextManagement.ContextTypes import ScoredDocument


class RetrievalReorderingAlgorithm:
    """简要算法说明。

        论文来源:
        - Long-Context LLMs Meet RAG (ICLR 2025, arXiv:2410.05983)
        - Retrieval Head Mechanistically Explains Long-Context Factuality
            (arXiv:2404.15574)

        核心原理:
        - 先按相关性分数对片段降序排序。
        - 再将条目交替放到列表首尾，使高相关证据暴露在提示词边界位置。

        参数含义:
        - documents: 检索片段，预期包含 `score`、`file_name`、`page_content` 等字段。

        结果说明:
        - 返回仅改变顺序、不删除条目的重排列表，便于后续编排进行边界感知的提示词注入。

        证据键:
        - long_context_llms_meet_rag_2024
        - retrieval_head_2024
        """

    def reorder(self, documents: Sequence[ScoredDocument]) -> list[ScoredDocument]:
        """按分数与边界放置策略重排检索片段。

        参数:
            documents: 输入检索片段。

        返回:
            在保留全部输入的前提下仅改变顺序的新列表。
        """
        ranked = sorted((dict(d) for d in documents), key=self._score, reverse=True)
        if len(ranked) <= 2:
            return ranked

        reordered: list[ScoredDocument | None] = [None] * len(ranked)
        left = 0
        right = len(ranked) - 1
        put_left = True

        for doc in ranked:
            if put_left:
                reordered[left] = doc
                left += 1
            else:
                reordered[right] = doc
                right -= 1
            put_left = not put_left

        return [doc for doc in reordered if doc is not None]

    @staticmethod
    def _score(document: dict[str, Any]) -> float:
        try:
            return float(document.get("score", 0.0))
        except (TypeError, ValueError):
            return 0.0
