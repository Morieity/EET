import logging
from Backend.Application.Interfaces.IFileRepository import IFileRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IFileStorage import IFileStorage

logger = logging.getLogger(__name__)


class DeleteFileUseCase:
    def __init__(
        self,
        file_repository: IFileRepository,
        vector_store_repository: IVectorStoreRepository,
        file_storage: IFileStorage,
    ):
        self._file_repo = file_repository
        self._vector_store = vector_store_repository
        self._file_storage = file_storage

    def execute(self, file_name: str) -> None:
        file_entity = self._file_repo.get_by_name(file_name)
        if file_entity is None:
            raise ValueError(f"File not found: {file_name}")

        self._vector_store.delete_by_file_name(file_entity.file_name)
        logger.info("Vectors deleted for file: %s", file_entity.file_name)

        self._file_storage.delete_file(file_entity.file_name)
        logger.info("File deleted from disk: %s", file_entity.file_name)

        self._file_repo.delete(file_entity.id)
        logger.info("File record deleted: %s", file_entity.file_name)
