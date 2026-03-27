"""UploadDocumentUseCase — 文档上传 + 去重 + 向量化入库。"""
import os
from typing import Any, Dict

from langchain_text_splitters import RecursiveCharacterTextSplitter
from werkzeug.datastructures import FileStorage

from Backend.Application.Interfaces.document_deduplicator import DocumentDeduplicator
from Backend.Application.Interfaces.pdf_repository import PdfLoader, VectorStoreRepository


class UploadDocumentUseCase:
    def __init__(
        self,
        pdf_dir: str,
        loader: PdfLoader,
        splitter: RecursiveCharacterTextSplitter,
        vector_store_repository: VectorStoreRepository,
        deduplicator: DocumentDeduplicator,
    ):
        self.pdf_dir = pdf_dir
        self.loader = loader
        self.splitter = splitter
        self.vector_store_repository = vector_store_repository
        self.deduplicator = deduplicator
        os.makedirs(self.pdf_dir, exist_ok=True)

    def execute(self, file: FileStorage) -> Dict[str, Any]:
        if not file:
            raise ValueError("No file provided")
        if not file.filename:
            raise ValueError("File name is empty")
        if not file.filename.lower().endswith(".pdf"):
            raise ValueError("Unsupported file format. Only PDF is supported.")

        file_name = file.filename
        save_path = os.path.join(self.pdf_dir, file_name)
        file.save(save_path)

        documents = self.loader(save_path)
        chunks = self.splitter.split_documents(documents)
        total_chunks = len(chunks)

        # 三级去重
        unique_chunks, deduplicated_count = self.deduplicator.deduplicate(chunks)

        # 持久化到向量库
        if unique_chunks:
            self.vector_store_repository.persist_documents(unique_chunks)

        return {
            "status": "success",
            "filename": file_name,
            "total_chunks": total_chunks,
            "persisted_chunks": len(unique_chunks),
            "deduplicated_chunks": deduplicated_count,
            "skipped_chunks": 0,
        }
