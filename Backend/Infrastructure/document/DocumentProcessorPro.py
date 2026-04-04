import re
import logging
from difflib import SequenceMatcher
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

# 控制字符正则：匹配除 \n \r \t 之外的所有控制字符和 Unicode 私有区符号
_RE_CONTROL_CHARS = re.compile(
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\uf000-\uf0ff]'
)

_MIN_CHUNK_LENGTH = 20
_NEAR_DEDUP_THRESHOLD = 0.9
_NEAR_DEDUP_WINDOW = 5


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

        # ── 后处理管线：清洗 → 过滤 → 精确去重 → 近似去重 ──
        all_chunks = self._clean(all_chunks)
        all_chunks = self._filter_noise(all_chunks)
        all_chunks = self._deduplicate(all_chunks)
        all_chunks = self._near_deduplicate(all_chunks)

        logger.info(
            "DocumentProcessorPro: %s → %d chunks (after post-processing)",
            file_path, len(all_chunks),
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

    # 数据清洗与去重 

    @staticmethod
    def _clean(chunks: list[Document]) -> list[Document]:
        """文本清洗：去除控制字符、合并多余空行、清理行首尾空格。"""
        for doc in chunks:
            text = doc.page_content
            text = _RE_CONTROL_CHARS.sub('', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = '\n'.join(line.strip() for line in text.splitlines())
            doc.page_content = text.strip()
        return chunks

    @staticmethod
    def _filter_noise(chunks: list[Document]) -> list[Document]:
        """过滤过短的噪音块。"""
        return [doc for doc in chunks if len(doc.page_content.strip()) >= _MIN_CHUNK_LENGTH]

    @staticmethod
    def _deduplicate(chunks: list[Document]) -> list[Document]:
        """精确去重：基于去空白指纹。"""
        seen: set[str] = set()
        unique: list[Document] = []
        for doc in chunks:
            fingerprint = re.sub(r'\s+', '', doc.page_content)
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(doc)
        return unique

    @staticmethod
    def _near_deduplicate(chunks: list[Document]) -> list[Document]:
        """近似去重：与最近窗口内的块比较相似度，超过阈值则丢弃。"""
        unique: list[Document] = []
        for doc in chunks:
            is_dup = False
            for existing in unique[-_NEAR_DEDUP_WINDOW:]:
                ratio = SequenceMatcher(
                    None, doc.page_content, existing.page_content
                ).ratio()
                if ratio >= _NEAR_DEDUP_THRESHOLD:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(doc)
        return unique

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
