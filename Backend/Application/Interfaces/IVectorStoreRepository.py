from abc import ABC, abstractmethod


class IVectorStoreRepository(ABC):
    """向量存储仓储接口，定义文档、实体、关系的向量化存储和检索操作。"""

    # ── 文档操作 ──────────────────────────────────────

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

    @abstractmethod
    def search_by_sources(
        self, source_keys: list[dict], query: str, k: int = 15
    ) -> list[dict]:
        """根据 source_file + chunk_index 精确检索切片，并用 query 做相关度排序。
        source_keys: [{"file_name": str, "chunk_index": str}, ...]
        返回: [{file_name, page_content, score, type}]
        """
        pass

    # ── 实体操作 ──────────────────────────────────────

    @abstractmethod
    def add_entity(self, name: str, entity_type: str, source_file: str = "") -> None:
        """添加或更新实体到向量存储。"""
        pass

    @abstractmethod
    def search_entities(
        self, query: str, top_k: int = 20, score_threshold: float = 0.85
    ) -> list[dict]:
        """检索与 query 相关的实体，返回 [{name, type, source_file, _score}]。"""
        pass

    @abstractmethod
    def delete_entities_by_file(self, file_name: str) -> None:
        """删除指定文件关联的所有实体。"""
        pass

    # ── 关系操作 ──────────────────────────────────────

    @abstractmethod
    def add_relation(
        self, head: str, relation: str, tail: str, source_file: str = ""
    ) -> None:
        """添加或更新关系三元组到向量存储。"""
        pass

    @abstractmethod
    def search_relations(
        self, query: str, top_k: int = 20, score_threshold: float = 0.5
    ) -> list[dict]:
        """检索与 query 相关的关系，返回 [{head, relation, tail, source_file, _score}]。"""
        pass

    @abstractmethod
    def delete_relations_by_file(self, file_name: str) -> None:
        """删除指定文件关联的所有关系。"""
        pass
