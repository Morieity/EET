"""故障树 API。

本文件中的 `GET` / `PUT` 接口都围绕同一种故障树 JSON 结构:
{
    "id": str,
    "name": str,
    "nodes": [
        {
            "id": str,
            "label": str,
            "node_type": "event" | "gate",
            "remark": str,
            "gate_type": "AND" | "OR",  # 仅 gate 节点存在
        },
        ...
    ],
    "edges": [
        {"id": str, "source_id": str, "target_id": str},
        ...
    ],
    "created_at": ISO8601 字符串,
    "conversation_id": str | None,
}
"""

import json
import logging
from flask import Blueprint, request
from Backend.Application.UseCases.FaultTreeUseCase import FaultTreeUseCase

fault_tree_bp = Blueprint("fault_tree", __name__)
logger = logging.getLogger(__name__)


def create_fault_tree_blueprint(fault_tree_use_case: FaultTreeUseCase) -> Blueprint:

    @fault_tree_bp.route("/api/fault-trees", methods=["GET"])
    def list_fault_trees():
        """返回全部故障树，列表中的每个元素都使用模块顶部定义的完整结构。"""
        trees = fault_tree_use_case.get_all()
        return [t.to_dict() for t in trees]

    @fault_tree_bp.route("/api/fault-trees/<tree_id>", methods=["GET"])
    def get_fault_tree(tree_id: str):
        """按 `tree_id` 返回单棵故障树；找不到时返回 404 错误 JSON。"""
        tree = fault_tree_use_case.get_by_id(tree_id)
        if tree is None:
            return {"error": "Fault tree not found"}, 404
        return tree.to_dict()

    @fault_tree_bp.route("/api/fault-trees/conversation/<conversation_id>", methods=["GET"])
    def get_fault_tree_by_conversation(conversation_id: str):
        """按 `conversation_id` 返回与该对话关联的故障树。

        返回体仍然是完整故障树结构；如果该对话还没有生成故障树，则返回:
        {"error": "No fault tree found for this conversation"}
        """
        tree = fault_tree_use_case.get_by_conversation_id(conversation_id)
        if tree is None:
            return {"error": "No fault tree found for this conversation"}, 404
        return tree.to_dict()

    @fault_tree_bp.route("/api/fault-trees/<tree_id>", methods=["PUT"])
    def update_fault_tree(tree_id: str):
        """用完整树结构覆盖更新指定故障树。

        实际接收 JSON，不是 patch，而是修改后的整棵树:
        {
            "name": str,
            "nodes": [
                {
                    "id": str,
                    "label": str,
                    "node_type": "event" | "gate",
                    "remark": str,            # 可选
                    "gate_type": "AND" | "OR" # 仅 gate 节点需要
                },
                ...
            ],
            "edges": [
                {"id": str, "source_id": str, "target_id": str},
                ...
            ],
        }

        这三个字段都必须存在且非空；成功后返回更新后的完整故障树。
        `created_at` 和 `conversation_id` 会沿用原记录中的值。
        """
        data = request.get_json(silent=True) or {}
        if not data.get("name") or not data.get("nodes") or not data.get("edges"):
            return {"error": "name, nodes, and edges are required"}, 400
        try:
            tree = fault_tree_use_case.update(tree_id, data)
            return tree.to_dict()
        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception:
            logger.exception("Failed to update fault tree: %s", tree_id)
            return {"error": "Internal server error"}, 500

    @fault_tree_bp.route("/api/fault-trees/<tree_id>", methods=["DELETE"])
    def delete_fault_tree(tree_id: str):
        """删除指定故障树。

        成功返回:
        {"message": "Fault tree deleted"}

        树不存在时返回:
        {"error": "Fault tree not found: <tree_id>"}
        """
        try:
            fault_tree_use_case.delete(tree_id)
            return {"message": "Fault tree deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception:
            logger.exception("Failed to delete fault tree: %s", tree_id)
            return {"error": "Internal server error"}, 500

    return fault_tree_bp
