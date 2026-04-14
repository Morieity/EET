from enum import Enum


class EntityType(Enum):
    COMPONENT = "COMPONENT"
    SYMPTOM = "SYMPTOM"
    ERROR_CODE = "ERROR_CODE"
    SOLUTION = "SOLUTION"


class RelationType(Enum):
    CAUSES = "CAUSES"
    BELONGS_TO = "BELONGS_TO"
    RESOLVES = "RESOLVES"
    DIAGNOSES = "DIAGNOSES"
