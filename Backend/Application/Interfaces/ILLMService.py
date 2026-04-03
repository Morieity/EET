from abc import ABC, abstractmethod
from collections.abc import Generator


class ILLMService(ABC):
    @abstractmethod
    def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        """流式调用 LLM，逐 token yield 文本内容。

        messages 格式：[{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        pass

    @abstractmethod
    def chat_with_tools(
        self, messages: list[dict], tools: list[dict]
    ) -> dict:
        """调用 LLM 并传入 tools 定义，返回结果。

        返回格式:
          - 普通回复: {"type": "text", "content": "..."}
          - 工具调用: {"type": "tool_call", "name": "...", "arguments": {...}}
        """
        pass
