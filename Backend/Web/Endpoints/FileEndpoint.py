import threading
import time
import json
from flask import Blueprint, request, Response
from Backend.Application.UseCases.ImportFileUseCase import ImportFileUseCase
from Backend.Application.UseCases.DeleteFileUseCase import DeleteFileUseCase
from Backend.Application.Interfaces.IFileRepository import IFileRepository

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md"}

file_bp = Blueprint("files", __name__, url_prefix="/api/files")

# 用于缓存后台向量化任务的状态变更事件，key 是原始 `file_name`。
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
        """上传文件并启动异步向量化。

        实际接收 `multipart/form-data`，字段名固定为 `file`。
        允许的扩展名是 `.pdf` / `.doc` / `.docx` / `.txt` / `.md`。

        成功时立即返回 `File.to_dict()`，此时状态固定为 `pending`:
        {
            "id": str,
            "file_name": str,
            "file_type": "pdf" | "word" | "txt" | "markdown",
            "created_at": ISO8601 字符串,
            "status": "pending",
        }

        接口返回 202 之后，后台线程才会继续做切分、向量化和状态更新。
        """
        if "file" not in request.files:
            return {"error": "No file provided"}, 400

        uploaded_file = request.files["file"]
        if not uploaded_file.filename:
            return {"error": "File name is empty"}, 400

        if not _is_allowed(uploaded_file.filename):
            return {"error": f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}, 400

        file_entity = import_use_case.receive_file(uploaded_file, uploaded_file.filename)

        # 启动后台线程执行向量化，并把最终状态暂存给 SSE 接口读取。
        _status_events[file_entity.file_name] = None

        def _embed_task(fname):
            import_use_case.embed_file(fname)
            # 从数据库重新读取最终状态，实际会得到 pending / embedded / failed 之一。
            updated = file_repository.get_by_name(fname)
            _status_events[fname] = updated.status.value if updated else "failed"

        thread = threading.Thread(target=_embed_task, args=(file_entity.file_name,), daemon=True)
        thread.start()

        return file_entity.to_dict(), 202

    @file_bp.route("", methods=["GET"])
    def list_files():
        """返回全部文件记录。

        每个元素都来自 `File.to_dict()`:
        {
            "id": str,
            "file_name": str,
            "file_type": "pdf" | "word" | "txt" | "markdown",
            "created_at": ISO8601 字符串,
            "status": "pending" | "embedded" | "failed",
        }
        """
        files = file_repository.get_all()
        return [f.to_dict() for f in files]

    @file_bp.route("/<file_name>", methods=["DELETE"])
    def delete_file(file_name: str):
        """按原始文件名删除文件、向量数据和数据库记录。

        路径参数传的是 `file_name`，不是文件 ID。
        成功返回 `{"message": "File deleted"}`，文件不存在时返回 404 错误 JSON。
        """
        try:
            delete_use_case.execute(file_name)
            return {"message": "File deleted"}, 200
        except ValueError as e:
            return {"error": str(e)}, 404

    @file_bp.route("/<file_name>/status", methods=["GET"])
    def file_status_sse(file_name: str):
        """推送指定文件的向量化状态。

        路径参数传的是上传时的原始 `file_name`。
        实际返回 `text/event-stream`，每次只发送 `data`，不带自定义 event 名:

        {"status": "pending" | "embedded" | "failed" | "timeout"}

        连接建立后会先发送数据库中的当前状态；如果当前已经是 `embedded` 或 `failed`，
        流会立刻结束。否则最多等待 120 秒，等后台线程把最终状态写入 `_status_events`。
        """
        file_entity = file_repository.get_by_name(file_name)
        if file_entity is None:
            return {"error": "File not found"}, 404

        def event_stream():
            # 先发送当前数据库状态，前端可以立即知道文件现在处于哪个阶段。
            yield f"data: {json.dumps({'status': file_entity.status.value})}\n\n"

            # 如果已经结束，就不再继续轮询后台状态。
            if file_entity.status.value in ("embedded", "failed"):
                return

            # 轮询等待后台线程写入最终状态；最长等待 120 秒。
            for _ in range(120):
                status = _status_events.get(file_name)
                if status is not None:
                    yield f"data: {json.dumps({'status': status})}\n\n"
                    _status_events.pop(file_name, None)
                    return
                time.sleep(1)

            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"

        return Response(event_stream(), mimetype="text/event-stream")

    @file_bp.route("/open-folder", methods=["POST"])
    def open_uploads_folder():
        """在系统资源管理器中打开 uploads 文件夹。"""
        import os
        import platform
        import subprocess

        folder = os.path.abspath("uploads")
        os.makedirs(folder, exist_ok=True)
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(folder)
            elif system == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            return {"message": "Folder opened"}, 200
        except Exception as e:
            return {"error": str(e)}, 500

    return file_bp
