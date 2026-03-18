from flask import Blueprint, jsonify, request
from Backend.Application.UseCases.ask_pdf_use_case import AskPdfUseCase
from Backend.Application.UseCases.chat_use_case import ChatUseCase
from Backend.Application.UseCases.upload_pdf_use_case import UploadPdfUseCase


def create_blueprint(
    chat_use_case: ChatUseCase,
    ask_pdf_use_case: AskPdfUseCase,
    upload_pdf_use_case: UploadPdfUseCase,
) -> Blueprint:
    """创建并返回聊天、文档问答和文档上传的 HTTP 路由。"""
    blueprint = Blueprint("llm_endpoints", __name__)

    @blueprint.route("/ai", methods=["POST"])
    def ai_post():
        """处理直接的模型对话请求。"""
        json_content = request.json or {}
        query = json_content.get("query", "")
        try:
            answer = chat_use_case.execute(query)
            return {"answer": answer}
        except Exception as exc:
            return jsonify({"status": "Error", "message": str(exc)}), 400

    @blueprint.route("/ask_pdf", methods=["POST"])
    def ask_pdf_post():
        """处理基于已索引 PDF 的检索增强问答请求。"""
        json_content = request.json or {}
        query = json_content.get("query", "")
        try:
            answer, sources = ask_pdf_use_case.execute(query)
            return {"answer": answer, "sources": sources}
        except Exception as exc:
            return jsonify({"status": "Error", "message": str(exc)}), 500

    @blueprint.route("/pdf", methods=["POST"])
    def pdf_post():
        """处理 PDF 上传并持久化向量索引。"""
        try:
            file = request.files.get("file")
            result = upload_pdf_use_case.execute(file)
            return result, 200
        except Exception as exc:
            return jsonify({"status": "Error", "message": str(exc)}), 400

    return blueprint