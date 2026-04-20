"""故障树节点 sources 字段 — 数据层单元测试

覆盖范围:
  - FaultTreeNode 实体 sources 字段创建、to_dict、from_dict
  - sources 默认空数组
  - 含中文 sources 的序列化/反序列化
  - FaultTreeRepository 保存/读取含 sources 的节点
  - 向后兼容：缺少 sources 的旧数据不报错
  - FaultTree 整体 to_dict/from_dict 包含 sources
"""

import json
import os
import sqlite3
import tempfile
import uuid

import pytest

from Backend.Domain.Entities.fault_tree import FaultTree, FaultTreeNode, FaultTreeEdge
from Backend.Domain.Common.Enums.FaultTreeEnums import NodeType, GateType


# ── FaultTreeNode 实体测试 ──


class TestFaultTreeNodeSources:
    """FaultTreeNode 实体 sources 字段单元测试"""

    def test_node_default_sources_empty_list(self):
        node = FaultTreeNode(node_id="n1", label="事件A")
        assert node.sources == []

    def test_node_with_sources(self):
        sources = [
            {"file_name": "手册.pdf", "page_content": "电机过热原因分析"},
            {"file_name": "案例.docx", "page_content": "案例#1 散热风扇失效"},
        ]
        node = FaultTreeNode(node_id="n1", label="电机过热", sources=sources)
        assert node.sources == sources
        assert len(node.sources) == 2

    def test_node_sources_none_becomes_empty_list(self):
        node = FaultTreeNode(node_id="n1", label="A", sources=None)
        assert node.sources == []

    def test_to_dict_includes_sources(self):
        sources = [{"file_name": "a.pdf", "page_content": "内容片段"}]
        node = FaultTreeNode(node_id="n1", label="事件", sources=sources)
        d = node.to_dict()
        assert "sources" in d
        assert d["sources"] == sources

    def test_to_dict_empty_sources(self):
        node = FaultTreeNode(node_id="n1", label="事件")
        d = node.to_dict()
        assert d["sources"] == []

    def test_from_dict_with_sources(self):
        data = {
            "id": "n1",
            "label": "电机过热",
            "node_type": "event",
            "remark": "备注",
            "sources": [
                {"file_name": "手册.pdf", "page_content": "原文片段"},
            ],
        }
        node = FaultTreeNode.from_dict(data)
        assert node.sources == data["sources"]

    def test_from_dict_without_sources_defaults_empty(self):
        data = {"id": "n1", "label": "事件", "node_type": "event"}
        node = FaultTreeNode.from_dict(data)
        assert node.sources == []

    def test_from_dict_sources_empty_array(self):
        data = {"id": "n1", "label": "门", "node_type": "gate", "gate_type": "OR", "sources": []}
        node = FaultTreeNode.from_dict(data)
        assert node.sources == []

    def test_gate_node_with_empty_sources(self):
        node = FaultTreeNode(
            node_id="g1", label="", node_type=NodeType.GATE,
            gate_type=GateType.OR, sources=[]
        )
        d = node.to_dict()
        assert d["sources"] == []
        assert d["gate_type"] == "OR"

    def test_chinese_content_in_sources(self):
        sources = [{"file_name": "设备维修手册.pdf", "page_content": "电机过热通常由以下原因引起：1. 环境温度过高"}]
        node = FaultTreeNode(node_id="n1", label="电机过热", sources=sources)
        d = node.to_dict()
        restored = FaultTreeNode.from_dict(d)
        assert restored.sources[0]["file_name"] == "设备维修手册.pdf"
        assert "环境温度过高" in restored.sources[0]["page_content"]

    def test_roundtrip_to_dict_from_dict(self):
        sources = [
            {"file_name": "a.pdf", "page_content": "片段1"},
            {"file_name": "b.docx", "page_content": "片段2"},
        ]
        original = FaultTreeNode(
            node_id="n1", label="事件A", node_type=NodeType.EVENT,
            remark="备注", sources=sources,
        )
        d = original.to_dict()
        restored = FaultTreeNode.from_dict(d)
        assert restored.id == original.id
        assert restored.label == original.label
        assert restored.sources == original.sources
        assert restored.remark == original.remark


# ── FaultTree 整体 to_dict/from_dict 测试 ──


