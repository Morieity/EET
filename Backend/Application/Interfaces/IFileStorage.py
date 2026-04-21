from abc import ABC, abstractmethod


class IFileStorage(ABC):
    @abstractmethod
    def save_file(self, uploaded_file, filename: str) -> str:
        """Save uploaded file to disk. Returns the saved file path."""
        pass

    @abstractmethod
    def delete_file(self, filename: str) -> None:
        """Delete a file from disk."""
        pass

    @abstractmethod
    def get_file_path(self, filename: str) -> str:
        """Return the full path for a stored file."""
        pass
