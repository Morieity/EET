import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


class DeepSeekChatProvider:
    """提供可复用的 DeepSeek ChatOpenAI 客户端。"""

    def __init__(self, temperature: float = 0.7):
        """根据环境变量创建兼容 DeepSeek 的模型客户端。"""
        load_dotenv()
        self._client = ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
            temperature=temperature,
        )

    @property
    def client(self) -> ChatOpenAI:
        """返回已配置的底层聊天客户端。"""
        return self._client

    def chat(self, query: str) -> str:
        """使用纯文本问题调用模型并返回回答内容。"""
        response = self._client.invoke(query)
        return response.content

    def stream_chat(self, query: str):
        """流式返回模型回答内容。"""
        for chunk in self._client.stream(query):
            yield chunk.content
