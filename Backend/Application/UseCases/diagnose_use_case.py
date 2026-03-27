"""DiagnoseUseCase — 多轮诊断对话。

加载会话 → 校验会话状态 → RAG 检索 → LLM 回复（含对话历史）→
意图识别 → 充分性评估 → 持久化。
"""
from Backend.Application.Interfaces.diagnosis_llm_client import DiagnosisLlmClient
from Backend.Application.Interfaces.fault_tree_skill import FaultTreeGenerationSkill
from Backend.Application.Interfaces.retriever_repository import RetrieverFactory
from Backend.Application.Interfaces.session_repository import SessionRepository
from Backend.Domain.Common.Enums.message_role import MessageRole
from Backend.Domain.Common.Enums.session_status import SessionStatus


class DiagnoseUseCase:
    def __init__(
        self,
        session_repository: SessionRepository,
        diagnosis_llm: DiagnosisLlmClient,
        retriever_factory: RetrieverFactory,
        fault_tree_skill: FaultTreeGenerationSkill,
    ):
        self._session_repo = session_repository
        self._llm = diagnosis_llm
        self._retriever = retriever_factory
        self._fault_tree_skill = fault_tree_skill

    def execute(self, session_id: str, message: str) -> dict:
        if not message or not message.strip():
            raise ValueError("message MUST NOT be empty")

        # 1. 加载会话
        session = self._session_repo.find_by_id(session_id)
        if session is None:
            raise LookupError("Session not found")

        # 2. 已完成会话不再接受新消息
        if session.status == SessionStatus.COMPLETED:
            raise PermissionError("Session is already completed")

        # 3. 意图识别
        intent = self._llm.classify_intent(message)

        # 4. 追加用户消息
        session.add_message(MessageRole.USER, message)

        # 构建完整对话历史
        history = [
            {"role": m.role.value, "content": m.content}
            for m in session.messages
        ]

        # 5. 对于非诊断意图，直接返回引导消息
        if intent == "off_topic":
            off_topic_reply = (
                "我是故障诊断助手，专注于帮助您分析设备故障。"
                "请描述您遇到的设备问题，我会帮您进行诊断。"
            )
            session.add_message(MessageRole.ASSISTANT, off_topic_reply)
            self._session_repo.save(session)
            return {
                "session_id": session.id,
                "status": session.status.value,
                "reply": {
                    "role": "assistant",
                    "content": off_topic_reply,
                    "intent": "off_topic",
                },
                "sources": [],
                "diagnosis_sufficient": False,
            }

        # 6. RAG 检索
        context = self._retrieve_context(message)

        # 7. LLM 诊断回复
        reply = self._llm.diagnose(history, context)

        # 8. 充分性评估
        sufficient = self._llm.assess_sufficiency(history)

        # 9. 如果充分，尝试用 Skill 生成故障树
        fault_tree_data = None
        if sufficient:
            fault_tree = self._fault_tree_skill.generate(session)
            if fault_tree is not None:
                session.link_fault_tree(fault_tree.id)
                fault_tree_data = fault_tree.to_dict()
                fault_tree_data["id"] = fault_tree.id
                fault_tree_data["name"] = fault_tree.name
                reply["content"] += (
                    "\n\n根据目前收集的信息，我已经对故障原因有了较全面的了解，"
                    "已为您生成故障树进行结构化分析。"
                )
                reply["intent"] = "fault_tree_generated"
            else:
                # Skill 信息不足，返回追问建议
                missing = self._fault_tree_skill.get_missing_info(session)
                if missing:
                    reply["content"] += "\n\n" + "\n".join(missing)
                reply["content"] += (
                    "\n\n根据目前收集的信息，我已经对故障原因有了较全面的了解。"
                    "建议现在生成故障树进行结构化分析。是否需要我为您生成故障树？"
                )
                reply["intent"] = "suggest_fault_tree"

        # 10. 追加 assistant 回复
        session.add_message(MessageRole.ASSISTANT, reply["content"])

        # 11. 持久化
        self._session_repo.save(session)

        # 收集 sources
        sources = self._get_sources(message)

        return {
            "session_id": session.id,
            "status": session.status.value,
            "reply": {
                "role": "assistant",
                "content": reply["content"],
                "intent": reply.get("intent", "fault_diagnosis"),
            },
            "sources": sources,
            "diagnosis_sufficient": sufficient,
            "fault_tree": fault_tree_data,
        }

    def _retrieve_context(self, query: str) -> str:
        try:
            retriever = self._retriever.get_retriever(k=10, score_threshold=0.1)
            docs = retriever.invoke(query)
            if not docs:
                return ""
            return "\n\n".join(
                f"Document: {d.metadata.get('source', 'Unknown')}\n{d.page_content}"
                for d in docs
            )
        except Exception:
            return ""

    def _get_sources(self, query: str) -> list[dict]:
        try:
            retriever = self._retriever.get_retriever(k=5, score_threshold=0.1)
            docs = retriever.invoke(query)
            return [
                {"source": d.metadata.get("source", "Unknown"), "page_content": d.page_content}
                for d in docs
            ]
        except Exception:
            return []
