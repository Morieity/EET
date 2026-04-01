import os
from Backend.Application.Interfaces.IFileStorage import IFileStorage

UPLOAD_FOLDER = "uploads"


class LocalFileStorage(IFileStorage):
    def __init__(self, upload_folder: str = UPLOAD_FOLDER):
        self._upload_folder = upload_folder
        os.makedirs(self._upload_folder, exist_ok=True)

    def save_file(self, uploaded_file, filename: str) -> str:
        path = os.path.join(self._upload_folder, filename)
        uploaded_file.save(path)
        return path

    def delete_file(self, filename: str) -> None:
        path = os.path.join(self._upload_folder, filename)
        if os.path.exists(path):
            os.remove(path)

    def get_file_path(self, filename: str) -> str:
        return os.path.join(self._upload_folder, filename)
