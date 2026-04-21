import os
import json
import logging
from collections.abc import Generator
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
)
from Backend.Application.Interfaces.ILLMService import ILLMService

load_dotenv()

logger = logging.getLogger(__name__)

_ROLE_MAP = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
    "tool": ToolMessage,
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
            max_retries=3,
            request_timeout=60,
        )

    def _to_lc_messages(self, messages: list[dict]):
        lc_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg.get("content") or ""

            if role == "assistant" and msg.get("tool_calls"):
                # Assistant message with tool_calls: build AIMessage with tool_calls
                tool_calls = []
                for tc in msg["tool_calls"]:
                    tool_calls.append({
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "args": json.loads(tc["function"]["arguments"])
                        if isinstance(tc["function"]["arguments"], str)
                        else tc["function"]["arguments"],
                    })
                lc_messages.append(AIMessage(content=content, tool_calls=tool_calls))
            elif role == "tool":
                lc_messages.append(ToolMessage(
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                ))
            else:
                cls = _ROLE_MAP.get(role, HumanMessage)
                lc_messages.append(cls(content=content))
        return lc_messages

    def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        lc_messages = self._to_lc_messages(messages)

        for chunk in self._llm.stream(lc_messages):
            if chunk.content:
                yield chunk.content

    def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> dict:
        lc_messages = self._to_lc_messages(messages)
        # Force the model to return a tool call for deterministic fault-tree flow.
        llm_with_tools = self._llm.bind_tools(tools, tool_choice="required")
        response = llm_with_tools.invoke(lc_messages)

        if response.tool_calls:
            tool_call = response.tool_calls[0]
            return {
                "type": "tool_call",
                "name": tool_call["name"],
                "arguments": tool_call["args"],
            }
        else:
            return {
                "type": "text",
                "content": response.content or "",
            }
