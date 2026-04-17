import logging

from Backend.Application.Interfaces.IConversationRepository import IConversationRepository
from Backend.Application.Interfaces.IFaultTreeRepository import IFaultTreeRepository
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
        conversation_repository: IConversationRepository | None = None,
        fault_tree_repository: IFaultTreeRepository | None = None,
    ):
        self._repo = work_order_repository
        self._vector_store = vector_store_repository
        self._graph_repo = graph_repository
        self._conversation_repo = conversation_repository
        self._fault_tree_repo = fault_tree_repository

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

    # ── 工单驱动故障树：关联查询与绑定方法 ──

    def get_conversations(self, work_order_id: str):
        """获取工单下的对话列表。"""
        if self._conversation_repo is None:
            return []
        return self._conversation_repo.get_by_work_order_id(work_order_id)

    def get_fault_trees(self, work_order_id: str) -> list:
        """获取工单关联的所有故障树（通过对话间接查询）。"""
        if self._conversation_repo is None or self._fault_tree_repo is None:
            return []
        conversations = self._conversation_repo.get_by_work_order_id(work_order_id)
        trees = []
        for conv in conversations:
            tree = self._fault_tree_repo.get_by_conversation_id(conv.id)
            if tree:
                trees.append(tree)
        return trees

    def get_aggregated_counts(self, work_order_ids: list[str]) -> dict[str, dict]:
        """批量获取工单关联的对话数和故障树数，避免 N+1 查询。

        返回 {work_order_id: {"conversation_count": int, "fault_tree_count": int}}
        """
        counts: dict[str, dict] = {wid: {"conversation_count": 0, "fault_tree_count": 0} for wid in work_order_ids}
        if not self._conversation_repo:
            return counts
        for wid in work_order_ids:
            convs = self._conversation_repo.get_by_work_order_id(wid)
            counts[wid]["conversation_count"] = len(convs)
            if self._fault_tree_repo:
                tree_count = 0
                for conv in convs:
                    if self._fault_tree_repo.get_by_conversation_id(conv.id):
                        tree_count += 1
                counts[wid]["fault_tree_count"] = tree_count
        return counts

    def link_fault_tree(self, work_order_id: str, fault_tree_id: str) -> WorkOrder:
        """绑定工单的最终故障树。"""
        wo = self._repo.get_by_id(work_order_id)
        if wo is None:
            raise ValueError(f"Work order not found: {work_order_id}")
        self._repo.link_fault_tree(work_order_id, fault_tree_id)
        wo.link_fault_tree(fault_tree_id)
        return wo

    def unlink_fault_tree(self, work_order_id: str) -> WorkOrder:
        """解除工单的故障树绑定。"""
        wo = self._repo.get_by_id(work_order_id)
        if wo is None:
            raise ValueError(f"Work order not found: {work_order_id}")
        self._repo.unlink_fault_tree(work_order_id)
        wo.unlink_fault_tree()
        return wo
