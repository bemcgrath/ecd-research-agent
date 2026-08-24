"""Provenance validation for CaseRecords against source articles / full text."""

from __future__ import annotations

import re

from ecd_research.evidence.validator import build_source_corpus, normalize_text
from ecd_research.models import (
    CaseRecord,
    CaseValidationResult,
    FullTextDocument,
    PubMedArticle,
)
from ecd_research.tools.pmc import build_fulltext_corpus

_ELLIPSIS_RE = re.compile(r"\.{3}|…")


def _urls_equivalent(left: str, right: str) -> bool:
    return normalize_text(left.rstrip("/")) == normalize_text(right.rstrip("/"))


def build_case_source_corpus(
    source_article: PubMedArticle,
    full_text: FullTextDocument | None = None,
) -> str:
    """Build grounding corpus: title+abstract, plus full text when available."""
    abstract_corpus = build_source_corpus(source_article)
    if full_text is None or not full_text.raw_text.strip():
        return abstract_corpus
    full_corpus = build_fulltext_corpus(full_text)
    # Keep PubMed abstract available so abstract-faithful quotes still validate.
    parts = [p for p in (abstract_corpus, full_corpus) if p and p.strip()]
    return "\n\n".join(parts)


def _supporting_text_grounded(supporting_text: str, corpus: str) -> bool:
    """Require an exact normalized span, or exact fragments if the model used ellipsis."""
    if not supporting_text.strip() or not corpus.strip():
        return False
    norm_corpus = normalize_text(corpus)
    norm_support = normalize_text(supporting_text)
    if norm_support in norm_corpus:
        return True

    # Allow "sentence ... sentence" only when each substantial fragment is exact.
    fragments = [
        normalize_text(part)
        for part in _ELLIPSIS_RE.split(supporting_text)
        if len(normalize_text(part)) >= 40
    ]
    if len(fragments) >= 2 and all(frag in norm_corpus for frag in fragments):
        return True
    return False


def validate_case_record(
    record: CaseRecord,
    source_article: PubMedArticle,
    *,
    full_text: FullTextDocument | None = None,
) -> CaseValidationResult:
    """Validate that a case record is grounded in the supplied source material."""
    errors: list[str] = []

    if record.pmid != source_article.pmid:
        errors.append(
            f"PMID mismatch: record={record.pmid!r} source={source_article.pmid!r}"
        )

    if full_text is not None and full_text.pmid != source_article.pmid:
        errors.append(
            f"full-text PMID mismatch: full_text={full_text.pmid!r} "
            f"article={source_article.pmid!r}"
        )

    source_title = source_article.title
    if record.source_title is not None and source_title is not None:
        if normalize_text(record.source_title) != normalize_text(source_title):
            errors.append("source_title does not match article title")
    elif record.source_title is not None and source_title is None:
        errors.append("source_title present but article title is missing")

    if record.doi is not None:
        if source_article.doi is None and (full_text is None or full_text.doi is None):
            errors.append("DOI present on record but missing on source article")
        else:
            expected_doi = source_article.doi or (full_text.doi if full_text else None)
            if expected_doi and normalize_text(record.doi) != normalize_text(expected_doi):
                errors.append("DOI mismatch between record and source article")

    expected_url = str(source_article.pubmed_url)
    if not _urls_equivalent(record.source_url, expected_url):
        errors.append(
            f"source_url mismatch: record={record.source_url!r} expected={expected_url!r}"
        )

    if not record.supporting_text or not record.supporting_text.strip():
        errors.append("supporting_text is empty")
    else:
        corpus = build_case_source_corpus(source_article, full_text)
        if not corpus.strip():
            errors.append("source material has no text to ground extraction")
        elif not _supporting_text_grounded(record.supporting_text, corpus):
            errors.append("supporting_text not found in supplied source material")

    if record.case_count is not None and record.case_count < 1:
        errors.append("case_count must be >= 1 when provided")

    if errors:
        rejected = record.model_copy(update={"validation_status": "rejected"})
        return CaseValidationResult(ok=False, errors=errors, record=rejected)

    validated = record.model_copy(update={"validation_status": "validated"})
    return CaseValidationResult(ok=True, errors=[], record=validated)
