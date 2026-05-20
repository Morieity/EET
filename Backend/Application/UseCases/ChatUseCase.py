from collections.abc import Generator
from typing import TYPE_CHECKING

from Backend.Application.Chat.ChatConfig import FaultTreeGenerationConfig
from Backend.Application.Chat.ChatContextBuilder import ChatContextBuilder
from Backend.Application.Chat.ChatConversationService import ChatConversationService
from Backend.Application.Chat.ChatModels import ChatResponseState
from Backend.Application.Chat.ChatPrompts import SYSTEM_PROMPT
from Backend.Application.Chat.ChatStreamingService import ChatStreamingService
from Backend.Application.Chat.FaultTreeChatFlow import FaultTreeChatFlow
from Backend.Application.Chat.FaultTreeIntentDetector import FaultTreeIntentDetector
from Backend.Application.Chat.RagRetrievalService import RagRetrievalService
from Backend.Application.ContextManagement.ContextManagerTypes import ContextManagerConfig
from Backend.Application.Interfaces.IContextManager import IContextManager
from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository
from Backend.Application.Interfaces.ILLMService import ILLMService
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Skills.FaultTreeSkill import FaultTreeSkill

if TYPE_CHECKING:
    from Backend.Application.UseCases.ExpertLearningUseCase import ExpertLearningUseCase


class ChatUseCase:
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        vector_store_repository: IVectorStoreRepository,
        llm_service: ILLMService,
        fault_tree_skill: FaultTreeSkill,
        graph_repository: IGraphRepository | None = None,
        context_manager: IContextManager | None = None,
        context_config: ContextManagerConfig | None = None,
        fault_tree_wait_timeout_seconds: float = 120,
        expert_learning: "ExpertLearningUseCase | None" = None,
    ):
        self._conversation_service = ChatConversationService(conversation_repository)
        self._retrieval_service = RagRetrievalService(
            vector_store_repository=vector_store_repository,
            graph_repository=graph_repository,
        )
        self._context_builder = ChatContextBuilder(
            context_manager=context_manager,
            context_config=context_config,
        )
        self._intent_detector = FaultTreeIntentDetector()
        self._plain_streaming = ChatStreamingService(llm_service)
        self._fault_tree_flow = FaultTreeChatFlow(
            llm_service=llm_service,
            fault_tree_skill=fault_tree_skill,
            config=FaultTreeGenerationConfig(
                wait_timeout_seconds=fault_tree_wait_timeout_seconds,
            ),
        )
        self._fault_tree_skill = fault_tree_skill
        self._expert_learning = expert_learning

    def execute(
        self, question: str, conversation_id: str | None = None
    ) -> Generator[dict, None, None]:
        """执行一轮对话，以 Generator 方式逐步 yield 事件给调用方。

        事件类型:
          - {"type": "conversation", "conversation_id": ..., "name": ...}
          - {"type": "sources", "sources": [...]}
          - {"type": "generating_tree"}
          - {"type": "token", "content": ...}
          - {"type": "fault_tree", "fault_tree": {...}}
          - {"type": "done", "answer": ..., "conversation_id": ...}
          - {"type": "error", "message": ...}
        """
        conversation, error_message = self._conversation_service.get_or_create(
            question=question,
            conversation_id=conversation_id,
        )
        if conversation is None:
            yield {"type": "error", "message": error_message}
            return

        yield self._conversation_service.to_event(conversation)

        retrieval = self._retrieval_service.retrieve(question)
        existing_tree_context = self._fault_tree_skill.get_existing_tree_context(conversation.id)
        system_content = SYSTEM_PROMPT + existing_tree_context
        chat_context = self._context_builder.build(
            question=question,
            conversation_rounds=conversation.rounds,
            system_content=system_content,
            retrieval=retrieval,
        )

        yield {"type": "sources", "sources": chat_context.sources}

        intent = self._intent_detector.detect(question)
        state = ChatResponseState()

        if intent.is_request:
            yield from self._fault_tree_flow.execute(
                question=question,
                conversation_id=conversation.id,
                messages=chat_context.messages,
                system_content=system_content,
                intent=intent,
                state=state,
            )
            if state.error_message:
                self._persist_round(conversation.id, question, chat_context.user_content, state, chat_context.sources)
                yield {"type": "error", "message": state.error_message}
                return
        else:
            yield from self._plain_streaming.stream_plain_chat(chat_context.messages, state)
            if state.error_message:
                yield {"type": "error", "message": state.error_message}
                return

        self._persist_round(conversation.id, question, chat_context.user_content, state, chat_context.sources)

        if self._expert_learning:
            self._expert_learning.index_conversation_round(
                conversation_id=conversation.id,
                question=question,
                answer=state.full_answer,
            )

        done_event = {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": state.full_answer,
        }
        if state.fault_tree_id:
            done_event["fault_tree_id"] = state.fault_tree_id

        yield done_event

    def _persist_round(
        self,
        conversation_id: str,
        question: str,
        prompt: str,
        state: ChatResponseState,
        sources: list[dict],
    ) -> None:
        self._conversation_service.persist_round(
            conversation_id=conversation_id,
            question=question,
            prompt=prompt,
            answer=state.full_answer,
            sources=sources,
            fault_tree_id=state.fault_tree_id,
        )
