import logging
from Backend.Application.Interfaces.IFileRepository import IFileRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IFileStorage import IFileStorage
from Backend.Application.Interfaces.IGraphRepository import IGraphRepository

logger = logging.getLogger(__name__)


class DeleteFileUseCase:
    def __init__(
        self,
        file_repository: IFileRepository,
        vector_store_repository: IVectorStoreRepository,
        file_storage: IFileStorage,
        graph_repository: IGraphRepository | None = None,
    ):
        self._file_repo = file_repository
        self._vector_store = vector_store_repository
        self._file_storage = file_storage
        self._graph_repo = graph_repository

    def execute(self, file_name: str) -> None:
        file_entity = self._file_repo.get_by_name(file_name)
        if file_entity is None:
            raise ValueError(f"File not found: {file_name}")

        self._vector_store.delete_by_file_name(file_entity.file_name)
        logger.info("Vectors deleted for file: %s", file_entity.file_name)

        # 删除图谱相关数据
        self._vector_store.delete_entities_by_file(file_entity.file_name)
        self._vector_store.delete_relations_by_file(file_entity.file_name)
        if self._graph_repo:
            self._graph_repo.remove_by_file(file_entity.file_name)
        logger.info("Graph data deleted for file: %s", file_entity.file_name)

        self._file_storage.delete_file(file_entity.file_name)
        logger.info("File deleted from disk: %s", file_entity.file_name)

        self._file_repo.delete(file_entity.id)
        logger.info("File record deleted: %s", file_entity.file_name)
