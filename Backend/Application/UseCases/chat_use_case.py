from Backend.Application.Interfaces.chat_repository import ChatClient


class ChatUseCase:
    def __init__(self, chat_client: ChatClient):
        """使用抽象聊天客户端初始化用例。"""
        self.chat_client = chat_client

    def execute(self, query: str) -> str:
        """校验输入并返回模型响应。"""
        if not query:
            raise ValueError("Query is required")
        return self.chat_client.chat(query)
