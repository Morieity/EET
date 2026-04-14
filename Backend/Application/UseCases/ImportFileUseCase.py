import os
import logging
from Backend.Domain.Entities.file import File
from Backend.Domain.Common.Enums.FileType import FileType
from Backend.Domain.Common.Enums.FileStatus import FileStatus
from Backend.Application.Interfaces.IFileRepository import IFileRepository
from Backend.Application.Interfaces.IDocumentProcessor import IDocumentProcessor
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IFileStorage import IFileStorage
from Backend.Application.Interfaces.ITripleExtractor import ITripleExtractor
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository

logger = logging.getLogger(__name__)


class ImportFileUseCase:
    def __init__(
        self,
        file_repository: IFileRepository,
        document_processor: IDocumentProcessor,
        vector_store_repository: IVectorStoreRepository,
        file_storage: IFileStorage,
        triple_extractor: ITripleExtractor | None = None,
        graph_repository: IGraphRepository | None = None,
    ):
        self._file_repo = file_repository
        self._doc_processor = document_processor
        self._vector_store = vector_store_repository
        self._file_storage = file_storage
        self._triple_extractor = triple_extractor
        self._graph_repo = graph_repository

    def receive_file(self, uploaded_file, filename: str) -> File:
        """同步阶段：保存文件到磁盘 + 创建实体(PENDING) + 存入 SQLite，返回实体。"""
        ext = os.path.splitext(filename)[1]
        file_type = FileType.from_extension(ext)

        saved_path = self._file_storage.save_file(uploaded_file, filename)
        logger.info("File saved to %s", saved_path)

        file_entity = File(file_name=filename, file_type=file_type)
        self._file_repo.save(file_entity)
        logger.info("File entity created: %s", file_entity.id)

        return file_entity

    def embed_file(self, file_name: str) -> None:
        """异步阶段：加载+分割文档 → 向量化存入 ChromaDB → 抽取三元组建图 → 更新状态。"""
        file_entity = self._file_repo.get_by_name(file_name)
        if file_entity is None:
            logger.error("File not found: %s", file_name)
            return

        try:
            file_path = self._file_storage.get_file_path(file_entity.file_name)
            documents = self._doc_processor.load_and_split(file_path, file_entity.file_type)
            self._vector_store.add_documents(file_entity.file_name, documents)
            self._file_repo.update_status(file_entity.id, FileStatus.EMBEDDED)
            logger.info("File embedded successfully: %s", file_entity.file_name)
        except Exception:
            self._file_repo.update_status(file_entity.id, FileStatus.FAILED)
            logger.exception("Failed to embed file: %s", file_entity.file_name)
            return

        # 知识图谱构建（降级策略：失败不影响已完成的向量嵌入）
        if self._triple_extractor and self._graph_repo:
            try:
                self._build_graph(file_entity.file_name, documents)
            except Exception:
                logger.exception("知识图谱构建失败（不影响向量检索）: %s", file_entity.file_name)

    def _build_graph(self, file_name: str, documents: list) -> None:
        chunks = [doc.page_content for doc in documents]
        logger.info("开始三元组抽取: %s (%d 个 chunk)", file_name, len(chunks))

        triples = self._triple_extractor.batch_extract(chunks, source_file=file_name)
        if not triples:
            logger.info("未抽取到三元组: %s", file_name)
            return

        # 写入 ChromaDB entity/relation collections
        seen_entities = set()
        for t in triples:
            if t.head not in seen_entities:
                self._vector_store.add_entity(t.head, t.head_type, source_file=file_name)
                seen_entities.add(t.head)
            if t.tail not in seen_entities:
                self._vector_store.add_entity(t.tail, t.tail_type, source_file=file_name)
                seen_entities.add(t.tail)
            self._vector_store.add_relation(t.head, t.relation, t.tail, source_file=file_name)

        # 写入 NetworkX 图并持久化
        self._graph_repo.add_triples(triples)
        self._graph_repo.save()
        logger.info(
            "知识图谱构建完成: %s → %d 条三元组, 图: %d 节点 %d 边",
            file_name, len(triples),
            self._graph_repo.node_count(), self._graph_repo.edge_count(),
        )
