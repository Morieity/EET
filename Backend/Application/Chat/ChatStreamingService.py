import logging
from collections.abc import Generator

from Backend.Application.Chat.ChatModels import ChatResponseState
from Backend.Application.Interfaces.ILLMService import ILLMService

logger = logging.getLogger(__name__)


class ChatStreamingService:
    def __init__(self, llm_service: ILLMService):
        self._llm = llm_service

    def stream_plain_chat(
        self,
        messages: list[dict],
        state: ChatResponseState,
    ) -> Generator[dict, None, None]:
        try:
            for token in self._llm.stream_chat(messages):
                state.full_answer += token
                yield {"type": "token", "content": token}
        except Exception:
            logger.exception("LLM stream failed")
            state.error_message = "LLM service error"
