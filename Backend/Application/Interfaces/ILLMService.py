from abc import ABC, abstractmethod
from collections.abc import Generator


class ILLMService(ABC):
    @abstractmethod
    def stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        """流式调用 LLM，逐 token yield 文本内容。

        messages 格式：[{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        pass
