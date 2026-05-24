"""Domain entity unit tests for FaultTree / FaultTreeNode / FaultTreeEdge."""

from Backend.Domain.Common.Enums.FaultTreeEnums import GateType, NodeType
from Backend.Domain.Entities.fault_tree import FaultTree, FaultTreeEdge, FaultTreeNode


def test_event_node_round_trip_through_dict() -> None:
    node = FaultTreeNode(
        node_id="n1",
        label="顶事件",
        node_type=NodeType.EVENT,
        remark="说明",
        sources=[{"file_name": "doc.pdf", "page_content": "片段"}],
    )

    payload = node.to_dict()
    restored = FaultTreeNode.from_dict(payload)

    assert "gate_type" not in payload  # event nodes do not serialize gate_type
    assert restored.id == node.id
    assert restored.label == node.label
    assert restored.node_type == NodeType.EVENT
    assert restored.gate_type is None
    assert restored.remark == "说明"
    assert restored.sources == node.sources


def test_gate_node_serializes_gate_type() -> None:
    node = FaultTreeNode(
        node_id="g1",
        label="",
        node_type=NodeType.GATE,
        gate_type=GateType.AND,
    )

    payload = node.to_dict()
    assert payload["gate_type"] == "AND"

    restored = FaultTreeNode.from_dict(payload)
    assert restored.node_type == NodeType.GATE
    assert restored.gate_type == GateType.AND


def test_fault_tree_round_trip_preserves_topology() -> None:
    tree = FaultTree(
        name="测试故障树",
        nodes=[
            FaultTreeNode(node_id="n1", label="顶事件"),
            FaultTreeNode(node_id="g1", label="", node_type=NodeType.GATE, gate_type=GateType.OR),
            FaultTreeNode(node_id="n2", label="子事件"),
        ],
        edges=[
            FaultTreeEdge(edge_id="e1", source_id="n1", target_id="g1"),
            FaultTreeEdge(edge_id="e2", source_id="g1", target_id="n2"),
        ],
        conversation_id="conv-1",
    )

    payload = tree.to_dict()
    restored = FaultTree.from_dict(payload)

    assert restored.name == "测试故障树"
    assert restored.conversation_id == "conv-1"
    assert [n.id for n in restored.nodes] == ["n1", "g1", "n2"]
    assert [(e.source_id, e.target_id) for e in restored.edges] == [
        ("n1", "g1"),
        ("g1", "n2"),
    ]
    assert restored.nodes[1].gate_type == GateType.OR
