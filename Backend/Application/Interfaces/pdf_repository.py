from typing import Protocol
from langchain_core.documents import Document


class PdfLoader(Protocol):
    """PDF 加载器接口，用于解析 PDF 文件。"""

    def __call__(self, path: str) -> list[Document]:
        """加载 PDF 路径并返回解析后的文档。"""
        ...


class TextSplitter(Protocol):
    """文本分割器接口，用于将文档切分为可用于向量化的片段。"""

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """将文档切分为可用于向量化的更小片段。"""
        ...


class VectorStoreRepository(Protocol):
    """向量数据库仓库接口，用于管理和持久化文档向量。"""

    def persist_documents(self, chunks: list[Document]) -> None:
        """将文档切片向量持久化到存储中。"""
        ...
