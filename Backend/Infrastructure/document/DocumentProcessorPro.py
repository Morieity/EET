import re
import logging
import unicodedata
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


_RE_HEADING_L1 = re.compile(
    r"^[一二三四五六七八九十百]+[、．.]"
)

_RE_HEADING_L2 = re.compile(
    r"^\d+[、．.]"
)

_RE_HEADING_L3 = re.compile(
    r"^\d+\.\d+"
)

# 多级编号：1.1.1、2.3.4 等
_RE_HEADING_L4 = re.compile(
    r"^\d+\.\d+\.\d+"
)

_RE_HEADING_MD = re.compile(
    r"^#{1,6}\s+"
)

# 第X编 / 第X部分
_RE_HEADING_DI_BIAN = re.compile(
    r"^第[一二三四五六七八九十百零\d]+(?:编|部分)"
)

# 第X篇
_RE_HEADING_DI_PIAN = re.compile(
    r"^第[一二三四五六七八九十百零\d]+篇"
)

# 第X章
_RE_HEADING_DI_ZHANG = re.compile(
    r"^第[一二三四五六七八九十百零\d]+章"
)

# 第X节
_RE_HEADING_DI_JIE = re.compile(
    r"^第[一二三四五六七八九十百零\d]+节"
)

# 第X条
_RE_HEADING_DI_TIAO = re.compile(
    r"^第[一二三四五六七八九十百零\d]+条"
)

# （一）/ (一) — 中文数字括号编号
_RE_HEADING_PAREN_CN = re.compile(
    r"^[（(][一二三四五六七八九十百]+[）)]"
)

# （1）/ (1) — 阿拉伯数字括号编号
_RE_HEADING_PAREN_NUM = re.compile(
    r"^[（(]\d+[）)]"
)

# 全角数字标题：１、 ２．
_RE_HEADING_FULLWIDTH = re.compile(
    r"^[０-９]+[、．.]"
)

# 阿拉伯数字 + 单闭括号：1) 2）
_RE_HEADING_NUM_PAREN = re.compile(
    r"^\d+[）)]"
)

# 罗马数字序号：Ⅰ、 Ⅱ. Ⅲ） ⅰ、 等
_RE_HEADING_ROMAN = re.compile(
    r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+[、．.）)]\s*"
)

_HEADING_PATTERNS = [
    (_RE_HEADING_DI_BIAN, "heading_di_bian", 1),       # 第X编 / 第X部分
    (_RE_HEADING_DI_PIAN, "heading_di_pian", 2),       # 第X篇
    (_RE_HEADING_DI_ZHANG, "heading_di_zhang", 3),     # 第X章
    (_RE_HEADING_DI_JIE, "heading_di_jie", 4),         # 第X节
    (_RE_HEADING_DI_TIAO, "heading_di_tiao", 5),       # 第X条
    (_RE_HEADING_L1, "heading_l1", 6),                  # 一、
    (_RE_HEADING_PAREN_CN, "heading_paren_cn", 7),     # （一）
    (_RE_HEADING_ROMAN, "heading_roman", 7),            # Ⅰ、
    (_RE_HEADING_L4, "heading_l4", 10),                 # 1.1.1（须在 L3 之前匹配）
    (_RE_HEADING_L3, "heading_l3", 9),                  # 1.1（须在 L2 之前匹配）
    (_RE_HEADING_L2, "heading_l2", 8),                  # 1、
    (_RE_HEADING_FULLWIDTH, "heading_fullwidth", 8),    # １、
    (_RE_HEADING_PAREN_NUM, "heading_paren_num", 11),  # （1）
    (_RE_HEADING_NUM_PAREN, "heading_num_paren", 11),  # 1）
    (_RE_HEADING_MD, "heading_md", None),               # Markdown：# 数量即层级
]


class DocumentProcessorPro(IDocumentProcessor):
    """分层文档处理器：先按结构标题粗切，再对超长块细切。"""

    def __init__(self, chunk_size: int = 1024, chunk_overlap: int = 200):
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

        # 合并所有页面文本，避免跨页断裂导致标题层级丢失
        merged_text = "\n".join(doc.page_content for doc in raw_docs)
        # Unicode 正规化：将 PDF 提取的异体字（如康熙部首⼀→一）转为标准字符
        merged_text = unicodedata.normalize('NFKC', merged_text)
        base_metadata = raw_docs[0].metadata if raw_docs else {}

        structural_blocks = self._split_by_structure(merged_text)
        all_chunks: list[Document] = []
        for heading, body in structural_blocks:
            all_chunks.extend(
                self._refine_block(heading, body, base_metadata)
            )

        # ── 后处理管线：清洗 → 过滤 → 精确去重 ──
        all_chunks = self._clean(all_chunks)
        all_chunks = self._filter_noise(all_chunks)
        all_chunks = self._deduplicate(all_chunks)

        logger.info(
            "DocumentProcessorPro: %s → %d chunks (after post-processing)",
            file_path, len(all_chunks),
        )
        return all_chunks


    @staticmethod
    def _split_by_structure(text: str) -> list[tuple[str, str]]:
        """
        按标题行将文本切成 (heading_path, body) 列表。
        利用标题层级栈维护父子关系，heading_path 用 " > " 连接各级标题。
        heading_path 为空字符串表示文档开头无标题的前言部分。
        """
        blocks: list[tuple[str, str]] = []
        # 栈元素: (heading_text, level)
        heading_stack: list[tuple[str, int]] = []
        current_lines: list[str] = []

        def _heading_path() -> str:
            return " > ".join(h for h, _ in heading_stack)

        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            result = _detect_heading(stripped) if stripped else None
            if result is not None:
                heading_text, level = result
                if current_lines:
                    blocks.append((_heading_path(), "".join(current_lines)))
                    current_lines = []
                # 弹出同级或更低级的标题，保留严格的父级
                while heading_stack and heading_stack[-1][1] >= level:
                    heading_stack.pop()
                heading_stack.append((heading_text, level))
            else:
                current_lines.append(line)

        if current_lines:
            blocks.append((_heading_path(), "".join(current_lines)))

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

        if heading:
            prefix = heading + "\n"
            for doc in sub_docs:
                doc.metadata["heading"] = heading
                if not doc.page_content.startswith(heading):
                    doc.page_content = prefix + doc.page_content
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
    def _get_loader(file_path: str, file_type: FileType):
        if file_type == FileType.PDF:
            return PDFPlumberLoader(file_path)
        if file_type == FileType.WORD:
            return Docx2txtLoader(file_path)
        if file_type in (FileType.TXT, FileType.MARKDOWN):
            return TextLoader(file_path, encoding="utf-8")
        raise ValueError(f"Unsupported file type: {file_type}")



def _detect_heading(line: str) -> tuple[str, int] | None:
    """
    判断一行是否为标题行。
    返回 (原始标题文本, 层级数值)，非标题返回 None。
    """
    for pat, label, level in _HEADING_PATTERNS:
        if pat.match(line):
            if level is None:
                # Markdown 标题：# 数量即层级
                level = len(line) - len(line.lstrip('#'))
            return line, level
    return None
