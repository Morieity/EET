"""文件夹领域实体，用于对上传文件进行分类管理。"""
import uuid
from datetime import datetime


class Folder:
    def __init__(
        self,
        name: str,
        folder_id: str | None = None,
        created_at: datetime | None = None,
    ):
        self.id = folder_id or str(uuid.uuid4())
        self.name = name
        self.created_at = created_at or datetime.now()

    def rename(self, new_name: str):
        self.name = new_name

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }
