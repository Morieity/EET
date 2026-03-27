from typing import Protocol


class DiagnosisLlmClient(Protocol):
    """诊断 LLM 客户端接口，封装意图识别、充分性评估和 RAG 增强诊断。"""

    def diagnose(
        self,
        conversation_history: list[dict[str, str]],
        retrieved_context: str,
    ) -> dict:
        """基于对话历史和检索上下文生成诊断回复。

        Returns:
            {"content": str, "intent": str}
        """
        ...

    def classify_intent(self, message: str) -> str:
        """对用户消息进行意图分类。

        Returns:
            "fault_diagnosis" | "off_topic"
        """
        ...

    def assess_sufficiency(
        self,
        conversation_history: list[dict[str, str]],
    ) -> bool:
        """评估当前对话历史是否已积累足够信息以生成故障树。"""
        ...
