from abc import ABC, abstractmethod
from Backend.Domain.Entities.triple import Triple


class ITripleExtractor(ABC):
    @abstractmethod
    def extract(self, chunk_text: str, source_file: str = "", source_chunk_id: str = "") -> list[Triple]:
        """从单个文本块中抽取知识三元组。"""
        pass

    @abstractmethod
    def batch_extract(self, chunks: list[str], source_file: str = "") -> list[Triple]:
        """批量抽取多个文本块的三元组。"""
        pass
