"""文件夹仓储抽象接口，定义文件夹的持久化操作契约。"""
from abc import ABC, abstractmethod
from Backend.Domain.Entities.folder import Folder


class IFolderRepository(ABC):
    @abstractmethod
    def save(self, folder: Folder) -> None:
        pass

    @abstractmethod
    def get_by_id(self, folder_id: str) -> Folder | None:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Folder | None:
        pass

    @abstractmethod
    def get_all(self) -> list[Folder]:
        pass

    @abstractmethod
    def update_name(self, folder_id: str, new_name: str) -> None:
        pass

    @abstractmethod
    def delete(self, folder_id: str) -> None:
        pass
