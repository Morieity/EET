from typing import Protocol


class ChatClient(Protocol):
    def chat(self, query: str) -> str:
        """将用户问题发送到模型后端并返回纯文本结果。"""
        ...


class ChatUseCase:
    def __init__(self, chat_client: ChatClient):
        """使用抽象聊天客户端初始化用例。"""
        self.chat_client = chat_client

    def execute(self, query: str) -> str:
        """校验输入并返回模型响应。"""
        if not query:
            raise ValueError("Query is required")
        return self.chat_client.chat(query)
