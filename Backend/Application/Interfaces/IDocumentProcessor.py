from abc import ABC, abstractmethod
from Backend.Domain.Common.Enums.FileType import FileType


class IDocumentProcessor(ABC):
    @abstractmethod
    def load_and_split(self, file_path: str, file_type: FileType) -> list:
        """Load a file and split it into document chunks."""
        pass
