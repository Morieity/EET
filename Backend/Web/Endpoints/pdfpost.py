from flask import Blueprint, jsonify, request
from Backend.Application.UseCases.upload_pdf_use_case import UploadPdfUseCase

# 已废弃：此文件中的 PDF 上传接口已被知识库文档管理接口取代，保留此文件仅供参考和未来可能的功能扩展。

def create_blueprint(
    upload_pdf_use_case: UploadPdfUseCase,
) -> Blueprint:
    """创建并返回 PDF 上传和向量化的 HTTP 路由。"""
    blueprint = Blueprint("pdf_endpoints", __name__)

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
