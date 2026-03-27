from typing import Protocol

from langchain_core.documents import Document


class DocumentDeduplicator(Protocol):
    """文档去重器接口。"""

    def deduplicate(
        self,
        chunks: list[Document],
    ) -> tuple[list[Document], int]:
        """对切分后的文档片段执行去重。

        Returns:
            (保留的片段列表, 被去重移除的片段数)
        """
        ...
