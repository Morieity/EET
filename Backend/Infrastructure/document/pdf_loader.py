from langchain_community.document_loaders import PDFPlumberLoader
from langchain_core.documents import Document


def load_pdf(path: str) -> list[Document]:
    """从 PDF 路径加载文档并进行有效性校验。"""
    loader = PDFPlumberLoader(path)
    documents = loader.load()
    if not documents:
        raise ValueError("PDF file is empty or unreadable")
    return documents
