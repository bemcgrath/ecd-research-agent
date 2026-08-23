"""Local persistence for ECD research findings."""

from ecd_research.storage.database import connect, default_db_path, init_schema
from ecd_research.storage.repository import EvidenceRepository

__all__ = [
    "EvidenceRepository",
    "connect",
    "default_db_path",
    "init_schema",
]
