from enum import Enum


class NodeType(Enum):
    EVENT = "event"
    GATE = "gate"


class GateType(Enum):
    AND = "AND"
    OR = "OR"
