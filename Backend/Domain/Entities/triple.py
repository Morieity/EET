from dataclasses import dataclass, field


@dataclass
class Triple:
    head: str
    head_type: str
    relation: str
    tail: str
    tail_type: str
    source_file: str = ""
    source_chunk_id: str = ""

    def to_dict(self) -> dict:
        return {
            "head": self.head,
            "head_type": self.head_type,
            "relation": self.relation,
            "tail": self.tail,
            "tail_type": self.tail_type,
            "source_file": self.source_file,
            "source_chunk_id": self.source_chunk_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Triple":
        return cls(
            head=data.get("head", ""),
            head_type=data.get("head_type", ""),
            relation=data.get("relation", ""),
            tail=data.get("tail", ""),
            tail_type=data.get("tail_type", ""),
            source_file=data.get("source_file", ""),
            source_chunk_id=data.get("source_chunk_id", ""),
        )
