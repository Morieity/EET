from enum import Enum


class WorkOrderStatus(Enum):
    """工单处理状态。

    PENDING: 已入库，但还未完成向量化/图谱处理。
    PARSED: 已完成向量化或基础解析。
    LINKED: 已完成图谱写入，可以参与后续自动构建流程。
    """

    PENDING = "PENDING"
    PARSED = "PARSED"
    LINKED = "LINKED"
