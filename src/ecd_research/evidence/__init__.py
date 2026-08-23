"""Evidence extraction and provenance validation."""

from ecd_research.evidence.extractor import EXTRACTOR_PROMPT_VERSION, extract_evidence
from ecd_research.evidence.validator import (
    build_source_corpus,
    normalize_text,
    validate_evidence_record,
)

__all__ = [
    "EXTRACTOR_PROMPT_VERSION",
    "build_source_corpus",
    "extract_evidence",
    "normalize_text",
    "validate_evidence_record",
]
