from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def build_text_splitter() -> RecursiveCharacterTextSplitter:
    """构建用于 PDF 切片的默认文本分割器配置。"""
    return RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=80,
        length_function=len,
        is_separator_regex=False,
    )


def split_documents(splitter: RecursiveCharacterTextSplitter, documents: list[Document]) -> list[Document]:
    """执行文档切分，并确保输出切片不为空。"""
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError("No chunks generated from PDF content")
    return chunks