class TestFaultTreeSources:
    """FaultTree 整体序列化含 sources 测试"""

    def _make_tree(self):
        nodes = [
            FaultTreeNode(
                node_id="n1", label="顶事件", node_type=NodeType.EVENT,
                sources=[{"file_name": "doc.pdf", "page_content": "内容"}],
            ),
            FaultTreeNode(
                node_id="g1", label="", node_type=NodeType.GATE,
                gate_type=GateType.OR, sources=[],
            ),
            FaultTreeNode(
                node_id="n2", label="子事件", node_type=NodeType.EVENT,
                sources=[{"file_name": "other.pdf", "page_content": "其他内容"}],
            ),
        ]
        edges = [
            FaultTreeEdge(edge_id="e1", source_id="n1", target_id="g1"),
            FaultTreeEdge(edge_id="e2", source_id="g1", target_id="n2"),
        ]
        return FaultTree(name="测试树", nodes=nodes, edges=edges)

    def test_fault_tree_to_dict_contains_sources(self):
        tree = self._make_tree()
        d = tree.to_dict()
        assert d["nodes"][0]["sources"] == [{"file_name": "doc.pdf", "page_content": "内容"}]
        assert d["nodes"][1]["sources"] == []

    def test_fault_tree_from_dict_restores_sources(self):
        tree = self._make_tree()
        d = tree.to_dict()
        restored = FaultTree.from_dict(d)
        assert restored.nodes[0].sources == tree.nodes[0].sources
        assert restored.nodes[2].sources == tree.nodes[2].sources


# ── Repository 层集成测试（使用临时 SQLite） ──


