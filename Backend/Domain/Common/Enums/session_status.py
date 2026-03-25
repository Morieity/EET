from enum import Enum


class SessionStatus(str, Enum):
    """诊断会话状态枚举。"""
    IN_PROGRESS = "in_progress"
    TREE_GENERATED = "tree_generated"
    COMPLETED = "completed"

    # 合法状态转换表
    _TRANSITIONS: dict = {}  # type: ignore[assignment]

    @classmethod
    def _build_transitions(cls) -> dict["SessionStatus", set["SessionStatus"]]:
        return {
            cls.IN_PROGRESS: {cls.TREE_GENERATED},
            cls.TREE_GENERATED: {cls.COMPLETED, cls.IN_PROGRESS},
            cls.COMPLETED: set(),
        }

    def can_transition_to(self, target: "SessionStatus") -> bool:
        transitions = self.__class__._build_transitions()
        return target in transitions.get(self, set())
