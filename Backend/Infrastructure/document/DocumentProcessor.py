from Backend.Application.Interfaces.IDocumentProcessor import IDocumentProcessor
from Backend.Domain.Common.Enums.FileType import FileType
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    TextLoader,
    Docx2txtLoader,
)


class DocumentProcessor(IDocumentProcessor):
    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 80):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )

    def load_and_split(self, file_path: str, file_type: FileType) -> list:
        loader = self._get_loader(file_path, file_type)
        docs = loader.load()
        return self._splitter.split_documents(docs)

    @staticmethod
    def _get_loader(file_path: str, file_type: FileType):
        if file_type == FileType.PDF:
            return PDFPlumberLoader(file_path)
        if file_type == FileType.WORD:
            return Docx2txtLoader(file_path)
        if file_type in (FileType.TXT, FileType.MARKDOWN):
            return TextLoader(file_path, encoding="utf-8")
        raise ValueError(f"Unsupported file type: {file_type}")
