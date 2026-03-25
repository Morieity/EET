from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def build_text_splitter() -> RecursiveCharacterTextSplitter:
    """构建用于 PDF 切片的默认文本分割器配置。"""
    # 这里的分割器配置是默认策略，到时需要根据具体文本调整
    return RecursiveCharacterTextSplitter(
        chunk_size=1024,
        chunk_overlap=80,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
        is_separator_regex=False,
    )


def split_documents(splitter: RecursiveCharacterTextSplitter, documents: list[Document]) -> list[Document]:
    """执行文档切分，并确保输出切片不为空。"""
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError("No chunks generated from PDF content")
    return chunks
