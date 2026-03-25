"""DiagnosisLlmAdapter — DeepSeek 实现意图识别、充分性评估与 RAG 增强诊断。"""
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


class DiagnosisLlmAdapter:
    """使用 DeepSeek 作为底层 LLM 的诊断适配器。"""

    def __init__(self, llm: ChatOpenAI):
        self._llm = llm

    # ------------------------------------------------------------------
    # diagnose: RAG 增强诊断对话
    # ------------------------------------------------------------------

    _DIAGNOSIS_PROMPT = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一名专业的设备故障诊断助手。根据以下知识库上下文和对话历史，"
            "帮助用户逐步定位故障原因。如果知识库中没有相关信息，明确告知用户。\n"
            "生成引导性追问，帮助用户补充故障细节（如故障时间、部位、伴随现象等）。\n\n"
            "知识库上下文:\n{context}\n\n"
            "要求：\n"
            "1. 回复内容必须与设备故障诊断相关\n"
            "2. 如果知识库有相关信息，引用并结合分析\n"
            "3. 如果信息不足，提出 2-3 个有针对性的追问\n"
            "4. 回复简洁专业，避免冗余\n"
        ),
        *[("placeholder", "{history}")],
        ("human", "{input}"),
    ])

    def diagnose(
        self,
        conversation_history: list[dict[str, str]],
        retrieved_context: str,
    ) -> dict:
        history_messages = []
        for msg in conversation_history[:-1]:  # Exclude current message
            role = msg["role"]
            if role == "user":
                history_messages.append(("human", msg["content"]))
            else:
                history_messages.append(("ai", msg["content"]))

        current_input = ""
        if conversation_history:
            current_input = conversation_history[-1]["content"]

        chain = self._DIAGNOSIS_PROMPT | self._llm
        result = chain.invoke({
            "context": retrieved_context or "（知识库中未找到相关内容）",
            "history": history_messages,
            "input": current_input,
        })

        return {
            "content": result.content,
            "intent": "fault_diagnosis",
        }

    # ------------------------------------------------------------------
    # classify_intent: 意图识别
    # ------------------------------------------------------------------

    _INTENT_PROMPT = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个意图分类器。判断用户消息是否属于设备故障诊断场景。\n"
            "只返回一个 JSON 对象: {{\"intent\": \"fault_diagnosis\"}} 或 {{\"intent\": \"off_topic\"}}\n"
            "不要输出其他任何内容。\n\n"
            "设备故障诊断相关的话题包括：设备异常、温度升高、振动、噪音、"
            "故障现象描述、维修历史、设备运行状态等。",
        ),
        ("human", "{message}"),
    ])

    def classify_intent(self, message: str) -> str:
        chain = self._INTENT_PROMPT | self._llm
        result = chain.invoke({"message": message})
        try:
            parsed = json.loads(result.content.strip())
            intent = parsed.get("intent", "off_topic")
            if intent in ("fault_diagnosis", "off_topic"):
                return intent
        except (json.JSONDecodeError, AttributeError):
            pass
        return "off_topic"

    # ------------------------------------------------------------------
    # assess_sufficiency: 信息充分性评估
    # ------------------------------------------------------------------

    _SUFFICIENCY_PROMPT = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一个故障诊断信息充分性评估器。根据以下对话历史，判断是否已积累"
            "了足够的信息来生成故障树。\n\n"
            "足够的信息通常包括：\n"
            "1. 明确的故障现象描述\n"
            "2. 故障发生的设备/部位\n"
            "3. 至少 2-3 个可能的故障原因被讨论\n"
            "4. 经过至少 3 轮左右的对话交互\n\n"
            "只返回一个 JSON 对象: {{\"sufficient\": true}} 或 {{\"sufficient\": false}}\n"
            "不要输出其他任何内容。",
        ),
        ("human", "对话历史:\n{history_text}"),
    ])

    def assess_sufficiency(
        self,
        conversation_history: list[dict[str, str]],
    ) -> bool:
        if len(conversation_history) < 4:
            return False

        history_text = "\n".join(
            f"[{m['role']}]: {m['content']}" for m in conversation_history
        )
        chain = self._SUFFICIENCY_PROMPT | self._llm
        result = chain.invoke({"history_text": history_text})
        try:
            parsed = json.loads(result.content.strip())
            return bool(parsed.get("sufficient", False))
        except (json.JSONDecodeError, AttributeError):
            return False
