import json
import logging
import os

from flask import Blueprint, request, Response

from Backend.Application.UseCases.ImportWorkOrderUseCase import ImportWorkOrderUseCase
from Backend.Application.UseCases.WorkOrderUseCase import WorkOrderUseCase

logger = logging.getLogger(__name__)

# 工单导入支持结构化表格和自由文本两类入口。
ALLOWED_IMPORT_EXTENSIONS = {".csv", ".xlsx", ".xls", ".txt", ".md"}


def _is_allowed_import(filename: str) -> bool:
    """校验上传文件扩展名是否在允许列表中。"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_IMPORT_EXTENSIONS


def _error_status_code(error: ValueError) -> int:
    """把业务异常映射为更合适的 HTTP 状态码。"""
    message = str(error)
    if "not found" in message.lower():
        return 404
    if "already exists" in message.lower():
        return 409
    return 400


def create_work_order_blueprint(
    import_use_case: ImportWorkOrderUseCase,
    work_order_use_case: WorkOrderUseCase,
    chat_use_case=None,
) -> Blueprint:
    """创建工单模块 Blueprint。"""
    work_order_bp = Blueprint("work_orders", __name__, url_prefix="/api/work-orders")

    @work_order_bp.route("/import", methods=["POST"])
    def import_work_orders():
        """导入工单。

        支持两种请求方式：
        1. multipart/form-data 上传 CSV/Excel/TXT/MD 文件。
        2. JSON body 直接提交 text 字段。
        """
        if "file" in request.files:
            uploaded_file = request.files["file"]
            if not uploaded_file.filename:
                return {"error": "File name is empty"}, 400
            if not _is_allowed_import(uploaded_file.filename):
                return {
                    "error": f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_IMPORT_EXTENSIONS))}"
                }, 400
            try:
                result = import_use_case.import_from_upload(uploaded_file, uploaded_file.filename)
                return result, 202
            except ImportError as exc:
                return {"error": str(exc)}, 500
            except ValueError as exc:
                return {"error": str(exc)}, 400
            except Exception:
                logger.exception("Failed to import work orders from file")
                return {"error": "Internal server error"}, 500

        data = request.get_json(silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return {"error": "Provide a file upload or JSON body with text"}, 400
        source_file = (data.get("source_file") or "manual_text.txt").strip() or "manual_text.txt"
        try:
            result = import_use_case.import_from_text(text, source_file=source_file)
            return result, 202
        except ValueError as exc:
            return {"error": str(exc)}, 400
        except Exception:
            logger.exception("Failed to import work orders from text")
            return {"error": "Internal server error"}, 500

    @work_order_bp.route("", methods=["POST"])
    def create_work_order():
        """创建单条结构化工单，并立即触发后台处理。"""
        data = request.get_json(silent=True) or {}
        try:
            work_order = work_order_use_case.create(data)
            import_use_case.process_async([work_order.id])
            return work_order.to_dict(), 201
        except ValueError as exc:
            return {"error": str(exc)}, _error_status_code(exc)
        except Exception:
            logger.exception("Failed to create work order")
            return {"error": "Internal server error"}, 500

    @work_order_bp.route("", methods=["GET"])
    def list_work_orders():
        """按可选过滤条件返回工单列表。"""
        device_name = request.args.get("device_name")
        fault_category = request.args.get("fault_category")
        status = request.args.get("status")
        try:
            work_orders = work_order_use_case.get_all(
                device_name=device_name,
                fault_category=fault_category,
                status=status,
            )
            counts = work_order_use_case.get_aggregated_counts([wo.id for wo in work_orders])
            result = []
            for wo in work_orders:
                d = wo.to_dict()
                c = counts.get(wo.id, {})
                d["conversation_count"] = c.get("conversation_count", 0)
                d["fault_tree_count"] = c.get("fault_tree_count", 0)
                result.append(d)
            return result
        except ValueError as exc:
            return {"error": str(exc)}, 400

    @work_order_bp.route("/device/<path:device_name>/stats", methods=["GET"])
    def get_device_stats(device_name: str):
        """返回指定设备的工单统计信息。"""
        return work_order_use_case.get_device_stats(device_name)

    @work_order_bp.route("/<work_order_id>", methods=["GET"])
    def get_work_order(work_order_id: str):
        """返回单条工单详情。"""
        work_order = work_order_use_case.get_by_id(work_order_id)
        if work_order is None:
            return {"error": "Work order not found"}, 404
        d = work_order.to_dict()
        convs = work_order_use_case.get_conversations(work_order_id)
        d["conversation_count"] = len(convs)
        d["fault_tree_count"] = len(work_order_use_case.get_fault_trees(work_order_id))
        return d

    @work_order_bp.route("/<work_order_id>", methods=["PUT"])
    def update_work_order(work_order_id: str):
        """更新工单，并重新触发向量化和图谱处理。"""
        data = request.get_json(silent=True) or {}
        try:
            work_order = work_order_use_case.update(work_order_id, data)
            import_use_case.process_async([work_order.id])
            return work_order.to_dict()
        except ValueError as exc:
            return {"error": str(exc)}, _error_status_code(exc)
        except Exception:
            logger.exception("Failed to update work order: %s", work_order_id)
            return {"error": "Internal server error"}, 500

    @work_order_bp.route("/<work_order_id>", methods=["DELETE"])
    def delete_work_order(work_order_id: str):
        """删除工单及其关联的向量/图谱数据。"""
        try:
            work_order_use_case.delete(work_order_id)
            return {"message": "Work order deleted"}, 200
        except ValueError as exc:
            return {"error": str(exc)}, _error_status_code(exc)
        except Exception:
            logger.exception("Failed to delete work order: %s", work_order_id)
            return {"error": "Internal server error"}, 500

    # ── T032: 工单关联对话列表 ──

    @work_order_bp.route("/<work_order_id>/conversations", methods=["GET"])
    def get_work_order_conversations(work_order_id: str):
        wo = work_order_use_case.get_by_id(work_order_id)
        if wo is None:
            return {"error": "Work order not found"}, 404
        convs = work_order_use_case.get_conversations(work_order_id)
        return {
            "work_order_id": work_order_id,
            "conversations": [c.to_dict() for c in convs],
        }

    # ── T033: 工单关联故障树列表 ──

    @work_order_bp.route("/<work_order_id>/fault-trees", methods=["GET"])
    def get_work_order_fault_trees(work_order_id: str):
        wo = work_order_use_case.get_by_id(work_order_id)
        if wo is None:
            return {"error": "Work order not found"}, 404
        trees = work_order_use_case.get_fault_trees(work_order_id)
        return {
            "work_order_id": work_order_id,
            "fault_trees": [
                {
                    "id": t.id,
                    "name": t.name,
                    "conversation_id": t.conversation_id,
                    "node_count": len(t.nodes),
                    "created_at": t.created_at.isoformat(),
                }
                for t in trees
            ],
        }

    # ── T034: 一键分析 ──

    @work_order_bp.route("/<work_order_id>/analyze", methods=["POST"])
    def analyze_work_order(work_order_id: str):
        if chat_use_case is None:
            return {"error": "Chat service not available"}, 503
        wo = work_order_use_case.get_by_id(work_order_id)
        if wo is None:
            return {"error": "Work order not found"}, 404
        data = request.get_json(silent=True) or {}
        initial_prompt = (data.get("initial_prompt") or "").strip()
        if not initial_prompt:
            initial_prompt = (
                f"基于工单 {wo.order_no} 的故障现象「{wo.fault_phenomenon}」，"
                f"请分析可能的故障原因并构建故障树"
            )

        def _format_sse(event):
            event_type = event.get("type", "")
            payload = {k: v for k, v in event.items() if k != "type"}
            d = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            return f"event: {event_type}\ndata: {d}\n\n"

        def event_stream():
            try:
                for event in chat_use_case.execute(initial_prompt, work_order_id=work_order_id):
                    yield _format_sse(event)
            except Exception:
                logger.exception("SSE stream error during work order analysis")
                err = json.dumps({"message": "服务器内部错误"}, ensure_ascii=False)
                yield f"event: error\ndata: {err}\n\n"

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── T035: 工单故障树绑定/解绑 ──

    @work_order_bp.route("/<work_order_id>/fault-tree", methods=["PUT"])
    def link_fault_tree(work_order_id: str):
        data = request.get_json(silent=True) or {}
        fault_tree_id = (data.get("fault_tree_id") or "").strip()
        if not fault_tree_id:
            return {"error": "fault_tree_id is required"}, 400
        try:
            wo = work_order_use_case.link_fault_tree(work_order_id, fault_tree_id)
            return {"id": wo.id, "fault_tree_id": wo.fault_tree_id, "message": "Fault tree linked successfully"}
        except ValueError as exc:
            return {"error": str(exc)}, _error_status_code(exc)

    @work_order_bp.route("/<work_order_id>/fault-tree", methods=["DELETE"])
    def unlink_fault_tree(work_order_id: str):
        try:
            wo = work_order_use_case.unlink_fault_tree(work_order_id)
            return {"id": wo.id, "fault_tree_id": None, "message": "Fault tree unlinked successfully"}
        except ValueError as exc:
            return {"error": str(exc)}, _error_status_code(exc)

    return work_order_bp