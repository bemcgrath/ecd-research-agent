"""Provenance validation for CaseRecords against source articles."""

from __future__ import annotations

from ecd_research.evidence.validator import build_source_corpus, normalize_text
from ecd_research.models import CaseRecord, CaseValidationResult, PubMedArticle


def _urls_equivalent(left: str, right: str) -> bool:
    return normalize_text(left.rstrip("/")) == normalize_text(right.rstrip("/"))


def validate_case_record(
    record: CaseRecord,
    source_article: PubMedArticle,
) -> CaseValidationResult:
    """Validate that a case record is grounded in the supplied article."""
    errors: list[str] = []

    if record.pmid != source_article.pmid:
        errors.append(
            f"PMID mismatch: record={record.pmid!r} source={source_article.pmid!r}"
        )

    source_title = source_article.title
    if record.source_title is not None and source_title is not None:
        if normalize_text(record.source_title) != normalize_text(source_title):
            errors.append("source_title does not match article title")
    elif record.source_title is not None and source_title is None:
        errors.append("source_title present but article title is missing")

    if record.doi is not None:
        if source_article.doi is None:
            errors.append("DOI present on record but missing on source article")
        elif normalize_text(record.doi) != normalize_text(source_article.doi):
            errors.append("DOI mismatch between record and source article")

    expected_url = str(source_article.pubmed_url)
    if not _urls_equivalent(record.source_url, expected_url):
        errors.append(
            f"source_url mismatch: record={record.source_url!r} expected={expected_url!r}"
        )

    if not record.supporting_text or not record.supporting_text.strip():
        errors.append("supporting_text is empty")
    else:
        corpus = build_source_corpus(source_article)
        if not corpus.strip():
            errors.append("source article has no title or abstract to ground extraction")
        elif normalize_text(record.supporting_text) not in normalize_text(corpus):
            errors.append("supporting_text not found in supplied source material")

    if record.case_count is not None and record.case_count < 1:
        errors.append("case_count must be >= 1 when provided")

    if errors:
        rejected = record.model_copy(update={"validation_status": "rejected"})
        return CaseValidationResult(ok=False, errors=errors, record=rejected)

    validated = record.model_copy(update={"validation_status": "validated"})
    return CaseValidationResult(ok=True, errors=[], record=validated)
