import logging

from Backend.Application.Chat.ChatConfig import RagRetrievalConfig
from Backend.Application.Chat.ChatModels import RetrievalResult
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository

logger = logging.getLogger(__name__)


class RagRetrievalService:
    def __init__(
        self,
        vector_store_repository: IVectorStoreRepository,
        graph_repository: IGraphRepository | None = None,
        config: RagRetrievalConfig | None = None,
    ):
        self._vector_store = vector_store_repository
        self._graph_repo = graph_repository
        self._config = config or RagRetrievalConfig()

    def retrieve(self, question: str) -> RetrievalResult:
        seed_names = self._collect_seed_names(question)
        graph_paths = self._expand_graph_paths(seed_names)
        sources = self._retrieve_sources_from_graph(question, graph_paths)
        sources = self._supplement_sources(question, sources)
        return RetrievalResult(
            seed_names=seed_names,
            graph_paths=graph_paths,
            sources=sources,
        )

    def _collect_seed_names(self, question: str) -> list[str]:
        seed_names: list[str] = []
        try:
            entity_results = self._vector_store.search_entities(query=question)
            seed_names = [m.get("name", "") for m in entity_results if m.get("name")]
        except Exception:
            logger.debug("Entity search skipped or failed")

        try:
            relation_results = self._vector_store.search_relations(query=question)
            for rel in relation_results:
                head = rel.get("head", "")
                tail = rel.get("tail", "")
                if head and head not in seed_names:
                    seed_names.append(head)
                if tail and tail not in seed_names:
                    seed_names.append(tail)
        except Exception:
            logger.debug("Relation search skipped or failed")

        return seed_names

    def _expand_graph_paths(self, seed_names: list[str]) -> list[dict]:
        if not seed_names or self._graph_repo is None:
            return []

        try:
            return self._graph_repo.expand_subgraph(
                seed_names,
                hops=self._config.graph_hops,
            )
        except Exception:
            logger.debug("Subgraph expansion failed, falling back to vector-only")
            return []

    def _retrieve_sources_from_graph(self, question: str, graph_paths: list[dict]) -> list[dict]:
        if not graph_paths:
            return []

        source_keys: list[dict] = []
        seen_keys: set[tuple] = set()
        for path in graph_paths:
            source_file = path.get("source_file", "")
            source_chunk_id = path.get("source_chunk_id", "")
            if source_file:
                key = (source_file, source_chunk_id)
                if key not in seen_keys:
                    seen_keys.add(key)
                    source_keys.append({"file_name": source_file, "chunk_index": source_chunk_id})

        if not source_keys:
            return []

        try:
            return self._vector_store.search_by_sources(
                source_keys=source_keys,
                query=question,
                k=self._config.max_sources,
            )
        except Exception:
            logger.debug("Graph-guided chunk retrieval failed")
            return []

    def _supplement_sources(self, question: str, sources: list[dict]) -> list[dict]:
        if len(sources) >= self._config.graph_min_sources:
            return sources

        try:
            fallback_k = self._config.max_sources - len(sources)
            if fallback_k <= 0:
                return sources

            fallback_sources = self._vector_store.search(
                query=question,
                k=fallback_k,
                score_threshold=self._config.fallback_score_threshold,
            )
            existing_contents = {
                (s.get("file_name", ""), s.get("page_content", "")) for s in sources
            }
            for fallback_source in fallback_sources:
                key = (
                    fallback_source.get("file_name", ""),
                    fallback_source.get("page_content", ""),
                )
                if key not in existing_contents:
                    sources.append(fallback_source)
                    existing_contents.add(key)
        except Exception:
            logger.exception("Vector store fallback search failed")

        return sources
