import json
import logging
from flask import Blueprint, request
from Backend.Application.UseCases.FaultTreeUseCase import FaultTreeUseCase

fault_tree_bp = Blueprint("fault_tree", __name__)
logger = logging.getLogger(__name__)


def create_fault_tree_blueprint(fault_tree_use_case: FaultTreeUseCase) -> Blueprint:

    @fault_tree_bp.route("/api/fault-trees", methods=["GET"])
    def list_fault_trees():
        trees = fault_tree_use_case.get_all()
        return [t.to_dict() for t in trees]

    @fault_tree_bp.route("/api/fault-trees/<tree_id>", methods=["GET"])
    def get_fault_tree(tree_id: str):
        tree = fault_tree_use_case.get_by_id(tree_id)
        if tree is None:
            return {"error": "Fault tree not found"}, 404
        return tree.to_dict()

    @fault_tree_bp.route("/api/fault-trees/conversation/<conversation_id>", methods=["GET"])
    def get_fault_tree_by_conversation(conversation_id: str):
        tree = fault_tree_use_case.get_by_conversation_id(conversation_id)
        if tree is None:
            return {"error": "No fault tree found for this conversation"}, 404
        return tree.to_dict()

    @fault_tree_bp.route("/api/fault-trees/<tree_id>", methods=["PUT"])
    def update_fault_tree(tree_id: str):
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
        try:
            fault_tree_use_case.delete(tree_id)
            return {"message": "Fault tree deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception:
            logger.exception("Failed to delete fault tree: %s", tree_id)
            return {"error": "Internal server error"}, 500

    return fault_tree_bp
