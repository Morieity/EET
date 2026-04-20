import json
import logging
from datetime import datetime
from Backend.Domain.Entities.fault_tree import FaultTree, FaultTreeNode, FaultTreeEdge
from Backend.Domain.Common.Enums.FaultTreeEnums import NodeType, GateType
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
from Backend.Infrastructure.persistence.database import get_connection

logger = logging.getLogger(__name__)


class SQLiteFaultTreeRepository(IFaultTreeRepository):

    def save(self, fault_tree: FaultTree) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO fault_trees (id, name, conversation_id, created_at) VALUES (?, ?, ?, ?)",
                (fault_tree.id, fault_tree.name, fault_tree.conversation_id,
                 fault_tree.created_at.isoformat()),
            )
            self._insert_nodes(conn, fault_tree.id, fault_tree.nodes)
            self._insert_edges(conn, fault_tree.id, fault_tree.edges)
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, tree_id: str) -> FaultTree | None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, name, conversation_id, created_at FROM fault_trees WHERE id = ?",
                (tree_id,),
            ).fetchone()
            if row is None:
                return None
            return self._build_tree(conn, row)
        finally:
            conn.close()

    def get_by_conversation_id(self, conversation_id: str) -> FaultTree | None:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT id, name, conversation_id, created_at FROM fault_trees "
                "WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1",
                (conversation_id,),
            ).fetchone()
            if row is None:
                return None
            return self._build_tree(conn, row)
        finally:
            conn.close()

    def get_all(self) -> list[FaultTree]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, name, conversation_id, created_at FROM fault_trees ORDER BY created_at DESC"
            ).fetchall()
            return [self._build_tree(conn, row) for row in rows]
        finally:
            conn.close()

    def update(self, fault_tree: FaultTree) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE fault_trees SET name = ?, conversation_id = ? WHERE id = ?",
                (fault_tree.name, fault_tree.conversation_id, fault_tree.id),
            )
            # 替换节点和边：先删后插
            conn.execute("DELETE FROM fault_tree_nodes WHERE tree_id = ?", (fault_tree.id,))
            conn.execute("DELETE FROM fault_tree_edges WHERE tree_id = ?", (fault_tree.id,))
            self._insert_nodes(conn, fault_tree.id, fault_tree.nodes)
            self._insert_edges(conn, fault_tree.id, fault_tree.edges)
            conn.commit()
        finally:
            conn.close()

    def delete(self, tree_id: str) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM fault_tree_nodes WHERE tree_id = ?", (tree_id,))
            conn.execute("DELETE FROM fault_tree_edges WHERE tree_id = ?", (tree_id,))
            conn.execute("DELETE FROM fault_trees WHERE id = ?", (tree_id,))
            conn.commit()
        finally:
            conn.close()

    # ── private helpers ──

    @staticmethod
    def _insert_nodes(conn, tree_id: str, nodes: list[FaultTreeNode]) -> None:
        for n in nodes:
            conn.execute(
                "INSERT INTO fault_tree_nodes (id, tree_id, label, node_type, gate_type, remark, sources) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (n.id, tree_id, n.label, n.node_type.value,
                 n.gate_type.value if n.gate_type else None, n.remark,
                 json.dumps(n.sources, ensure_ascii=False)),
            )

    @staticmethod
    def _insert_edges(conn, tree_id: str, edges: list[FaultTreeEdge]) -> None:
        for e in edges:
            conn.execute(
                "INSERT INTO fault_tree_edges (id, tree_id, source_id, target_id) "
                "VALUES (?, ?, ?, ?)",
                (e.id, tree_id, e.source_id, e.target_id),
            )

    @staticmethod
    def _build_tree(conn, row) -> FaultTree:
        tree_id = row["id"]

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
