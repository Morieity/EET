"""Diagnosis endpoints — 诊断会话管理 & 多轮对话 Blueprint。"""
from flask import Blueprint, jsonify, request

from Backend.Application.UseCases.create_session_use_case import CreateSessionUseCase
from Backend.Application.UseCases.diagnose_use_case import DiagnoseUseCase
from Backend.Application.UseCases.get_session_use_case import GetSessionUseCase


def create_blueprint(
    create_session_use_case: CreateSessionUseCase,
    diagnose_use_case: DiagnoseUseCase,
    get_session_use_case: GetSessionUseCase,
) -> Blueprint:
    blueprint = Blueprint("diagnosis_endpoints", __name__, url_prefix="/api/diagnosis")

    @blueprint.route("/sessions", methods=["POST"])
    def create_session():
        json_content = request.json or {}
        initial_message = json_content.get("initial_message", "")
        try:
            result = create_session_use_case.execute(initial_message)
            return jsonify(result), 201
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        except Exception:
            return jsonify({"status": "error", "message": "Internal processing error"}), 500

    @blueprint.route("/sessions/<session_id>/messages", methods=["POST"])
    def send_message(session_id: str):
        json_content = request.json or {}
        message = json_content.get("message", "")
        try:
            result = diagnose_use_case.execute(session_id, message)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        except LookupError:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        except PermissionError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 409
        except Exception:
            return jsonify({"status": "error", "message": "Internal processing error"}), 500

    @blueprint.route("/sessions/<session_id>", methods=["GET"])
    def get_session(session_id: str):
        try:
            result = get_session_use_case.execute(session_id)
            return jsonify(result), 200
        except LookupError:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        except Exception:
            return jsonify({"status": "error", "message": "Internal processing error"}), 500

    return blueprint
