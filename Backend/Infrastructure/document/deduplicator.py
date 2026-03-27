"""三级文档去重器：SHA-256 哈希 → 元数据比对 → 嵌入余弦相似度 > 0.95。"""
import hashlib
from typing import Optional

from langchain_core.documents import Document

from Backend.Application.Interfaces.retriever_repository import RetrieverFactory


class ThreeTierDeduplicator:
    """三级去重策略实现 (R-004)。"""

    def __init__(
        self,
        retriever_factory: RetrieverFactory,
        similarity_threshold: float = 0.95,
    ):
        self._retriever_factory = retriever_factory
        self._similarity_threshold = similarity_threshold

    @staticmethod
    def _hash_content(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def deduplicate(
        self,
        chunks: list[Document],
        existing_hashes: Optional[set[str]] = None,
    ) -> tuple[list[Document], int]:
        """执行三级去重，返回 (保留片段, 去重数量)。"""
        if existing_hashes is None:
            existing_hashes = set()

        unique: list[Document] = []
        removed = 0
        seen_hashes: set[str] = set(existing_hashes)

        for chunk in chunks:
            content = chunk.page_content.strip()
            if not content:
                removed += 1
                continue

            # Level 1: SHA-256 hash dedup
            content_hash = self._hash_content(content)
            if content_hash in seen_hashes:
                removed += 1
                continue

            # Level 2: Metadata dedup (same source + similar position)
            if self._metadata_duplicate(chunk, unique):
                removed += 1
                continue

            # Level 3: Embedding similarity via retriever
            if self._embedding_duplicate(chunk):
                removed += 1
                continue

            seen_hashes.add(content_hash)
            unique.append(chunk)

        return unique, removed

    @staticmethod
    def _metadata_duplicate(chunk: Document, existing: list[Document]) -> bool:
        """Check if a chunk has identical source + page metadata as existing."""
        src = chunk.metadata.get("source", "")
        page = chunk.metadata.get("page")
        for doc in existing:
            if (
                doc.metadata.get("source", "") == src
                and doc.metadata.get("page") == page
                and doc.page_content.strip() == chunk.page_content.strip()
            ):
                return True
        return False

    def _embedding_duplicate(self, chunk: Document) -> bool:
        """Query the vector store for highly similar existing chunks."""
        try:
            retriever = self._retriever_factory.get_retriever(
                k=1,
                score_threshold=self._similarity_threshold,
            )
            results = retriever.invoke(chunk.page_content)
            return len(results) > 0
        except Exception:
            # If vector store is empty or unavailable, treat as non-duplicate
            return False
