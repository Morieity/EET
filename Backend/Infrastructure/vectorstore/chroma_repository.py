from typing import Iterable
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings


class ChromaVectorStoreRepository:
    """处理 Chroma 向量库的读写操作。"""

    def __init__(self, persist_directory: str, embedding: FastEmbedEmbeddings):
        """保存向量持久化与检索所需的仓储配置。"""
        self.persist_directory = persist_directory
        self.embedding = embedding

    def get_retriever(self, k: int = 20, score_threshold: float = 0.1):
        """创建基于相似度阈值策略的检索器。"""
        vector_store = Chroma(
            persist_directory=self.persist_directory,
            embedding_function=self.embedding,
        )
        return vector_store.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": k, "score_threshold": score_threshold},
        )

    def persist_documents(self, chunks: Iterable[Document]) -> None:
        """将文档切片写入 Chroma，供后续检索使用。"""
        vector_store = Chroma.from_documents(
            documents=list(chunks),
            embedding=self.embedding,
            persist_directory=self.persist_directory,
        )
        vector_store.persist()
