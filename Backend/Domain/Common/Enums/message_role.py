from enum import Enum


class MessageRole(str, Enum):
    """对话消息角色枚举。"""
    USER = "user"
    ASSISTANT = "assistant"
