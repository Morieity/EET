import os
import logging
from collections.abc import Generator
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from Backend.Application.Interfaces.ILLMService import ILLMService

load_dotenv()

logger = logging.getLogger(__name__)

_ROLE_MAP = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


class LLMService(ILLMService):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.7,
    ):
        self._llm = ChatOpenAI(
            model=model or os.getenv("LLM_MODEL", "deepseek-chat"),
            api_key=api_key or os.getenv("LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            temperature=temperature,
            streaming=True,
        )

    def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        lc_messages = []
        for msg in messages:
            cls = _ROLE_MAP.get(msg["role"], HumanMessage)
            lc_messages.append(cls(content=msg["content"]))

        for chunk in self._llm.stream(lc_messages):
            if chunk.content:
                yield chunk.content
