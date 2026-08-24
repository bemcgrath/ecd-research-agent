"""Heuristic same-patient duplicate detection across CaseRecords.

Marks likely duplicates; does not invent merged patient records.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ecd_research.models import CaseRecord, TherapyTiming

# Large-n rows belong in the review/series bucket (see GLOSSARY).
LARGE_SERIES_MIN_N = 10

_SCORE_RE = re.compile(
    r"\b(?:sara|icars|edss|mrs|nihss)?\s*(\d+)\s*/\s*(\d+)\b",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:/[a-z0-9]+)?", re.IGNORECASE)

_REVIEW_TITLE_STRONG = (
    "systematic review",
    "meta-analysis",
    "metaanalysis",
    "narrative review",
    "scoping review",
)
_CASE_TITLE_MARKERS = (
    "case report",
    "case series",
    "case presentation",
)


def is_review_or_large_series(record: CaseRecord) -> bool:
    """True for large-n series or review-style papers (not single-case primary)."""
    if record.case_count is not None and record.case_count >= LARGE_SERIES_MIN_N:
        return True

    title = (record.source_title or "").lower()
    if any(marker in title for marker in _REVIEW_TITLE_STRONG):
        return True

    # "Literature review" / plain "review" without case-report framing.
    if "review" in title and not any(m in title for m in _CASE_TITLE_MARKERS):
        if record.case_count is not None and record.case_count >= 5:
            return True
        if "literature review" in title or title.strip().startswith("review"):
            return True

    return False


def _norm_mutation(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _timing_key(record: CaseRecord) -> str | None:
    if record.therapy_timing is None:
        return None
    if record.therapy_timing == TherapyTiming.NOT_REPORTED:
        return None
    return record.therapy_timing.value


def _score_tokens(text: str) -> set[str]:
    return {f"{a}/{b}".lower() for a, b in _SCORE_RE.findall(text or "")}


def _timeline_blob(record: CaseRecord) -> str:
    parts = [
        record.symptoms_to_diagnosis or "",
        record.diagnosis_to_treatment or "",
        record.neurologic_outcome or "",
        record.supporting_text or "",
    ]
    return " ".join(parts).lower()


def _content_tokens(text: str) -> set[str]:
    stop = {
        "the",
        "and",
        "with",
        "after",
        "from",
        "was",
        "were",
        "this",
        "that",
        "patient",
        "treatment",
        "therapy",
        "months",
        "years",
        "year",
        "month",
        "not",
        "reported",
    }
    tokens = {t.lower() for t in _TOKEN_RE.findall(text or "")}
    return {t for t in tokens if len(t) > 2 and t not in stop}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def likely_same_patient(a: CaseRecord, b: CaseRecord) -> bool:
    """Heuristic: same mutation + timing + overlapping scores or near-identical timeline."""
    if a.pmid == b.pmid:
        return False

    mut_a, mut_b = _norm_mutation(a.mutation), _norm_mutation(b.mutation)
    if not mut_a or not mut_b or mut_a != mut_b:
        return False

    timing_a, timing_b = _timing_key(a), _timing_key(b)
    if not timing_a or not timing_b or timing_a != timing_b:
        return False

    scores_a = _score_tokens(_timeline_blob(a))
    scores_b = _score_tokens(_timeline_blob(b))
    if scores_a and scores_b and scores_a & scores_b:
        return True

    tokens_a = _content_tokens(_timeline_blob(a))
    tokens_b = _content_tokens(_timeline_blob(b))
    if _jaccard(tokens_a, tokens_b) >= 0.55:
        return True

    return False


def _prefer_canonical(a: CaseRecord, b: CaseRecord) -> CaseRecord:
    """Prefer fuller / non-abstract-limited / earlier PMID as the kept row."""
    score_a = (
        (0 if a.abstract_limited else 2)
        + (1 if a.neurologic_outcome else 0)
        + (1 if a.supporting_text and len(a.supporting_text) > 80 else 0)
    )
    score_b = (
        (0 if b.abstract_limited else 2)
        + (1 if b.neurologic_outcome else 0)
        + (1 if b.supporting_text and len(b.supporting_text) > 80 else 0)
    )
    if score_a != score_b:
        return a if score_a > score_b else b
    return a if a.pmid <= b.pmid else b


def find_likely_duplicate_pairs(
    records: list[CaseRecord],
) -> list[tuple[str, str]]:
    """Return (canonical_pmid, duplicate_pmid) pairs; one secondary per link."""
    pairs: list[tuple[str, str]] = []
    n = len(records)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = records[i], records[j]
            if not likely_same_patient(a, b):
                continue
            kept = _prefer_canonical(a, b)
            other = b if kept.pmid == a.pmid else a
            pairs.append((kept.pmid, other.pmid))
    return pairs


def duplicate_of_map(records: list[CaseRecord]) -> dict[str, str]:
    """Map duplicate PMID -> canonical PMID (transitive collapse to preferred root)."""
    pairs = find_likely_duplicate_pairs(records)
    parent: dict[str, str] = {}
    for kept, dup in pairs:
        parent[dup] = kept

    def root(pmid: str) -> str:
        seen: set[str] = set()
        while pmid in parent and pmid not in seen:
            seen.add(pmid)
            pmid = parent[pmid]
        return pmid

    # Prefer the better record when chains exist.
    by_pmid = {r.pmid: r for r in records}
    groups: dict[str, list[str]] = defaultdict(list)
    for pmid in {p for pair in pairs for p in pair}:
        groups[root(pmid)].append(pmid)

    result: dict[str, str] = {}
    for members in groups.values():
        member_records = [by_pmid[p] for p in members if p in by_pmid]
        if len(member_records) < 2:
            continue
        canonical = member_records[0]
        for rec in member_records[1:]:
            canonical = _prefer_canonical(canonical, rec)
        for rec in member_records:
            if rec.pmid != canonical.pmid:
                result[rec.pmid] = canonical.pmid
    return result
