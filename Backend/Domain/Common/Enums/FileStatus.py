from enum import Enum


class FileStatus(Enum):
    PENDING = "pending"
    EMBEDDED = "embedded"
    FAILED = "failed"
