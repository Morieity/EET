from typing import Protocol, List
from langchain_core.documents import Document


class Retriever(Protocol):
    """文档检索器接口，用于从向量库中检索相关文档。"""

    def invoke(self, query: str) -> List[Document]:
        """返回与用户问题相关的文档列表。"""
        ...


class RetrieverFactory(Protocol):
    """检索器工厂接口，用于创建配置化的检索器实例。"""

    def get_retriever(self, k: int = 20, score_threshold: float = 0.1) -> Retriever:
        """返回带有仓储默认配置的检索器实例。"""
        ...
