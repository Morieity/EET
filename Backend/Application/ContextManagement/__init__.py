from Backend.Application.ContextManagement.AlgorithmRegistry import ContextAlgorithmRegistry
from Backend.Application.ContextManagement.ContextManagerTypes import (
    ContextManagerConfig,
    ContextPreparationResult,
)

__all__ = [
    "ContextAlgorithmRegistry",
    "ContextManagerConfig",
    "ContextPreparationResult",
    "DefaultContextManager",
]


def __getattr__(name: str):
    if name == "DefaultContextManager":
        from Backend.Application.ContextManagement.ContextManager import DefaultContextManager

        return DefaultContextManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
