from dataclasses import dataclass
from typing import Any

from Backend.Application.ContextManagement.ContextTypes import ConversationRoundRecord


@dataclass(frozen=True)
class HistoryTieringResult:
    """三层历史表示。

    字段:
    - hot_rounds: 作为原始文本保留的最近轮次。
    - warm_summary: 中期轮次的精炼摘要。
    - cold_summary: 早期轮次的粗粒度摘要。
    """

    hot_rounds: list[ConversationRoundRecord]
    warm_summary: str
    cold_summary: str


class HistoryTieringAlgorithm:
    """简要算法说明。

        论文来源:
        - MemAgent (arXiv:2507.02259)
        - Long Context vs. RAG for LLMs (arXiv:2501.01880)

        核心原理:
        - 将时效性强的轮次以原始上下文保留（热层）。
        - 将中间轮次压缩为精炼摘要（温层）。
        - 将较早轮次压缩为粗粒度记忆要点（冷层）。

        参数含义:
        - rounds: 按时间顺序排列的对话轮次。
        - hot_size: 原样保留的最新轮次数。
        - warm_size: 热层之前需要汇总为温层的轮次数。

        结果说明:
        - 产出 `HistoryTieringResult` 对象与可渲染的历史片段，
            在上下文连续性与 token 控制之间取得平衡。

        证据键:
        - memagent_2025
        - long_context_vs_rag_2024
        """

    # 工业/故障诊断领域的关键词汇
    # 用于在摘要时优先保留包含这些词的对话
    INDUSTRIAL_KEY_TERMS = {
        "故障", "现象", "原因", "解决", "方案", "诊断", "排查",
        "错误", "异常", "问题", "症状", "分析", "根本",
        "故障树", "故障分析", "故障现象", "解决方案",
    }

    def split(
        self,
        rounds: list[ConversationRoundRecord],
        hot_size: int = 3,
        warm_size: int = 7,
    ) -> HistoryTieringResult:
        """将历史拆分为冷/温/热三层。

        参数:
            rounds: 按时间顺序的对话轮次。
            hot_size: 尾部原样保留的轮次数。
            warm_size: 位于热层之前、用于摘要的轮次数。

        返回:
            包含三层表示的 `HistoryTieringResult`。
        """
        if not rounds:
            return HistoryTieringResult(hot_rounds=[], warm_summary="", cold_summary="")

        total = len(rounds)
        hot_start = max(0, total - hot_size)
        warm_start = max(0, hot_start - warm_size)

        cold_rounds = rounds[:warm_start]
        warm_rounds = rounds[warm_start:hot_start]
        hot_rounds = rounds[hot_start:]

        return HistoryTieringResult(
            hot_rounds=[dict(r) for r in hot_rounds],
            warm_summary=self._summarize_warm_rounds(warm_rounds),
            cold_summary=self._summarize_cold_rounds(cold_rounds),
        )

    def build_history_section(self, tiering: HistoryTieringResult) -> str:
        """根据分层结果渲染文本历史块。"""
        parts: list[str] = []

        if tiering.cold_summary:
            parts.append("[Cold Memory Summary]\n" + tiering.cold_summary)

        if tiering.warm_summary:
            parts.append("[Warm Memory Summary]\n" + tiering.warm_summary)

        if tiering.hot_rounds:
            hot_lines = []
            for turn in tiering.hot_rounds:
                question = self._trim(str(turn.get("question", "")), limit=240)
                answer = self._trim(str(turn.get("answer", "")), limit=320)
                hot_lines.append(f"User: {question}\nAssistant: {answer}")
            parts.append("[Hot Turns]\n" + "\n\n".join(hot_lines))

        return "\n\n".join(parts)

    def _summarize_warm_rounds(self, rounds: list[ConversationRoundRecord]) -> str:
        if not rounds:
            return ""

        # ① 先按是否包含关键词排序（优先保留关键话题）
        scored_rounds = []
        for turn in rounds:
            question = str(turn.get("question", ""))
            answer = str(turn.get("answer", ""))
            combined = (question + answer).lower()
            
            # 计算关键词匹配数
            key_term_count = sum(1 for term in self.INDUSTRIAL_KEY_TERMS if term in combined)
            scored_rounds.append((key_term_count, turn))
        
        # ② 按关键词数量排序（降序）
        scored_rounds.sort(key=lambda x: x[0], reverse=True)
        
        # ③ 优先保留TOP轮次作为摘要
        bullets: list[str] = []
        for _, turn in scored_rounds[:5]:  # 最多5个要点
            question = self._trim(str(turn.get("question", "")), limit=120)
            answer = self._trim(str(turn.get("answer", "")), limit=150)
            if question or answer:
                bullets.append(f"- Q: {question} | A: {answer}")

        return "\n".join(bullets)

    def _summarize_cold_rounds(self, rounds: list[ConversationRoundRecord]) -> str:
        if not rounds:
            return ""

        # ① 一次性扫描，找包含关键词的问题
        key_questions = []
        for r in rounds:
            question = str(r.get("question", ""))
            combined = question.lower()
            key_term_count = sum(1 for term in self.INDUSTRIAL_KEY_TERMS if term in combined)
            
            if key_term_count > 0:  # 只保留包含关键词的问题
                key_questions.append((key_term_count, question))
        
        # ② 按关键词数量排序，取TOP问题
        key_questions.sort(key=lambda x: x[0], reverse=True)
        top_questions = [q for _, q in key_questions[:5]]  # 最多5个
        
        # ③ 如果没有关键词问题，看看能采样多少
        if not top_questions:
            all_questions = [self._trim(str(r.get("question", "")), limit=100) for r in rounds]
            all_questions = [q for q in all_questions if q]
            sample = all_questions[-5:] if all_questions else []
        else:
            sample = [self._trim(q, limit=100) for q in top_questions]
        
        if not sample:
            return ""

        return "- Historical focus: " + " ; ".join(sample)

    @staticmethod
    def _trim(text: str, limit: int) -> str:
        stripped = " ".join(text.split())
        if len(stripped) <= limit:
            return stripped
        return stripped[: limit - 3] + "..."

    @staticmethod
    def estimate_round_tokens(turn: dict[str, Any]) -> int:
        """按字符数粗略估算单轮对话的 token。"""
        question = str(turn.get("question", ""))
        answer = str(turn.get("answer", ""))
        return max(1, (len(question) + len(answer)) // 4)
