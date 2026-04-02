from abc import ABC, abstractmethod


class IVectorStoreRepository(ABC):
    @abstractmethod
    def add_documents(self, file_name: str, documents: list) -> None:
        """Add document chunks to the vector store with file_name in metadata."""
        pass

    @abstractmethod
    def delete_by_file_name(self, file_name: str) -> None:
        """Delete all vectors associated with a file_name."""
        pass

    @abstractmethod
    def search(self, query: str, k: int = 5, score_threshold: float = 0.1) -> list[dict]:
        """检索与 query 相关的文档片段，返回 [{file_name, page_content, score}]。"""
        pass
