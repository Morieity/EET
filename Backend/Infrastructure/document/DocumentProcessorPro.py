import re
import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PDFPlumberLoader,
    TextLoader,
    Docx2txtLoader,
)
from Backend.Application.Interfaces.IDocumentProcessor import IDocumentProcessor
from Backend.Domain.Common.Enums.FileType import FileType

logger = logging.getLogger(__name__)


_RE_HEADING_L1 = re.compile(
    r"^[一二三四五六七八九十百]+[、．.]"
)

_RE_HEADING_L2 = re.compile(
    r"^\d+[、．.]"
)

_RE_HEADING_L3 = re.compile(
    r"^\d+\.\d+"
)

_RE_HEADING_MD = re.compile(
    r"^#{1,6}\s+"
)

_HEADING_PATTERNS = [
    (_RE_HEADING_L1, "heading_l1"),
    (_RE_HEADING_L2, "heading_l2"),
    (_RE_HEADING_L3, "heading_l3"),
    (_RE_HEADING_MD, "heading_md"),
]


class DocumentProcessorPro(IDocumentProcessor):
    """分层文档处理器：先按结构标题粗切，再对超长块细切。"""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 80):
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._fine_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=[
                "\n\n", 
                "\n", 
                "。", ". ",   
                "！", "! ",   
                "？", "? ",   
                "；", "; ",  
                "，", ", ",   
                " ",          
                ""            
            ],
        )


    def load_and_split(self, file_path: str, file_type: FileType) -> list:
        loader = self._get_loader(file_path, file_type)
        raw_docs = loader.load()

        all_chunks: list[Document] = []
        for doc in raw_docs:
            structural_blocks = self._split_by_structure(doc.page_content)
            for heading, body in structural_blocks:
                all_chunks.extend(
                    self._refine_block(heading, body, doc.metadata)
                )

        logger.info(
            "DocumentProcessorPro: %s → %d chunks", file_path, len(all_chunks)
        )
        return all_chunks


    @staticmethod
    def _split_by_structure(text: str) -> list[tuple[str, str]]:
        """
        按标题行将文本切成 (heading, body) 列表。
        heading 为空字符串表示文档开头无标题的前言部分。
        """
        blocks: list[tuple[str, str]] = []
        current_heading = ""
        current_lines: list[str] = []

        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped and _detect_heading(stripped):
                if current_lines:
                    blocks.append((current_heading, "".join(current_lines)))
                current_heading = stripped
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            blocks.append((current_heading, "".join(current_lines)))

        if not blocks:
            blocks.append(("", text))

        return blocks


    def _refine_block(
        self, heading: str, body: str, base_metadata: dict
    ) -> list[Document]:
        metadata = {**base_metadata}
        if heading:
            metadata["heading"] = heading

        full_text = f"{heading}\n{body}" if heading else body

        if len(full_text) <= self._chunk_size:
            return [Document(page_content=full_text, metadata=metadata)]

        sub_docs = self._fine_splitter.split_documents(
            [Document(page_content=full_text, metadata=metadata)]
        )

        for doc in sub_docs:
            if heading:
                doc.metadata["heading"] = heading
        return sub_docs


    @staticmethod
    def _get_loader(file_path: str, file_type: FileType):
        if file_type == FileType.PDF:
            return PDFPlumberLoader(file_path)
        if file_type == FileType.WORD:
            return Docx2txtLoader(file_path)
        if file_type in (FileType.TXT, FileType.MARKDOWN):
            return TextLoader(file_path, encoding="utf-8")
        raise ValueError(f"Unsupported file type: {file_type}")



def _detect_heading(line: str) -> bool:
    """判断一行是否为标题行。"""
    return any(pat.match(line) for pat, _ in _HEADING_PATTERNS)
