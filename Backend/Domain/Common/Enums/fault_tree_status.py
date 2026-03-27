from enum import Enum


class FaultTreeStatus(str, Enum):
    """故障树状态枚举。"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    STANDARDIZED = "standardized"
    FAILED_STANDARDIZATION = "failed_standardization"

    @classmethod
    def _build_transitions(cls) -> dict["FaultTreeStatus", set["FaultTreeStatus"]]:
        return {
            cls.DRAFT: {cls.CONFIRMED},
            cls.CONFIRMED: {cls.STANDARDIZED, cls.FAILED_STANDARDIZATION, cls.DRAFT},
            cls.STANDARDIZED: set(),
            cls.FAILED_STANDARDIZATION: {cls.CONFIRMED},
        }

    def can_transition_to(self, target: "FaultTreeStatus") -> bool:
        transitions = self.__class__._build_transitions()
        return target in transitions.get(self, set())
