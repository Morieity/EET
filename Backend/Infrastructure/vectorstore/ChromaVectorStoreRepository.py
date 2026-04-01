from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository


class ChromaVectorStoreRepository(IVectorStoreRepository):
    def __init__(self, persist_directory: str = "db", collection_name: str = "rag_docs"):
        self._embedding = FastEmbedEmbeddings()
        self._persist_directory = persist_directory
        self._collection_name = collection_name

    def _get_store(self) -> Chroma:
        return Chroma(
            persist_directory=self._persist_directory,
            embedding_function=self._embedding,
            collection_name=self._collection_name,
        )

    def add_documents(self, file_name: str, documents: list) -> None:
        for doc in documents:
            doc.metadata["file_name"] = file_name
        store = self._get_store()
        store.add_documents(documents)

    def delete_by_file_name(self, file_name: str) -> None:
        store = self._get_store()
        collection = store._collection
        results = collection.get(where={"file_name": file_name})
        if results["ids"]:
            collection.delete(ids=results["ids"])
