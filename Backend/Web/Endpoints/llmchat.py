from flask import Blueprint, jsonify, request
from Backend.Application.UseCases.ask_pdf_use_case import AskPdfUseCase

# 已废弃：此文件中的聊天接口已被诊断会话管理接口取代，保留此文件仅供参考和未来可能的功能扩展。

def create_blueprint(
    ask_pdf_use_case: AskPdfUseCase,
) -> Blueprint:
    """创建并返回基于 RAG 的聊天 HTTP 路由。"""
    blueprint = Blueprint("llm_endpoints", __name__)

    @blueprint.route("/chat", methods=["POST"])
    def chat_post():
        """处理基于 RAG 的聊天请求。"""
        json_content = request.json or {}
        query = json_content.get("query", "")
        k = json_content.get("k", 20)
        score_threshold = json_content.get("score_threshold", 0.1)

        try:
            answer, sources = ask_pdf_use_case.execute(
                query=query,
                k=int(k),
                score_threshold=float(score_threshold),
            )
            return {"answer": answer, "sources": sources}
        except Exception as exc:
            return jsonify({"status": "Error", "message": str(exc)}), 500

    return blueprint