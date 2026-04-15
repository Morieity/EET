from dataclasses import dataclass


@dataclass(frozen=True)
class TokenBudgetPlan:
    """提示词各分区的 token 分配结果。

    字段:
    - system: 系统指令预算。
    - kg: 图谱上下文预算。
    - vector: 向量检索片段预算。
    - history: 对话历史预算。
    - query: 当前用户查询预留预算。
    - generation_reserve: 回答生成余量预算。
    """

    system: int
    kg: int
    vector: int
    history: int
    query: int
    generation_reserve: int

    def as_dict(self) -> dict[str, int]:
        return {
            "system": self.system,
            "kg": self.kg,
            "vector": self.vector,
            "history": self.history,
            "query": self.query,
            "generation_reserve": self.generation_reserve,
        }


class TokenBudgetingAlgorithm:
    """简要算法说明。

        论文来源:
        - Long Context vs. RAG for LLMs: An Evaluation and Revisits
            (arXiv:2501.01880)
        - LongLLMLingua (arXiv:2310.06839)
        - Retrieval Head Mechanistically Explains Long-Context Factuality
            (arXiv:2404.15574)

        核心原理:
        - 按固定比例为提示词分区分配 token 预算。
        - 计算运行时利用率并触发分级压缩动作。
        - 按策略将 system/query 分区设为不可压缩。

        参数含义:
        - max_context_tokens: 模型输入的 token 总上限。
        - ratios: 各分区比例的可选覆盖配置。
        - total_prompt_tokens: 生成前运行时提示词 token 用量。

        结果说明:
        - 基于利用率阈值（0.6 / 0.8 / 0.9）生成确定性的预算计划与压缩动作列表。

        证据键:
        - long_context_vs_rag_2024
        - longllmlingua_2023_2024
        - retrieval_head_2024
        """

    DEFAULT_RATIOS = {
        "system": 0.05,
        "kg": 0.20,
        "vector": 0.35,
        "history": 0.25,
        "query": 0.05,
        "generation_reserve": 0.10,
    }

    NON_COMPRESSIBLE_SECTIONS = {"system", "query"}

    def build_plan(
        self,
        max_context_tokens: int,
        ratios: dict[str, float] | None = None,
    ) -> TokenBudgetPlan:
        """根据总上下文上限与比例构建分区预算。

        参数:
            max_context_tokens: 模型上下文窗口总量。
            ratios: 对特定分区比例的可选覆盖。

        返回:
            各分区为整数 token 预算的 `TokenBudgetPlan`。
        """
        if max_context_tokens <= 0:
            raise ValueError("max_context_tokens must be positive")

        active_ratios = dict(self.DEFAULT_RATIOS)
        if ratios:
            active_ratios.update(ratios)

        base = {
            key: int(max_context_tokens * ratio)
            for key, ratio in active_ratios.items()
        }
        assigned = sum(base.values())

        # 将残余 token 追加到 vector 预算，提升检索侧灵活性。
        base["vector"] += max_context_tokens - assigned

        return TokenBudgetPlan(
            system=base["system"],
            kg=base["kg"],
            vector=base["vector"],
            history=base["history"],
            query=base["query"],
            generation_reserve=base["generation_reserve"],
        )

    @staticmethod
    def utilization_rate(total_prompt_tokens: int, max_context_tokens: int) -> float:
        """计算提示词占上下文窗口的利用率。"""
        if max_context_tokens <= 0:
            return 1.0
        return max(0.0, total_prompt_tokens / max_context_tokens)

    def decide_actions(self, total_prompt_tokens: int, max_context_tokens: int) -> list[str]:
        """根据利用率返回分级压缩动作。"""
        utilization = self.utilization_rate(total_prompt_tokens, max_context_tokens)
        actions: list[str] = []

        if utilization > 0.6:
            actions.append("compress_history_tier2")

        if utilization > 0.8:
            actions.extend([
                "compress_history_tier3",
                "compress_vector_docs_keep_50pct",
            ])

        if utilization > 0.9:
            actions.extend([
                "kg_one_hop_only",
                "remove_kg_community_summary",
                "vector_top_k_hard_cap",
            ])

        return actions

    def is_compressible(self, section: str) -> bool:
        """检查指定提示词分区是否允许被压缩。"""
        return section not in self.NON_COMPRESSIBLE_SECTIONS
