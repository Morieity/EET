from abc import ABC, abstractmethod
from typing import Any


class ILogger(ABC):
    """Application-layer logging contract for dependency injection."""

    @abstractmethod
    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        pass

    @abstractmethod
    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        pass

    @abstractmethod
    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        pass

    @abstractmethod
    def error(self, message: str, context: dict[str, Any] | None = None) -> None:
        pass
