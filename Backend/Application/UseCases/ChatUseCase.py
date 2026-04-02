import logging
from collections.abc import Generator
from Backend.Domain.Entities.conversation import Conversation, ChatRound
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.ILLMService import ILLMService

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant good at answering questions based on the provided documents. "
    "If the provided context does not contain enough information to answer, say so honestly."
)

MAX_HISTORY_ROUNDS = 10


class ChatUseCase:
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        vector_store_repository: IVectorStoreRepository,
        llm_service: ILLMService,
    ):
        self._conversation_repo = conversation_repository
        self._vector_store = vector_store_repository
        self._llm = llm_service

    def execute(
        self, question: str, conversation_id: str | None = None
    ) -> Generator[dict, None, None]:
        """执行一轮对话，以 Generator 方式逐步 yield 事件给调用方。

        事件类型:
          - {"type": "conversation", "conversation_id": ..., "name": ...}
          - {"type": "sources", "sources": [...]}
          - {"type": "token", "content": ...}
          - {"type": "done", "answer": ..., "conversation_id": ...}
          - {"type": "error", "message": ...}
        """
        # 1. 获取或创建对话
        if conversation_id:
            conversation = self._conversation_repo.get_by_id(conversation_id)
            if conversation is None:
                yield {"type": "error", "message": f"Conversation not found: {conversation_id}"}
                return
        else:
            name = question[:30] if len(question) > 30 else question
            conversation = Conversation(name=name)
            self._conversation_repo.save(conversation)
            logger.info("New conversation created: %s", conversation.id)

        yield {
            "type": "conversation",
            "conversation_id": conversation.id,
            "name": conversation.name,
        }

        # 2. 从向量库检索相关文档
        try:
            sources = self._vector_store.search(query=question, k=5, score_threshold=0.1)
        except Exception:
            logger.exception("Vector store search failed")
            sources = []

        yield {"type": "sources", "sources": sources}

        # 3. 构建 messages（system + context + 历史 + 当前问题）
        context = "\n\n".join(
            [f"[{s.get('file_name', 'Unknown')}]\n{s['page_content']}" for s in sources]
        )

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 加入最近 N 轮历史对话
        recent_rounds = conversation.rounds[-MAX_HISTORY_ROUNDS:]
        for r in recent_rounds:
            messages.append({"role": "user", "content": r.question})
            messages.append({"role": "assistant", "content": r.answer})

        # 当前问题拼接检索上下文
        if context:
            user_content = f"{question}\n\nContext:\n{context}"
        else:
            user_content = question

        messages.append({"role": "user", "content": user_content})

        # 4. 流式调用 LLM
        full_answer = ""
        try:
            for token in self._llm.stream_chat(messages):
                full_answer += token
                yield {"type": "token", "content": token}
        except Exception:
            logger.exception("LLM stream failed")
            yield {"type": "error", "message": "LLM service error"}
            return

        # 5. 保存这一轮对话到数据库
        chat_round = ChatRound(
            question=question,
            prompt=user_content,
            answer=full_answer,
            sources=sources,
        )
        self._conversation_repo.add_round(conversation.id, chat_round)
        logger.info("Chat round saved for conversation: %s", conversation.id)

        yield {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": full_answer,
        }
