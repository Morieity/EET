import os
from typing import Protocol, Dict, Any
from werkzeug.datastructures import FileStorage
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class PdfLoader(Protocol):
    def __call__(self, path: str) -> list[Document]:
        """加载 PDF 路径并返回解析后的文档。"""
        ...


class TextSplitter(Protocol):
    def split_documents(self, documents: list[Document]) -> list[Document]:
        """将文档切分为可用于向量化的更小片段。"""
        ...


class VectorStoreRepository(Protocol):
    def persist_documents(self, chunks: list[Document]) -> None:
        """将文档切片向量持久化到存储中。"""
        ...


class UploadPdfUseCase:
    def __init__(
        self,
        pdf_dir: str,
        loader: PdfLoader,
        splitter: RecursiveCharacterTextSplitter,
        vector_store_repository: VectorStoreRepository,
    ):
        """初始化上传依赖并确保目标目录存在。"""
        self.pdf_dir = pdf_dir
        self.loader = loader
        self.splitter = splitter
        self.vector_store_repository = vector_store_repository
        os.makedirs(self.pdf_dir, exist_ok=True)

    def execute(self, file: FileStorage) -> Dict[str, Any]:
        """校验并保存上传文件，随后解析、切分并持久化 PDF 内容。"""
        if not file:
            raise ValueError("No file provided")
        if not file.filename:
            raise ValueError("File name is empty")
        if not file.filename.lower().endswith(".pdf"):
            raise ValueError("File must be a PDF")

        file_name = file.filename
        save_path = os.path.join(self.pdf_dir, file_name)
        file.save(save_path)

        documents = self.loader(save_path)
        chunks = self.splitter.split_documents(documents)

        self.vector_store_repository.persist_documents(chunks)

        return {
            "status": "Successfully Uploaded",
            "filename": file_name,
            "doc_len": len(documents),
            "chunks": len(chunks),
        }
