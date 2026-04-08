from datetime import datetime
from Backend.Application.Interfaces.IFileRepository import IFileRepository
from Backend.Domain.Entities.file import File
from Backend.Domain.Common.Enums.FileType import FileType
from Backend.Domain.Common.Enums.FileStatus import FileStatus
from Backend.Infrastructure.persistence.database import get_connection


class SQLiteFileRepository(IFileRepository):
    def save(self, file: File) -> None:
        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO files (id, file_name, file_type, created_at, status, folder_id) VALUES (?, ?, ?, ?, ?, ?)",
                (file.id, file.file_name, file.file_type.value, file.created_at.isoformat(), file.status.value, file.folder_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete(self, file_id: str) -> None:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
        finally:
            conn.close()

    def get_by_name(self, file_name: str) -> File | None:
        conn = get_connection()
        try:
            row = conn.execute("SELECT * FROM files WHERE file_name = ?", (file_name,)).fetchone()
            if row is None:
                return None
            return self._row_to_entity(row)
        finally:
            conn.close()

    def get_all(self) -> list[File]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM files ORDER BY created_at DESC").fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    def update_status(self, file_id: str, status: FileStatus) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE files SET status = ? WHERE id = ?", (status.value, file_id))
            conn.commit()
        finally:
            conn.close()

    def update_folder(self, file_id: str, folder_id: str | None) -> None:
        conn = get_connection()
        try:
            conn.execute("UPDATE files SET folder_id = ? WHERE id = ?", (folder_id, file_id))
            conn.commit()
        finally:
            conn.close()

    def get_by_folder_id(self, folder_id: str) -> list[File]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM files WHERE folder_id = ? ORDER BY created_at DESC", (folder_id,)).fetchall()
            return [self._row_to_entity(row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def _row_to_entity(row) -> File:
        return File(
            file_id=row["id"],
            file_name=row["file_name"],
            file_type=FileType(row["file_type"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            status=FileStatus(row["status"]),
            folder_id=row["folder_id"],
        )
