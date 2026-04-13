import uuid
from datetime import datetime
from Backend.Domain.Common.Enums.FileType import FileType
from Backend.Domain.Common.Enums.FileStatus import FileStatus


class File:
    def __init__(
        self,
        file_name: str,
        file_type: FileType,
        file_id: str | None = None,
        created_at: datetime | None = None,
        status: FileStatus = FileStatus.PENDING,
        folder_id: str | None = None,
    ):
        self.id = file_id or str(uuid.uuid4())
        self.file_name = file_name
        self.file_type = file_type
        self.created_at = created_at or datetime.now()
        self.status = status
        self.folder_id = folder_id

    def mark_embedded(self):
        self.status = FileStatus.EMBEDDED

    def mark_failed(self):
        self.status = FileStatus.FAILED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file_name": self.file_name,
            "file_type": self.file_type.value,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "folder_id": self.folder_id,
        }
