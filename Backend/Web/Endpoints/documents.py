"""Document endpoints — 知识库文档管理 Blueprint。"""
from flask import Blueprint, jsonify, request

from Backend.Application.UseCases.upload_document_use_case import UploadDocumentUseCase


def create_blueprint(upload_document_use_case: UploadDocumentUseCase) -> Blueprint:
    blueprint = Blueprint("document_endpoints", __name__, url_prefix="/api/documents")

    @blueprint.route("/upload", methods=["POST"])
    def upload_document():
        try:
            file = request.files.get("file")
            result = upload_document_use_case.execute(file)
            return jsonify(result), 200
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400
        except Exception as exc:
            return jsonify({"status": "error", "message": "Internal processing error"}), 500

    return blueprint
