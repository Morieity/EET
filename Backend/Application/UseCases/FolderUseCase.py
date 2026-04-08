"""文件夹用例层，处理创建、重命名、删除文件夹及文件归类的业务逻辑。"""
import logging
from Backend.Domain.Entities.folder import Folder
from Backend.Application.Interfaces.IFolderRepository import IFolderRepository
from Backend.Application.Interfaces.IFileRepository import IFileRepository

logger = logging.getLogger(__name__)


class FolderUseCase:
    def __init__(
        self,
        folder_repository: IFolderRepository,
        file_repository: IFileRepository,
    ):
        self._folder_repo = folder_repository
        self._file_repo = file_repository

    def create_folder(self, name: str) -> Folder:
        existing = self._folder_repo.get_by_name(name)
        if existing is not None:
            raise ValueError(f"Folder already exists: {name}")
        folder = Folder(name=name)
        self._folder_repo.save(folder)
        logger.info("Folder created: %s (%s)", folder.name, folder.id)
        return folder

    def rename_folder(self, folder_id: str, new_name: str) -> Folder:
        folder = self._folder_repo.get_by_id(folder_id)
        if folder is None:
            raise ValueError(f"Folder not found: {folder_id}")
        existing = self._folder_repo.get_by_name(new_name)
        if existing is not None and existing.id != folder_id:
            raise ValueError(f"Folder name already taken: {new_name}")
        folder.rename(new_name)
        self._folder_repo.update_name(folder_id, new_name)
        logger.info("Folder renamed: %s -> %s", folder_id, new_name)
        return folder

    def list_folders(self) -> list[dict]:
        folders = self._folder_repo.get_all()
        result = []
        for folder in folders:
            files = self._file_repo.get_by_folder_id(folder.id)
            folder_dict = folder.to_dict()
            folder_dict["files"] = [f.to_dict() for f in files]
            result.append(folder_dict)
        return result

    def delete_folder(self, folder_id: str) -> None:
        folder = self._folder_repo.get_by_id(folder_id)
        if folder is None:
            raise ValueError(f"Folder not found: {folder_id}")
        self._folder_repo.delete(folder_id)
        logger.info("Folder deleted: %s (%s)", folder.name, folder_id)

    def move_file_to_folder(self, file_id: str, folder_id: str | None) -> None:
        if folder_id is not None:
            folder = self._folder_repo.get_by_id(folder_id)
            if folder is None:
                raise ValueError(f"Folder not found: {folder_id}")
        self._file_repo.update_folder(file_id, folder_id)
        logger.info("File %s moved to folder %s", file_id, folder_id)
