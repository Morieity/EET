import threading
import time
import json
from flask import Blueprint, request, Response
from Backend.Application.UseCases.ImportFileUseCase import ImportFileUseCase
from Backend.Application.UseCases.DeleteFileUseCase import DeleteFileUseCase
from Backend.Application.Interfaces.IFileRepository import IFileRepository

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}

file_bp = Blueprint("files", __name__, url_prefix="/api/files")

# 用于存储文件向量化状态变更事件（file_id -> status）
_status_events: dict[str, str | None] = {}


def _is_allowed(filename: str) -> bool:
    import os
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def create_file_blueprint(
    import_use_case: ImportFileUseCase,
    delete_use_case: DeleteFileUseCase,
    file_repository: IFileRepository,
) -> Blueprint:

    @file_bp.route("", methods=["POST"])
    def import_file():
        if "file" not in request.files:
            return {"error": "No file provided"}, 400

        uploaded_file = request.files["file"]
        if not uploaded_file.filename:
            return {"error": "File name is empty"}, 400

        if not _is_allowed(uploaded_file.filename):
            return {"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}, 400

        file_entity = import_use_case.receive_file(uploaded_file, uploaded_file.filename)

        # 启动后台线程执行向量化
        _status_events[file_entity.file_name] = None

        def _embed_task(fname):
            import_use_case.embed_file(fname)
            # 从数据库重新读取最新状态
            updated = file_repository.get_by_name(fname)
            _status_events[fname] = updated.status.value if updated else "failed"

        thread = threading.Thread(target=_embed_task, args=(file_entity.file_name,), daemon=True)
        thread.start()

        return file_entity.to_dict(), 202

    @file_bp.route("", methods=["GET"])
    def list_files():
        files = file_repository.get_all()
        return [f.to_dict() for f in files]

    @file_bp.route("/<file_name>", methods=["DELETE"])
    def delete_file(file_name: str):
        try:
            delete_use_case.execute(file_name)
            return {"message": "File deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    @file_bp.route("/<file_name>/status", methods=["GET"])
    def file_status_sse(file_name: str):
        """SSE 端点：前端监听文件向量化状态变更。"""
        file_entity = file_repository.get_by_name(file_name)
        if file_entity is None:
            return {"error": "File not found"}, 404

        def event_stream():
            # 先发送当前状态
            yield f"data: {json.dumps({'status': file_entity.status.value})}\n\n"

            # 如果已经是终态，直接结束
            if file_entity.status.value in ("embedded", "failed"):
                return

            # 轮询等待状态变更
            for _ in range(120):  # 最多等 120 秒
                status = _status_events.get(file_name)
                if status is not None:
                    yield f"data: {json.dumps({'status': status})}\n\n"
                    _status_events.pop(file_name, None)
                    return
                time.sleep(1)

            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"

        return Response(event_stream(), mimetype="text/event-stream")

    return file_bp
