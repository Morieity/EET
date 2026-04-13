"""文件夹仓储的 SQLite 实现，负责文件夹的增删改查持久化。"""
from datetime import datetime
from Backend.Application.Interfaces.IFolderRepository import IFolderRepository
from Backend.Domain.Entities.folder import Folder
from Backend.Infrastructure.persistence.database import get_connection


class SQLiteFolderRepository(IFolderRepository):
    def save(self, folder: Folder) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO folders (id, name, created_at) VALUES (?, ?, ?)",
                (folder.id, folder.name, folder.created_at.isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_by_id(self, folder_id: str) -> Folder | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM folders WHERE id = ?", (folder_id,)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        finally:
            conn.close()

    def get_by_name(self, name: str) -> Folder | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM folders WHERE name = ?", (name,)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        finally:
            conn.close()

    def get_all(self) -> list[Folder]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM folders ORDER BY created_at DESC").fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    def update_name(self, folder_id: str, new_name: str) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE folders SET name = ? WHERE id = ?", (new_name, folder_id))
            conn.commit()
        finally:
            conn.close()

    def delete(self, folder_id: str) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE files SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
            conn.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_entity(row) -> Folder:
        return Folder(
            folder_id=row["id"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
