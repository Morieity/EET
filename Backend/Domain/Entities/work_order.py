import uuid
from datetime import datetime

from Backend.Domain.Common.Enums.WorkOrderStatus import WorkOrderStatus


class WorkOrder:
    """故障工单领域实体。

    该对象同时承担三类职责：
    1. 持有工单的核心业务字段。
    2. 记录工单异步处理状态和错误信息。
    3. 提供统一的序列化与向量化文本拼装能力。
    """

    def __init__(
        self,
        order_no: str,
        device_name: str,
        device_code: str = "",
        fault_phenomenon: str = "",
        fault_cause: str = "",
        fault_category: str = "",
        severity: str = "",
        solution: str = "",
        occurrence_time: datetime | None = None,
        resolution_time: datetime | None = None,
        operator: str = "",
        status: WorkOrderStatus = WorkOrderStatus.PENDING,
        source_file: str = "",
        raw_text: str = "",
        processing_error: str = "",
        work_order_id: str | None = None,
        created_at: datetime | None = None,
        fault_tree_id: str | None = None,
    ):
        self.id = work_order_id or str(uuid.uuid4())
        self.order_no = order_no
        self.device_name = device_name
        self.device_code = device_code
        self.fault_phenomenon = fault_phenomenon
        self.fault_cause = fault_cause
        self.fault_category = fault_category
        self.severity = severity
        self.solution = solution
        self.occurrence_time = occurrence_time
        self.resolution_time = resolution_time
        self.operator = operator
        self.status = status
        self.source_file = source_file
        self.raw_text = raw_text
        self.processing_error = processing_error
        self.fault_tree_id = fault_tree_id
        self.created_at = created_at or datetime.now()

    def link_fault_tree(self, fault_tree_id: str) -> None:
        """绑定最终故障树。"""
        self.fault_tree_id = fault_tree_id

    def unlink_fault_tree(self) -> None:
        """解除故障树绑定。"""
        self.fault_tree_id = None

    def mark_pending(self, processing_error: str = "") -> None:
        """将工单标记为待处理，并记录最近一次处理错误。"""
        self.status = WorkOrderStatus.PENDING
        self.processing_error = processing_error

    def mark_parsed(self) -> None:
        """标记为已完成基础解析/向量化。"""
        self.status = WorkOrderStatus.PARSED
        self.processing_error = ""

    def mark_linked(self) -> None:
        """标记为已完成图谱关联。"""
        self.status = WorkOrderStatus.LINKED
        self.processing_error = ""

    def to_embedding_text(self) -> str:
        """将工单字段拼成统一文本，供向量化和三元组抽取复用。"""
        lines = [
            f"工单编号: {self.order_no}",
            f"设备名称: {self.device_name}",
        ]
        if self.device_code:
            lines.append(f"设备编码: {self.device_code}")
        if self.fault_phenomenon:
            lines.append(f"故障现象: {self.fault_phenomenon}")
        if self.fault_cause:
            lines.append(f"故障原因: {self.fault_cause}")
        if self.fault_category:
            lines.append(f"故障分类: {self.fault_category}")
        if self.severity:
            lines.append(f"严重等级: {self.severity}")
        if self.solution:
            lines.append(f"处置措施: {self.solution}")
        if self.operator:
            lines.append(f"处理人: {self.operator}")
        if self.occurrence_time:
            lines.append(f"发生时间: {self.occurrence_time.isoformat()}")
        if self.resolution_time:
            lines.append(f"解决时间: {self.resolution_time.isoformat()}")
        if self.raw_text:
            lines.append(f"原始文本: {self.raw_text}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """转换为 API 返回与持久化更新都可复用的字典结构。"""
        return {
            "id": self.id,
            "order_no": self.order_no,
            "device_name": self.device_name,
            "device_code": self.device_code,
            "fault_phenomenon": self.fault_phenomenon,
            "fault_cause": self.fault_cause,
            "fault_category": self.fault_category,
            "severity": self.severity,
            "solution": self.solution,
            "occurrence_time": self.occurrence_time.isoformat() if self.occurrence_time else None,
            "resolution_time": self.resolution_time.isoformat() if self.resolution_time else None,
            "operator": self.operator,
            "status": self.status.value,
            "source_file": self.source_file,
            "raw_text": self.raw_text,
            "processing_error": self.processing_error,
            "fault_tree_id": self.fault_tree_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkOrder":
        """从字典恢复实体，并负责时间字段与状态字段的类型还原。"""
        occurrence_time = data.get("occurrence_time")
        resolution_time = data.get("resolution_time")
        created_at = data.get("created_at")
        return cls(
            work_order_id=data.get("id") or data.get("work_order_id"),
            order_no=(data.get("order_no") or "").strip(),
            device_name=(data.get("device_name") or "").strip(),
            device_code=(data.get("device_code") or "").strip(),
            fault_phenomenon=(data.get("fault_phenomenon") or "").strip(),
            fault_cause=(data.get("fault_cause") or "").strip(),
            fault_category=(data.get("fault_category") or "").strip(),
            severity=(data.get("severity") or "").strip(),
            solution=(data.get("solution") or "").strip(),
            occurrence_time=datetime.fromisoformat(occurrence_time) if occurrence_time else None,
            resolution_time=datetime.fromisoformat(resolution_time) if resolution_time else None,
            operator=(data.get("operator") or "").strip(),
            status=WorkOrderStatus(data.get("status", WorkOrderStatus.PENDING.value)),
            source_file=(data.get("source_file") or "").strip(),
            raw_text=(data.get("raw_text") or "").strip(),
            processing_error=(data.get("processing_error") or "").strip(),
            created_at=datetime.fromisoformat(created_at) if created_at else None,
            fault_tree_id=data.get("fault_tree_id"),
        )
