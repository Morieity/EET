from typing import Protocol


class ChatClient(Protocol):
    """聊天客户端接口，用于与 LLM 交互。"""

    def chat(self, query: str) -> str:
        """将用户问题发送到模型后端并返回纯文本结果。"""
        ...
