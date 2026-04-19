import logging

from Backend.Application.Interfaces.IGraphRepository import IGraphRepository
from Backend.Application.Interfaces.IVectorStoreRepository import IVectorStoreRepository
from Backend.Application.Interfaces.IWorkOrderRepository import IWorkOrderRepository
from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Domain.Entities.work_order import WorkOrder

logger = logging.getLogger(__name__)


class WorkOrderUseCase:
    """工单 CRUD 用例。

    这里聚焦同步业务操作：创建、查询、更新、删除和统计。
    向量化与图谱构建交给 ImportWorkOrderUseCase 负责。
    """

    def __init__(
        self,
        work_order_repository: IWorkOrderRepository,
        vector_store_repository: IVectorStoreRepository,
        graph_repository: IGraphRepository | None = None,
    ):
        self._repo = work_order_repository
        self._vector_store = vector_store_repository
        self._graph_repo = graph_repository

    def create(self, data: dict) -> WorkOrder:
        """创建单条工单，并默认进入待处理状态。"""
        self._validate_required_fields(data)
        work_order = WorkOrder.from_dict({
            **data,
            "status": WorkOrderStatus.PENDING.value,
            "processing_error": "",
        })
        self._repo.save(work_order)
        logger.info("Work order created: %s", work_order.id)
        return work_order

    def get_by_id(self, work_order_id: str) -> WorkOrder | None:
        """查询单条工单详情。"""
        return self._repo.get_by_id(work_order_id)

    def get_all(
        self,
        device_name: str | None = None,
        fault_category: str | None = None,
        status: str | None = None,
    ) -> list[WorkOrder]:
        """查询工单列表，并把字符串状态转换成枚举。"""
        status_enum = WorkOrderStatus(status) if status else None
        return self._repo.get_all(device_name=device_name, fault_category=fault_category, status=status_enum)

    def update(self, work_order_id: str, data: dict) -> WorkOrder:
        """更新工单，并把状态重置为 PENDING 以触发重新处理。"""
        existing = self._repo.get_by_id(work_order_id)
        if existing is None:
            raise ValueError(f"Work order not found: {work_order_id}")
        merged = {
            **existing.to_dict(),
            **data,
            "id": work_order_id,
            "created_at": existing.created_at.isoformat(),
            "status": WorkOrderStatus.PENDING.value,
            "processing_error": "",
        }
        self._validate_required_fields(merged)
        updated = WorkOrder.from_dict(merged)
        self._repo.update(updated)
        logger.info("Work order updated: %s", work_order_id)
        return updated

    def delete(self, work_order_id: str) -> None:
        """删除工单，并同步清理向量库和图谱中的关联数据。"""
        existing = self._repo.get_by_id(work_order_id)
        if existing is None:
            raise ValueError(f"Work order not found: {work_order_id}")

        # 文档向量以工单 ID 作为来源标识存储。
        self._vector_store.delete_by_file_name(existing.id)
        graph_source = self.graph_source(existing.id)
        # 图谱实体和关系使用独立 source 标识，避免误删普通文档数据。
        if hasattr(self._vector_store, "delete_entities_by_file"):
            self._vector_store.delete_entities_by_file(graph_source)
        if hasattr(self._vector_store, "delete_relations_by_file"):
            self._vector_store.delete_relations_by_file(graph_source)
        if self._graph_repo is not None:
            self._graph_repo.remove_by_file(graph_source)

        self._repo.delete(work_order_id)
        logger.info("Work order deleted: %s", work_order_id)

    def get_device_stats(self, device_name: str) -> dict:
        """返回设备维度的工单统计。"""
        return self._repo.get_device_stats(device_name)

    @staticmethod
    def graph_source(work_order_id: str) -> str:
        """生成工单图谱来源标识。"""
        return f"work_order::{work_order_id}"

    @staticmethod
    def _validate_required_fields(data: dict) -> None:
        """校验创建/更新时必须存在的关键字段。"""
        if not (data.get("order_no") or "").strip():
            raise ValueError("order_no is required")
        if not (data.get("device_name") or "").strip():
            raise ValueError("device_name is required")
