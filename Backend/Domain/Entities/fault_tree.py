"""FaultTree 聚合根、FaultTreeNode 与 FaultTreeEdge 实体。

采用图结构（节点 + 边）表示故障树，与前端 React Flow 数据格式对齐。
事件节点和逻辑门节点作为独立节点存在，通过边连接。
纯 Python dataclass，不依赖任何外部框架。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from Backend.Domain.Common.Enums.fault_tree_status import FaultTreeStatus
from Backend.Domain.Common.Enums.gate_type import GateType
from Backend.Domain.Common.Enums.node_type import NodeType

# 节点类型常量（对应前端 React Flow 自定义节点类型）
NODE_TYPE_EVENT = "event"
NODE_TYPE_GATE = "gate"


@dataclass
class FaultTreeNode:
    """故障树节点。

    type == "event": 事件节点 — label（名称）、remark（备注）有效
    type == "gate":  逻辑门节点 — gate_type 有效
    """
    id: str
    type: str   # NODE_TYPE_EVENT | NODE_TYPE_GATE
    label: str = ""
    remark: str = ""
    gate_type: Optional[GateType] = None

    def to_dict(self) -> dict:
        """序列化为前后端通用的 JSON 格式。"""
        data: dict = {}
        if self.type == NODE_TYPE_EVENT:
            data["label"] = self.label
            if self.remark:
                data["remark"] = self.remark
        elif self.type == NODE_TYPE_GATE and self.gate_type:
            data["gateType"] = self.gate_type.value
        return {"id": self.id, "type": self.type, "data": data}

    @staticmethod
    def from_dict(raw: dict) -> FaultTreeNode:
        """从 JSON dict 反序列化。"""
        node_type = raw["type"]
        node_data = raw.get("data", {})
        if node_type == NODE_TYPE_EVENT:
            return FaultTreeNode(
                id=raw["id"],
                type=node_type,
                label=node_data.get("label", ""),
                remark=node_data.get("remark", ""),
            )
        if node_type == NODE_TYPE_GATE:
            gt_str = node_data.get("gateType")
            return FaultTreeNode(
                id=raw["id"],
                type=node_type,
                gate_type=GateType(gt_str) if gt_str else None,
            )
        raise ValueError(f"Unknown node type: {node_type}")


@dataclass
class FaultTreeEdge:
    """故障树边 — 节点之间的有向连接。"""
    id: str
    source: str
    target: str

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source, "target": self.target}

    @staticmethod
    def from_dict(raw: dict) -> FaultTreeEdge:
        return FaultTreeEdge(
            id=raw["id"],
            source=raw["source"],
            target=raw["target"],
        )


@dataclass
class FaultTree:
    """故障树聚合根 — 图结构（节点列表 + 边列表）。"""
    id: str
    name: str
    description: str
    session_id: str
    nodes: list[FaultTreeNode] = field(default_factory=list)
    edges: list[FaultTreeEdge] = field(default_factory=list)
    status: FaultTreeStatus = FaultTreeStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None

    # ---- Factory ----

    @staticmethod
    def create(
        name: str,
        description: str,
        session_id: str,
        nodes: list[FaultTreeNode],
        edges: list[FaultTreeEdge],
    ) -> FaultTree:
        return FaultTree(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            session_id=session_id,
            nodes=nodes,
            edges=edges,
            status=FaultTreeStatus.DRAFT,
            created_at=datetime.now(timezone.utc),
        )

    # ---- Query helpers ----

    def find_node(self, node_id: str) -> Optional[FaultTreeNode]:
        """根据 ID 查找节点。"""
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    @property
    def root_node_id(self) -> Optional[str]:
        """找到根事件节点（无入边的事件节点）。"""
        has_incoming = {e.target for e in self.edges}
        for node in self.nodes:
            if node.type == NODE_TYPE_EVENT and node.id not in has_incoming:
                return node.id
        return None

    def get_children(self, node_id: str) -> list[str]:
        """获取指定节点的所有直接子节点 ID。"""
        return [e.target for e in self.edges if e.source == node_id]

    def get_node_type(self, node_id: str) -> Optional[NodeType]:
        """根据图拓扑推断事件节点的 NodeType。

        有子逻辑门的事件 → intermediate_event
        无子节点的事件   → basic_event
        """
        node = self.find_node(node_id)
        if node is None or node.type != NODE_TYPE_EVENT:
            return None
        outgoing_targets = self.get_children(node_id)
        for tid in outgoing_targets:
            target_node = self.find_node(tid)
            if target_node and target_node.type == NODE_TYPE_GATE:
                return NodeType.INTERMEDIATE_EVENT
        return NodeType.BASIC_EVENT

    # ---- Validation ----

    def validate_structure(self) -> list[str]:
        """校验整棵故障树图的结构合法性。"""
        errors: list[str] = []
        node_ids = {n.id for n in self.nodes}

        # 1. 节点 ID 不能重复
        seen_ids: set[str] = set()
        for n in self.nodes:
            if n.id in seen_ids:
                errors.append(f"Duplicate node id: '{n.id}'")
            seen_ids.add(n.id)

        # 2. 边引用的节点必须存在
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge '{edge.id}': source '{edge.source}' not found")
            if edge.target not in node_ids:
                errors.append(f"Edge '{edge.id}': target '{edge.target}' not found")

        # 3. 逻辑门节点必须有 gateType
        for node in self.nodes:
            if node.type == NODE_TYPE_GATE and node.gate_type is None:
                errors.append(f"Gate node '{node.id}' MUST have gateType")

        # 4. 事件节点必须有 label
        for node in self.nodes:
            if node.type == NODE_TYPE_EVENT and not node.label:
                errors.append(f"Event node '{node.id}' MUST have label")

        # 5. 必须存在根事件节点（无入边的事件节点）
        if self.root_node_id is None:
            errors.append("No root event node found (event with no incoming edges)")

        # 6. 检测环 — 故障树 MUST 为 DAG
        adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
        for edge in self.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)

        visited: set[str] = set()
        in_stack: set[str] = set()

        def _has_cycle(nid: str) -> bool:
            visited.add(nid)
            in_stack.add(nid)
            for child in adj.get(nid, []):
                if child in in_stack:
                    return True
                if child not in visited and _has_cycle(child):
                    return True
            in_stack.discard(nid)
            return False

        for nid in node_ids:
            if nid not in visited:
                if _has_cycle(nid):
                    errors.append("Graph contains a cycle — fault tree MUST be acyclic (DAG)")
                    break

        return errors

    # ---- Serialization ----

    def to_dict(self) -> dict:
        """序列化 tree_data（存入 JSON）。"""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

    @staticmethod
    def tree_data_from_dict(data: dict) -> tuple[list[FaultTreeNode], list[FaultTreeEdge]]:
        """从 JSON dict 反序列化节点和边列表。"""
        nodes = [FaultTreeNode.from_dict(n) for n in data.get("nodes", [])]
        edges = [FaultTreeEdge.from_dict(e) for e in data.get("edges", [])]
        return nodes, edges

    # ---- Status transitions ----

    def transition_to(self, target: FaultTreeStatus) -> None:
        if not self.status.can_transition_to(target):
            raise ValueError(
                f"Invalid transition: {self.status.value} → {target.value}"
            )
        self.status = target
        if target == FaultTreeStatus.CONFIRMED:
            self.confirmed_at = datetime.now(timezone.utc)
