"""Evidence critic: adversarial checks before synthesis."""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field

from ecd_research.evidence.validator import (
    build_source_corpus,
    normalize_text,
    validate_evidence_record,
)
from ecd_research.models import EvidenceRecord, EvidenceStrength, PubMedArticle, StudyType

BROAD_EFFICACY_RE = re.compile(
    r"\b(all patients|universally|always effective|standard of care for all|"
    r"cures?|guarantees?|definitive treatment for)\b",
    re.IGNORECASE,
)
TREATMENT_INSTRUCTION_RE = re.compile(
    r"\b(should (start|stop|increase|decrease|take)|must (take|stop)|"
    r"prescribe|recommended dose)\b",
    re.IGNORECASE,
)
MUTATION_CLAIM_RE = re.compile(
    r"\b(braf|map2k1|kras|nras|araf|pik3ca|v600e)\b",
    re.IGNORECASE,
)


class CritiqueLabel(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class CritiqueFinding(BaseModel):
    code: str
    detail: str


class CritiqueResult(BaseModel):
    """Critic outcome for one EvidenceRecord."""

    label: CritiqueLabel
    findings: list[CritiqueFinding] = Field(default_factory=list)
    record: EvidenceRecord
    source_pmid: str


def _article_by_pmid(
    articles: list[PubMedArticle],
) -> dict[str, PubMedArticle]:
    return {a.pmid: a for a in articles}


def critique_evidence_record(
    record: EvidenceRecord,
    source_article: PubMedArticle | None = None,
    *,
    corpus_records: list[EvidenceRecord] | None = None,
) -> CritiqueResult:
    """Apply deterministic critic checks; fail closed on provenance gaps."""
    findings: list[CritiqueFinding] = []

    if record.validation_status != "validated":
        findings.append(
            CritiqueFinding(
                code="not_validated",
                detail="Record is not provenance-validated; cannot be treated as supported.",
            )
        )

    if source_article is not None:
        provenance = validate_evidence_record(record, source_article)
        if not provenance.ok:
            findings.append(
                CritiqueFinding(
                    code="provenance_failed",
                    detail="; ".join(provenance.errors),
                )
            )
    else:
        findings.append(
            CritiqueFinding(
                code="missing_source_article",
                detail="No source article supplied for critic provenance re-check.",
            )
        )

    if TREATMENT_INSTRUCTION_RE.search(record.claim):
        findings.append(
            CritiqueFinding(
                code="clinical_instruction_language",
                detail="Claim uses treatment-instruction language; research tool must not prescribe.",
            )
        )

    if record.study_type == StudyType.CASE_REPORT and BROAD_EFFICACY_RE.search(
        record.claim
    ):
        findings.append(
            CritiqueFinding(
                code="case_report_overgeneralized",
                detail="Case report claim uses broad efficacy language.",
            )
        )

    if record.study_type == StudyType.CASE_REPORT and record.evidence_strength in {
        EvidenceStrength.HIGH,
        EvidenceStrength.MODERATE,
    }:
        findings.append(
            CritiqueFinding(
                code="strength_overstated",
                detail="Case report marked moderate/high strength; likely overstated.",
            )
        )

    if record.abstract_limited:
        findings.append(
            CritiqueFinding(
                code="abstract_limited",
                detail="Evidence is abstract-limited; full-text may change interpretation.",
            )
        )

    if record.sample_size is None and record.study_type in {
        StudyType.CASE_SERIES,
        StudyType.RETROSPECTIVE_COHORT,
        StudyType.PROSPECTIVE_SINGLE_ARM_TRIAL,
        StudyType.PROSPECTIVE_CONTROLLED_TRIAL,
    }:
        findings.append(
            CritiqueFinding(
                code="sample_size_unknown",
                detail="Study type usually implies a sample size, but none was extracted.",
            )
        )

    if source_article is not None and MUTATION_CLAIM_RE.search(record.claim):
        corpus = normalize_text(build_source_corpus(source_article))
        mentioned = [
            m.group(0).lower()
            for m in MUTATION_CLAIM_RE.finditer(record.claim)
        ]
        for token in mentioned:
            if token not in corpus:
                findings.append(
                    CritiqueFinding(
                        code="mutation_not_in_source",
                        detail=f"Claim mentions {token!r} but source title/abstract do not.",
                    )
                )

    # Simple contradiction scan: opposite polarity keywords across records.
    if corpus_records:
        claim_l = normalize_text(record.claim)
        positive = any(w in claim_l for w in ("effective", "response", "improved", "benefit"))
        negative = any(
            w in claim_l for w in ("ineffective", "no response", "failed", "worsened", "toxicity")
        )
        if positive or negative:
            for other in corpus_records:
                if other.pmid == record.pmid and other.claim == record.claim:
                    continue
                if other.intervention and record.intervention:
                    if normalize_text(other.intervention) != normalize_text(
                        record.intervention
                    ):
                        continue
                other_l = normalize_text(other.claim)
                other_pos = any(
                    w in other_l for w in ("effective", "response", "improved", "benefit")
                )
                other_neg = any(
                    w in other_l
                    for w in ("ineffective", "no response", "failed", "worsened", "toxicity")
                )
                if (positive and other_neg) or (negative and other_pos):
                    findings.append(
                        CritiqueFinding(
                            code="possible_contradiction",
                            detail=(
                                f"Possible conflict with PMID {other.pmid}: {other.claim[:160]}"
                            ),
                        )
                    )
                    break

    hard_fail_codes = {
        "not_validated",
        "provenance_failed",
        "missing_source_article",
        "mutation_not_in_source",
        "clinical_instruction_language",
    }
    codes = {f.code for f in findings}

    if codes & hard_fail_codes:
        label = CritiqueLabel.UNSUPPORTED
    elif "possible_contradiction" in codes:
        label = CritiqueLabel.CONTRADICTED
    elif codes & {
        "case_report_overgeneralized",
        "strength_overstated",
        "sample_size_unknown",
        "abstract_limited",
    }:
        # abstract_limited alone → PARTIALLY_SUPPORTED (still usable with caveat)
        label = CritiqueLabel.PARTIALLY_SUPPORTED
    elif not findings:
        label = CritiqueLabel.SUPPORTED
    else:
        label = CritiqueLabel.PARTIALLY_SUPPORTED

    # abstract_limited-only should be PARTIALLY_SUPPORTED, not fail
    if codes == {"abstract_limited"}:
        label = CritiqueLabel.PARTIALLY_SUPPORTED

    return CritiqueResult(
        label=label,
        findings=findings,
        record=record,
        source_pmid=record.pmid,
    )


def critique_evidence_set(
    records: list[EvidenceRecord],
    articles: list[PubMedArticle],
) -> list[CritiqueResult]:
    """Critique each record against its source article and the broader set."""
    by_pmid = _article_by_pmid(articles)
    results: list[CritiqueResult] = []
    for record in records:
        results.append(
            critique_evidence_record(
                record,
                by_pmid.get(record.pmid),
                corpus_records=records,
            )
        )
    return results
