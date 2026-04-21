from abc import ABC, abstractmethod
from Backend.Domain.Entities.file import File
from Backend.Domain.Common.Enums.FileStatus import FileStatus


class IFileRepository(ABC):
    @abstractmethod
    def save(self, file: File) -> None:
        pass

    @abstractmethod
    def delete(self, file_id: str) -> None:
        pass

    @abstractmethod
    def get_by_name(self, file_name: str) -> File | None:
        pass

    @abstractmethod
    def get_all(self) -> list[File]:
        pass

    @abstractmethod
    def update_status(self, file_id: str, status: FileStatus) -> None:
        pass
