"""CreateSessionUseCase — 创建诊断会话并执行首轮 RAG 诊断。"""
from Backend.Application.Interfaces.diagnosis_llm_client import DiagnosisLlmClient
from Backend.Application.Interfaces.retriever_repository import RetrieverFactory
from Backend.Application.Interfaces.session_repository import SessionRepository
from Backend.Domain.Common.Enums.message_role import MessageRole
from Backend.Domain.Entities.diagnosis_session import DiagnosisSession


class CreateSessionUseCase:
    def __init__(
        self,
        session_repository: SessionRepository,
        diagnosis_llm: DiagnosisLlmClient,
        retriever_factory: RetrieverFactory,
    ):
        self._session_repo = session_repository
        self._llm = diagnosis_llm
        self._retriever = retriever_factory

    def execute(self, initial_message: str) -> dict:
        if not initial_message or not initial_message.strip():
            raise ValueError("initial_message MUST NOT be empty")

        # 创建会话
        session = DiagnosisSession.create()
        session.add_message(MessageRole.USER, initial_message)

        # RAG 检索
        context = self._retrieve_context(initial_message)

        # 构建对话历史
        history = [{"role": "user", "content": initial_message}]

        # LLM 诊断
        reply = self._llm.diagnose(history, context)

        # 追加 assistant 回复
        session.add_message(MessageRole.ASSISTANT, reply["content"])

        # 持久化
        self._session_repo.save(session)

        return {
            "session_id": session.id,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "reply": {
                "role": "assistant",
                "content": reply["content"],
                "intent": reply.get("intent", "fault_diagnosis"),
            },
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
