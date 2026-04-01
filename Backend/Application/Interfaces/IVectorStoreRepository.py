from abc import ABC, abstractmethod


class IVectorStoreRepository(ABC):
    @abstractmethod
    def add_documents(self, file_name: str, documents: list) -> None:
        """Add document chunks to the vector store with file_name in metadata."""
        pass

    @abstractmethod
    def delete_by_file_name(self, file_name: str) -> None:
        """Delete all vectors associated with a file_name."""
        pass
