import os
import logging
from Backend.Domain.Entities.file import File
from Backend.Domain.Common.Enums.FileType import FileType
from Backend.Domain.Common.Enums.FileStatus import FileStatus
from Backend.Application.Interfaces.IFileRepository import IFileRepository
from Backend.Application.Interfaces.IDocumentProcessor import IDocumentProcessor
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IFileStorage import IFileStorage

logger = logging.getLogger(__name__)


class ImportFileUseCase:
    def __init__(
        self,
        file_repository: IFileRepository,
        document_processor: IDocumentProcessor,
        vector_store_repository: IVectorStoreRepository,
        file_storage: IFileStorage,
    ):
        self._file_repo = file_repository
        self._doc_processor = document_processor
        self._vector_store = vector_store_repository
        self._file_storage = file_storage

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
        """异步阶段：加载+分割文档 → 向量化存入 ChromaDB → 更新状态。"""
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
