from abc import ABC, abstractmethod

from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus
from Backend.Domain.Entities.work_order import WorkOrder


class IWorkOrderRepository(ABC):
    """工单仓储抽象，屏蔽应用层对具体数据库实现的依赖。"""

    @abstractmethod
    def save(self, work_order: WorkOrder) -> None:
        """保存单条工单。"""
        pass

    @abstractmethod
    def save_many(self, work_orders: list[WorkOrder]) -> None:
        """批量保存工单，用于导入场景。"""
        pass

    @abstractmethod
    def get_by_id(self, work_order_id: str) -> WorkOrder | None:
        """按主键查询单条工单。"""
        pass

    @abstractmethod
    def get_by_order_no(self, order_no: str) -> WorkOrder | None:
        """按业务编号查询工单，便于做幂等校验。"""
        pass

    @abstractmethod
    def get_all(
        self,
        device_name: str | None = None,
        fault_category: str | None = None,
        status: WorkOrderStatus | None = None,
    ) -> list[WorkOrder]:
        """按可选过滤条件查询工单列表。"""
        pass

    @abstractmethod
    def update(self, work_order: WorkOrder) -> None:
        """更新整条工单记录。"""
        pass

    @abstractmethod
    def update_status(
        self,
        work_order_id: str,
        status: WorkOrderStatus,
        processing_error: str = "",
    ) -> None:
        """仅更新异步处理状态与错误信息。"""
        pass

    @abstractmethod
    def delete(self, work_order_id: str) -> None:
        """删除工单主记录。"""
        pass

    @abstractmethod
    def get_device_stats(self, device_name: str) -> dict:
        """返回设备维度的工单聚合统计。"""
        pass