@pytest.fixture()
def db_connection(tmp_path):
    """创建临时 SQLite 数据库，含故障树表结构"""
    db_path = str(tmp_path / "test.sqlite3")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_trees (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            conversation_id TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_tree_nodes (
            id TEXT NOT NULL,
            tree_id TEXT NOT NULL,
            label TEXT NOT NULL,
            node_type TEXT NOT NULL,
            gate_type TEXT,
            remark TEXT DEFAULT '',
            sources TEXT DEFAULT '[]',
            PRIMARY KEY (id, tree_id),
            FOREIGN KEY (tree_id) REFERENCES fault_trees(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fault_tree_edges (
            id TEXT NOT NULL,
            tree_id TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            PRIMARY KEY (id, tree_id),
            FOREIGN KEY (tree_id) REFERENCES fault_trees(id)
        )
    """)
    conn.commit()
    yield conn
    conn.close()


class TestRepositorySourcesIntegration:
    """Repository 层 sources 读写集成测试（使用真实 SQLite）"""

    def _insert_tree(self, conn, tree: FaultTree):
        """手动插入故障树到数据库，模拟 Repository 的 save"""
        conn.execute(
            "INSERT INTO fault_trees (id, name, conversation_id, created_at) VALUES (?, ?, ?, ?)",
            (tree.id, tree.name, tree.conversation_id, tree.created_at.isoformat()),
        )
        for n in tree.nodes:
            conn.execute(
                "INSERT INTO fault_tree_nodes (id, tree_id, label, node_type, gate_type, remark, sources) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (n.id, tree.id, n.label, n.node_type.value,
                 n.gate_type.value if n.gate_type else None, n.remark,
                 json.dumps(n.sources, ensure_ascii=False)),
            )
        for e in tree.edges:
            conn.execute(
                "INSERT INTO fault_tree_edges (id, tree_id, source_id, target_id) VALUES (?, ?, ?, ?)",
                (e.id, tree.id, e.source_id, e.target_id),
            )
        conn.commit()

    def _read_tree(self, conn, tree_id: str) -> FaultTree | None:
        """手动从数据库读取故障树，模拟 Repository 的 get_by_id"""
        from datetime import datetime
        row = conn.execute(
            "SELECT id, name, conversation_id, created_at FROM fault_trees WHERE id = ?",
            (tree_id,),
        ).fetchone()
        if row is None:
            return None

        node_rows = conn.execute(
            "SELECT id, label, node_type, gate_type, remark, sources FROM fault_tree_nodes WHERE tree_id = ?",
            (tree_id,),
        ).fetchall()
        nodes = [
            FaultTreeNode(
                node_id=nr["id"],
                label=nr["label"],
                node_type=NodeType(nr["node_type"]),
                gate_type=GateType(nr["gate_type"]) if nr["gate_type"] else None,
                remark=nr["remark"] or "",
                sources=json.loads(nr["sources"] or "[]"),
            )
            for nr in node_rows
        ]

        edge_rows = conn.execute(
            "SELECT id, source_id, target_id FROM fault_tree_edges WHERE tree_id = ?",
            (tree_id,),
        ).fetchall()
        edges = [
            FaultTreeEdge(edge_id=er["id"], source_id=er["source_id"], target_id=er["target_id"])
            for er in edge_rows
        ]

        return FaultTree(
            name=row["name"],
            nodes=nodes,
            edges=edges,
            tree_id=tree_id,
            created_at=datetime.fromisoformat(row["created_at"]),
            conversation_id=row["conversation_id"],
        )

    def test_save_and_read_with_sources(self, db_connection):
        sources = [
            {"file_name": "设备维修手册.pdf", "page_content": "电机过热通常由以下原因引起"},
            {"file_name": "故障案例库.docx", "page_content": "案例#213：电机过热导致停机"},
        ]
        tree = FaultTree(
            name="测试树",
            nodes=[
                FaultTreeNode(node_id="n1", label="电机过热", sources=sources),
                FaultTreeNode(
                    node_id="g1", label="", node_type=NodeType.GATE,
                    gate_type=GateType.OR, sources=[],
                ),
            ],
            edges=[FaultTreeEdge(edge_id="e1", source_id="n1", target_id="g1")],
        )
        self._insert_tree(db_connection, tree)
        loaded = self._read_tree(db_connection, tree.id)

        assert loaded is not None
        n1 = next(n for n in loaded.nodes if n.id == "n1")
        g1 = next(n for n in loaded.nodes if n.id == "g1")
        assert n1.sources == sources
        assert g1.sources == []

    def test_save_and_read_empty_sources(self, db_connection):
        tree = FaultTree(
            name="空来源树",
            nodes=[FaultTreeNode(node_id="n1", label="事件", sources=[])],
            edges=[],
        )
        self._insert_tree(db_connection, tree)
        loaded = self._read_tree(db_connection, tree.id)
        assert loaded.nodes[0].sources == []

    def test_backward_compat_null_sources_column(self, db_connection):
        """模拟旧数据：sources 列为 NULL 时不报错，返回空数组"""
        tree_id = str(uuid.uuid4())
        db_connection.execute(
            "INSERT INTO fault_trees (id, name, conversation_id, created_at) VALUES (?, ?, ?, ?)",
            (tree_id, "旧树", None, "2026-01-01T00:00:00"),
        )
        db_connection.execute(
            "INSERT INTO fault_tree_nodes (id, tree_id, label, node_type, gate_type, remark, sources) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("n1", tree_id, "旧节点", "event", None, "", None),
        )
        db_connection.commit()

        loaded = self._read_tree(db_connection, tree_id)
        assert loaded is not None
        assert loaded.nodes[0].sources == []

    def test_backward_compat_empty_string_sources(self, db_connection):
        """sources 列为空字符串时不报错"""
        tree_id = str(uuid.uuid4())
        db_connection.execute(
            "INSERT INTO fault_trees (id, name, conversation_id, created_at) VALUES (?, ?, ?, ?)",
            (tree_id, "空字符串树", None, "2026-01-01T00:00:00"),
        )
        db_connection.execute(
            "INSERT INTO fault_tree_nodes (id, tree_id, label, node_type, gate_type, remark, sources) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("n1", tree_id, "节点", "event", None, "", ""),
        )
        db_connection.commit()

        loaded = self._read_tree(db_connection, tree_id)
        assert loaded is not None
        assert loaded.nodes[0].sources == []

    def test_chinese_sources_roundtrip(self, db_connection):
        """中文来源内容完整保存和读取"""
        sources = [{"file_name": "设备维修手册.pdf", "page_content": "电机过热通常由以下原因引起：1. 环境温度过高 2. 散热风扇失效"}]
        tree = FaultTree(
            name="中文测试",
            nodes=[FaultTreeNode(node_id="n1", label="电机过热", sources=sources)],
            edges=[],
        )
        self._insert_tree(db_connection, tree)
        loaded = self._read_tree(db_connection, tree.id)
        assert loaded.nodes[0].sources[0]["file_name"] == "设备维修手册.pdf"
        assert "环境温度过高" in loaded.nodes[0].sources[0]["page_content"]

    def test_multiple_nodes_different_sources(self, db_connection):
        """多个节点各自独立的 sources"""
        tree = FaultTree(
            name="多节点",
            nodes=[
                FaultTreeNode(node_id="n1", label="A",
                              sources=[{"file_name": "a.pdf", "page_content": "A内容"}]),
                FaultTreeNode(node_id="n2", label="B",
                              sources=[{"file_name": "b.pdf", "page_content": "B内容"}]),
                FaultTreeNode(node_id="n3", label="C", sources=[]),
            ],
            edges=[],
        )
        self._insert_tree(db_connection, tree)
        loaded = self._read_tree(db_connection, tree.id)

        node_map = {n.id: n for n in loaded.nodes}
        assert node_map["n1"].sources[0]["file_name"] == "a.pdf"
        assert node_map["n2"].sources[0]["file_name"] == "b.pdf"
        assert node_map["n3"].sources == []

    def test_json_dumps_ensure_ascii_false(self):
        """验证 json.dumps 使用 ensure_ascii=False 保留中文"""
        sources = [{"file_name": "手册.pdf", "page_content": "中文内容"}]
        dumped = json.dumps(sources, ensure_ascii=False)
        assert "手册.pdf" in dumped
        assert "中文内容" in dumped
        assert "\\u" not in dumped
