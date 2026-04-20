import hashlib
import logging
from pathlib import Path
from langchain_chroma import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository

logger = logging.getLogger(__name__)

# 项目根目录下的模型缓存路径
_MODEL_CACHE_DIR = str(Path(__file__).resolve().parents[3] / "llm_model")


class ChromaVectorStoreRepository(IVectorStoreRepository):
    def __init__(self, persist_directory: str = "db", collection_name: str = "rag_docs"):
        self._embedding = FastEmbedEmbeddings(cache_dir=_MODEL_CACHE_DIR)
        self._persist_directory = persist_directory
        self._collection_name = collection_name

    def _get_store(self) -> Chroma:
        return Chroma(
            persist_directory=self._persist_directory,
            embedding_function=self._embedding,
            collection_name=self._collection_name,
        )

    def _get_entity_store(self) -> Chroma:
        return Chroma(
            persist_directory=self._persist_directory,
            embedding_function=self._embedding,
            collection_name="graph_entities",
        )

    def _get_relation_store(self) -> Chroma:
        return Chroma(
            persist_directory=self._persist_directory,
            embedding_function=self._embedding,
            collection_name="graph_relations",
        )

    # ── 原有 rag_docs 方法 ──────────────────────────

    def add_documents(self, file_name: str, documents: list) -> None:
        for doc in documents:
            doc.metadata["file_name"] = file_name
        store = self._get_store()
        store.add_documents(documents)

    def delete_by_file_name(self, file_name: str) -> None:
        store = self._get_store()
        collection = store._collection
        results = collection.get(where={"file_name": file_name})
        if results["ids"]:
            collection.delete(ids=results["ids"])

    # 对话历史 chunk 的最低相似度阈值（仅 >= 此值才纳入检索结果）
    CONVERSATION_SCORE_THRESHOLD = 0.7

    def search(self, query: str, k: int = 5, score_threshold: float = 0.1) -> list[dict]:
        store = self._get_store()
        results = store.similarity_search_with_relevance_scores(query, k=k)
        filtered: list[dict] = []
        for doc, score in results:
            if score < score_threshold:
                continue
            doc_type = doc.metadata.get("type", "")
            is_conversation = (
                doc_type == "conversation_history"
                or doc.metadata.get("file_name", "").startswith("conversation_")
            )
            # 对话历史要求更高的相似度才纳入，以文档为主
            if is_conversation and score < self.CONVERSATION_SCORE_THRESHOLD:
                continue
            filtered.append(
                {
                    "file_name": doc.metadata.get("file_name", "Unknown"),
                    "page_content": doc.page_content,
                    "score": score,
                    "type": doc_type or ("conversation_history" if is_conversation else "document"),
                }
            )
        return filtered

    # ── graph_entities 方法 ─────────────────────────

    def add_entity(self, name: str, entity_type: str, source_file: str = "") -> None:
        store = self._get_entity_store()
        entity_id = self._entity_id(name)
        collection = store._collection
        existing = collection.get(ids=[entity_id])
        if existing["ids"]:
            # upsert: 更新元数据
            collection.update(
                ids=[entity_id],
                documents=[name],
                metadatas=[{"name": name, "type": entity_type, "source_file": source_file}],
            )
        else:
            collection.add(
                ids=[entity_id],
                documents=[name],
                metadatas=[{"name": name, "type": entity_type, "source_file": source_file}],
            )

    def search_entities(
        self, query: str, top_k: int = 20, score_threshold: float = 0.85
    ) -> list[dict]:
        store = self._get_entity_store()
        try:
            results = store._collection.query(
                query_texts=[query], n_results=top_k, include=["metadatas", "distances"]
            )
        except Exception:
            logger.debug("Entity search failed, collection may be empty")
            return []
        if not results["metadatas"] or not results["metadatas"][0]:
            return []
        # Chroma 返回 L2 距离，转换为相关度分数: score = 1 / (1 + distance)
        filtered: list[dict] = []
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            score = 1.0 / (1.0 + dist)
            if score >= score_threshold:
                filtered.append({**meta, "_score": round(score, 4)})
        return filtered

    def delete_entities_by_file(self, file_name: str) -> None:
        store = self._get_entity_store()
        collection = store._collection
        try:
            results = collection.get(where={"source_file": file_name})
        except Exception:
            return
        if results["ids"]:
            collection.delete(ids=results["ids"])

    # ── graph_relations 方法 ────────────────────────

    def add_relation(self, head: str, relation: str, tail: str, source_file: str = "") -> None:
        store = self._get_relation_store()
        rel_id = self._relation_id(head, relation, tail)
        text = f"{head} {relation} {tail}"
        collection = store._collection
        existing = collection.get(ids=[rel_id])
        if existing["ids"]:
            collection.update(
                ids=[rel_id],
                documents=[text],
                metadatas=[{"head": head, "relation": relation, "tail": tail, "source_file": source_file}],
            )
        else:
            collection.add(
                ids=[rel_id],
                documents=[text],
                metadatas=[{"head": head, "relation": relation, "tail": tail, "source_file": source_file}],
            )

    def search_relations(
        self, query: str, top_k: int = 20, score_threshold: float = 0.5
    ) -> list[dict]:
        store = self._get_relation_store()
        try:
            results = store._collection.query(
                query_texts=[query], n_results=top_k, include=["metadatas", "distances"]
            )
        except Exception:
            logger.debug("Relation search failed, collection may be empty")
            return []
        if not results["metadatas"] or not results["metadatas"][0]:
            return []
        filtered: list[dict] = []
        for meta, dist in zip(results["metadatas"][0], results["distances"][0]):
            score = 1.0 / (1.0 + dist)
            if score >= score_threshold:
                filtered.append({**meta, "_score": round(score, 4)})
        return filtered

    def delete_relations_by_file(self, file_name: str) -> None:
        store = self._get_relation_store()
        collection = store._collection
        try:
            results = collection.get(where={"source_file": file_name})
        except Exception:
            return
        if results["ids"]:
            collection.delete(ids=results["ids"])

    # ── 工具方法 ────────────────────────────────────

    @staticmethod
    def _entity_id(name: str) -> str:
        return "ent_" + hashlib.md5(name.encode()).hexdigest()[:12]

    @staticmethod
    def _relation_id(head: str, relation: str, tail: str) -> str:
        key = f"{head}|{relation}|{tail}"
        return "rel_" + hashlib.md5(key.encode()).hexdigest()[:12]
