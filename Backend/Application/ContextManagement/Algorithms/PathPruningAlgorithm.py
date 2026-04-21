from collections.abc import Sequence
from typing import Any

from Backend.Application.ContextManagement.ContextTypes import GraphPath


class PathPruningAlgorithm:
    """简要算法说明。

        论文来源:
        - From Local to Global: A Graph RAG Approach to Query-Focused Summarization
            (arXiv:2404.16130)
        - PathRAG: Pruning Graph-based RAG with Relational Paths
            (arXiv:2502.14902)

        核心原理:
        - 使用置信度阈值过滤低质量图路径。
        - 移除完全重复的三元组。
        - 在按置信度补齐前优先保证关系类型多样性。

        参数含义:
        - paths: 图路径候选（`from`、`relation`、`to`，可选 score）。
        - min_confidence: [0, 1] 区间内的路径质量下限。
        - max_paths: 输出路径数量上限。
        - relation_diversity: 是否优先保证关系类型多样性。

        结果说明:
        - 返回更紧凑、更干净的路径列表用于知识图谱上下文注入。
        - 输出路径在可用时会包含归一化后的置信度。

        证据键:
        - graphrag_local_to_global_2024
        - pathrag_2025
        """

    def prune(
        self,
        paths: Sequence[GraphPath],
        min_confidence: float = 0.4,
        max_paths: int = 20,
        relation_diversity: bool = True,
    ) -> list[GraphPath]:
        """基于置信度、去重与多样性对图路径进行裁剪。

        参数:
            paths: 图路径候选集合。
            min_confidence: 允许的最小置信度。
            max_paths: 输出路径最大数量。
            relation_diversity: 是否启用关系类型优先选择。

        返回:
            经过裁剪并排序后可用于提示词上下文的图路径。
        """
        if not paths:
            return []

        min_confidence = max(0.0, min(1.0, min_confidence))
        max_paths = max(1, max_paths)

        filtered: list[GraphPath] = []
        seen_triplets: set[tuple[str, str, str]] = set()

        for raw in paths:
            item = dict(raw)
            source = str(item.get("from", ""))
            relation = str(item.get("relation", ""))
            target = str(item.get("to", ""))

            if not source or not relation or not target:
                continue

            triplet = (source, relation, target)
            if triplet in seen_triplets:
                continue
            seen_triplets.add(triplet)

            confidence = self._confidence(item)
            if confidence < min_confidence:
                continue

            item["confidence"] = confidence
            filtered.append(item)

        filtered.sort(key=self._confidence, reverse=True)

        if not relation_diversity:
            return filtered[:max_paths]

        diverse = self._diversity_first(filtered, max_paths=max_paths)
        return diverse[:max_paths]

    def _diversity_first(self, paths: list[GraphPath], max_paths: int) -> list[GraphPath]:
        by_relation: dict[str, list[GraphPath]] = {}
        for p in paths:
            rel = str(p.get("relation", ""))
            by_relation.setdefault(rel, []).append(p)

        selected: list[GraphPath] = []

        # 第一轮：每种关系类型保留一个最佳候选。
        for rel in sorted(by_relation.keys()):
            selected.append(by_relation[rel][0])
            if len(selected) >= max_paths:
                return selected

        # 第二轮：按全局剩余置信度顺序继续补齐。
        selected_keys = {
            (str(p.get("from", "")), str(p.get("relation", "")), str(p.get("to", "")))
            for p in selected
        }
        for p in paths:
            key = (str(p.get("from", "")), str(p.get("relation", "")), str(p.get("to", "")))
            if key in selected_keys:
                continue
            selected.append(p)
            if len(selected) >= max_paths:
                break

        return selected

    @staticmethod
    def _confidence(path: dict[str, Any]) -> float:
        for key in ("confidence", "score", "weight"):
            if key in path:
                try:
                    return max(0.0, min(1.0, float(path[key])))
                except (TypeError, ValueError):
                    continue
        return 0.5
