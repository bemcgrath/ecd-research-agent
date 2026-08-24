"""Structured case report extraction and aggregation."""

from ecd_research.cases.aggregation import (
    CaseAggregationResult,
    aggregate_case_records,
)
from ecd_research.cases.corpus import CaseCorpusRunResult, run_case_corpus
from ecd_research.cases.critic import critique_case_corpus
from ecd_research.cases.dedupe import is_review_or_large_series, likely_same_patient
from ecd_research.cases.extractor import EXTRACTOR_PROMPT_VERSION, extract_case_records
from ecd_research.cases.report import render_case_corpus_markdown
from ecd_research.cases.selection import select_case_report_articles
from ecd_research.cases.validator import validate_case_record

__all__ = [
    "EXTRACTOR_PROMPT_VERSION",
    "CaseAggregationResult",
    "CaseCorpusRunResult",
    "aggregate_case_records",
    "critique_case_corpus",
    "extract_case_records",
    "is_review_or_large_series",
    "likely_same_patient",
    "render_case_corpus_markdown",
    "run_case_corpus",
    "select_case_report_articles",
    "validate_case_record",
]
