from enum import Enum


class FileType(Enum):
    PDF = "pdf"
    WORD = "word"
    TXT = "txt"
    MARKDOWN = "markdown"

    @staticmethod
    def from_extension(ext: str) -> "FileType":
        mapping = {
            ".pdf": FileType.PDF,
            ".doc": FileType.WORD,
            ".docx": FileType.WORD,
            ".txt": FileType.TXT,
            ".md": FileType.MARKDOWN,
        }
        file_type = mapping.get(ext.lower())
        if file_type is None:
            raise ValueError(f"Unsupported file extension: {ext}")
        return file_type
