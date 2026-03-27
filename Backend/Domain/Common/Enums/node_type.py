from enum import Enum


class NodeType(str, Enum):
    """故障树节点类型枚举（IEC 61025）。"""
    BASIC_EVENT = "basic_event"
    INTERMEDIATE_EVENT = "intermediate_event"
    UNDEVELOPED_EVENT = "undeveloped_event"
    EXTERNAL_EVENT = "external_event"
    CONDITIONAL_EVENT = "conditional_event"
