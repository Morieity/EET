import logging
from typing import Any

from Backend.Application.Interfaces.ILogger import ILogger


class PythonLoggerAdapter(ILogger):
    """Adapter that forwards ILogger calls to python logging."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        self._logger.debug(self._format(message, context))

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        self._logger.info(self._format(message, context))

    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        self._logger.warning(self._format(message, context))

    def error(self, message: str, context: dict[str, Any] | None = None) -> None:
        self._logger.error(self._format(message, context))

    @staticmethod
    def _format(message: str, context: dict[str, Any] | None) -> str:
        if not context:
            return message
        context_items = ", ".join(f"{k}={v}" for k, v in sorted(context.items()))
        return f"{message} | {context_items}"


class NullLogger(ILogger):
    """No-op logger used when DI disables context logging."""

    def debug(self, message: str, context: dict[str, Any] | None = None) -> None:
        return None

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        return None

    def warning(self, message: str, context: dict[str, Any] | None = None) -> None:
        return None

    def error(self, message: str, context: dict[str, Any] | None = None) -> None:
        return None
