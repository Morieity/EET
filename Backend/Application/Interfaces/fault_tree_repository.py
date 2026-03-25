from typing import Protocol, Optional

from Backend.Domain.Entities.fault_tree import FaultTree


class FaultTreeRepository(Protocol):
    """故障树仓储接口。"""

    def save(self, fault_tree: FaultTree) -> None:
        """持久化故障树（序列化 root_node 为 JSONB）。"""
        ...

    def find_by_id(self, fault_tree_id: str) -> Optional[FaultTree]:
        """根据 ID 加载故障树（反序列化 JSONB 为 domain entity）；不存在时返回 None。"""
        ...
