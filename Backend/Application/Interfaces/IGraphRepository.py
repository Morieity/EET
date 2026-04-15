from abc import ABC, abstractmethod
from Backend.Domain.Entities.triple import Triple


class IGraphRepository(ABC):
    @abstractmethod
    def load(self) -> None:
        """从持久化存储加载图到内存。"""
        pass

    @abstractmethod
    def save(self) -> None:
        """将内存图持久化到存储。"""
        pass

    @abstractmethod
    def add_triples(self, triples: list[Triple]) -> None:
        """批量添加三元组到图中。"""
        pass

    @abstractmethod
    def remove_by_file(self, file_name: str) -> None:
        """移除与指定文件关联的所有节点和边。"""
        pass

    @abstractmethod
    def expand_subgraph(self, seed_entities: list[str], hops: int = 2) -> list[dict]:
        """从种子实体出发，BFS 扩展 N 跳子图，返回关系路径列表。

        返回格式: [{"from": str, "relation": str, "to": str}, ...]
        """
        pass

    @abstractmethod
    def node_count(self) -> int:
        pass

    @abstractmethod
    def edge_count(self) -> int:
        pass
