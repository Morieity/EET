from datetime import datetime
import sqlite3

from Backend.Application.Interfaces.IWorkOrderRepository import IWorkOrderRepository
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Domain.Entities.work_order import WorkOrder
from Backend.Infrastructure.persistence.database import get_connection


class SQLiteWorkOrderRepository(IWorkOrderRepository):
    """基于 SQLite 的工单仓储实现。"""

    def save(self, work_order: WorkOrder) -> None:
        """插入单条工单；order_no 冲突时转为业务异常。"""
        conn = get_connection()
        try:
            conn.execute(
                """
                INSERT INTO work_orders (
                    id, order_no, device_name, device_code, fault_phenomenon,
                    fault_cause, fault_category, severity, solution,
                    occurrence_time, resolution_time, operator, status,
                    source_file, raw_text, processing_error, created_at, fault_tree_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._entity_to_params(work_order),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Work order already exists: {work_order.order_no}") from exc
        finally:
            conn.close()

    def save_many(self, work_orders: list[WorkOrder]) -> None:
        """批量插入工单，适合导入接口一次写入多行。"""
        conn = get_connection()
        try:
            conn.executemany(
                """
                INSERT INTO work_orders (
                    id, order_no, device_name, device_code, fault_phenomenon,
                    fault_cause, fault_category, severity, solution,
                    occurrence_time, resolution_time, operator, status,
                    source_file, raw_text, processing_error, created_at, fault_tree_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._entity_to_params(work_order) for work_order in work_orders],
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("One or more work orders already exist") from exc
        finally:
            conn.close()

    def get_by_id(self, work_order_id: str) -> WorkOrder | None:
        """按主键查询单条工单。"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM work_orders WHERE id = ?", (work_order_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        finally:
            conn.close()

    def get_by_order_no(self, order_no: str) -> WorkOrder | None:
        """按业务编号查询工单。"""
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM work_orders WHERE order_no = ?", (order_no,)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        finally:
            conn.close()

    def get_all(
        self,
        device_name: str | None = None,
        fault_category: str | None = None,
        status: WorkOrderStatus | None = None,
    ) -> list[WorkOrder]:
        """构造带可选过滤条件的查询语句。"""
        conn = get_connection()
        try:
            query = "SELECT * FROM work_orders WHERE 1=1"
            params: list[str] = []
            # 过滤条件按需拼接，避免为每种组合单独写 SQL。
            if device_name:
                query += " AND device_name = ?"
                params.append(device_name)
            if fault_category:
                query += " AND fault_category = ?"
                params.append(fault_category)
            if status:
                query += " AND status = ?"
                params.append(status.value)
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    def update(self, work_order: WorkOrder) -> None:
        """全量更新工单字段。"""
        conn = get_connection()
        try:
            cursor = conn.execute(
                """
                UPDATE work_orders
                SET order_no = ?, device_name = ?, device_code = ?, fault_phenomenon = ?,
                    fault_cause = ?, fault_category = ?, severity = ?, solution = ?,
                    occurrence_time = ?, resolution_time = ?, operator = ?, status = ?,
                    source_file = ?, raw_text = ?, processing_error = ?, fault_tree_id = ?
                WHERE id = ?
                """,
                (
                    work_order.order_no,
                    work_order.device_name,
                    work_order.device_code,
                    work_order.fault_phenomenon,
                    work_order.fault_cause,
                    work_order.fault_category,
                    work_order.severity,
                    work_order.solution,
                    work_order.occurrence_time.isoformat() if work_order.occurrence_time else None,
                    work_order.resolution_time.isoformat() if work_order.resolution_time else None,
                    work_order.operator,
                    work_order.status.value,
                    work_order.source_file,
                    work_order.raw_text,
                    work_order.processing_error,
                    work_order.fault_tree_id,
                    work_order.id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Work order not found: {work_order.id}")
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Work order already exists: {work_order.order_no}") from exc
        finally:
            conn.close()

    def update_status(
        self,
        work_order_id: str,
        status: WorkOrderStatus,
        processing_error: str = "",
    ) -> None:
        """只更新异步处理状态，避免每次都覆盖整条记录。"""
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE work_orders SET status = ?, processing_error = ? WHERE id = ?",
                (status.value, processing_error, work_order_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, work_order_id: str) -> None:
        """删除工单主表记录。"""
        conn = get_connection()
        try:
            conn.execute("DELETE FROM work_orders WHERE id = ?", (work_order_id,))
            conn.commit()
        finally:
            conn.close()

    def get_device_stats(self, device_name: str) -> dict:
        """聚合设备维度统计，直接返回给 API 层使用。"""
        conn = get_connection()
        try:
            # 不同维度单独聚合，便于前端直接绘图或展示标签统计。
            total_row = conn.execute(
                "SELECT COUNT(*) AS total FROM work_orders WHERE device_name = ?",
                (device_name,),
            ).fetchone()
            status_rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM work_orders WHERE device_name = ? GROUP BY status",
                (device_name,),
            ).fetchall()
            category_rows = conn.execute(
                "SELECT fault_category, COUNT(*) AS count FROM work_orders WHERE device_name = ? GROUP BY fault_category",
                (device_name,),
            ).fetchall()
            severity_rows = conn.execute(
                "SELECT severity, COUNT(*) AS count FROM work_orders WHERE device_name = ? GROUP BY severity",
                (device_name,),
            ).fetchall()
            return {
                "device_name": device_name,
                "total": total_row["total"] if total_row else 0,
                "by_status": {row["status"]: row["count"] for row in status_rows if row["status"]},
                "by_category": {
                    row["fault_category"]: row["count"]
                    for row in category_rows
                    if row["fault_category"]
                },
                "by_severity": {
                    row["severity"]: row["count"]
                    for row in severity_rows
                    if row["severity"]
                },
            }
        finally:
            conn.close()

    def get_by_device_name(self, device_name: str) -> list[WorkOrder]:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM work_orders WHERE device_name = ? ORDER BY created_at DESC",
                (device_name,),
            ).fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    def link_fault_tree(self, work_order_id: str, fault_tree_id: str) -> bool:
        conn = get_connection()
        try:
            cursor = conn.execute(
                "UPDATE work_orders SET fault_tree_id = ? WHERE id = ?",
                (fault_tree_id, work_order_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def unlink_fault_tree(self, work_order_id: str) -> bool:
        conn = get_connection()
        try:
            cursor = conn.execute(
                "UPDATE work_orders SET fault_tree_id = NULL WHERE id = ?",
                (work_order_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def _entity_to_params(work_order: WorkOrder) -> tuple:
        """把领域实体转换成 SQL 参数顺序。"""
        return (
            work_order.id,
            work_order.order_no,
            work_order.device_name,
            work_order.device_code,
            work_order.fault_phenomenon,
            work_order.fault_cause,
            work_order.fault_category,
            work_order.severity,
            work_order.solution,
            work_order.occurrence_time.isoformat() if work_order.occurrence_time else None,
            work_order.resolution_time.isoformat() if work_order.resolution_time else None,
            work_order.operator,
            work_order.status.value,
            work_order.source_file,
            work_order.raw_text,
            work_order.processing_error,
            work_order.created_at.isoformat(),
            work_order.fault_tree_id,
        )

    @staticmethod
    def _row_to_entity(row) -> WorkOrder:
        """把 SQLite 行记录恢复为领域实体。"""
        return WorkOrder(
            work_order_id=row["id"],
            order_no=row["order_no"],
            device_name=row["device_name"],
            device_code=row["device_code"] or "",
            fault_phenomenon=row["fault_phenomenon"] or "",
            fault_cause=row["fault_cause"] or "",
            fault_category=row["fault_category"] or "",
            severity=row["severity"] or "",
            solution=row["solution"] or "",
            occurrence_time=datetime.fromisoformat(row["occurrence_time"]) if row["occurrence_time"] else None,
            resolution_time=datetime.fromisoformat(row["resolution_time"]) if row["resolution_time"] else None,
            operator=row["operator"] or "",
            status=WorkOrderStatus(row["status"]),
            source_file=row["source_file"] or "",
            raw_text=row["raw_text"] or "",
            processing_error=row["processing_error"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            fault_tree_id=row["fault_tree_id"] if "fault_tree_id" in row.keys() else None,
        )