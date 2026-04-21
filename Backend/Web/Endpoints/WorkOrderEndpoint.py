import logging
import os

from flask import Blueprint, request

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
            return [work_order.to_dict() for work_order in work_orders]
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
        return work_order.to_dict()

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

    return work_order_bp