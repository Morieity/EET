from enum import Enum


class GateType(str, Enum):
    """故障树逻辑门类型枚举。"""
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    INHIBIT = "INHIBIT"
    PRIORITY_AND = "PRIORITY_AND"
