import uuid
from datetime import datetime
from Backend.Domain.Common.Enums.FaultTreeEnums import NodeType, GateType


class FaultTreeNode:
    def __init__(
        self,
        node_id: str,
        label: str,
        node_type: NodeType = NodeType.EVENT,
        gate_type: GateType | None = None,
        remark: str = "",
        sources: list[dict] | None = None,
    ):
        self.id = node_id
        self.label = label
        self.node_type = node_type
        self.gate_type = gate_type
        self.remark = remark
        self.sources = sources or []

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "label": self.label,
            "node_type": self.node_type.value,
            "remark": self.remark,
            "sources": self.sources,
        }
        if self.gate_type:
            d["gate_type"] = self.gate_type.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "FaultTreeNode":
        gate_type = GateType(data["gate_type"]) if data.get("gate_type") else None
        return cls(
            node_id=data["id"],
            label=data.get("label", ""),
            node_type=NodeType(data.get("node_type", "event")),
            gate_type=gate_type,
            remark=data.get("remark", ""),
            sources=data.get("sources", []),
        )


class FaultTreeEdge:
    def __init__(self, edge_id: str, source_id: str, target_id: str):
        self.id = edge_id
        self.source_id = source_id
        self.target_id = target_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FaultTreeEdge":
        return cls(
            edge_id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
        )


class FaultTree:
    def __init__(
        self,
        name: str,
        nodes: list[FaultTreeNode] | None = None,
        edges: list[FaultTreeEdge] | None = None,
        tree_id: str | None = None,
        created_at: datetime | None = None,
        conversation_id: str | None = None,
    ):
        self.id = tree_id or str(uuid.uuid4())
        self.name = name
        self.nodes = nodes or []
        self.edges = edges or []
        self.created_at = created_at or datetime.now()
        self.conversation_id = conversation_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "created_at": self.created_at.isoformat(),
            "conversation_id": self.conversation_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FaultTree":
        nodes = [FaultTreeNode.from_dict(n) for n in data.get("nodes", [])]
        edges = [FaultTreeEdge.from_dict(e) for e in data.get("edges", [])]
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        return cls(
            name=data["name"],
            nodes=nodes,
            edges=edges,
            tree_id=data.get("id"),
            created_at=created_at,
            conversation_id=data.get("conversation_id"),
        )
