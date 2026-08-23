"""Tests for evidence provenance validation and extraction."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ecd_research.evidence.extractor import (
    EXTRACTOR_PROMPT_VERSION,
    _ExtractionPayload,
    _ExtractedClaim,
    extract_evidence,
)
from ecd_research.evidence.validator import (
    build_source_corpus,
    normalize_text,
    validate_evidence_record,
)
from ecd_research.models import (
    EvidenceRecord,
    EvidenceStrength,
    PubMedArticle,
    StudyType,
)


def _article(**overrides: object) -> PubMedArticle:
    base = {
        "pmid": "99999999",
        "title": "Complete Erdheim-Chester disease example article",
        "authors": ["Smith J"],
        "journal": "Example Journal of Rare Diseases",
        "publication_date": "2026 Aug 15",
        "abstract": (
            "BACKGROUND: Background text about one patient with ECD.\n\n"
            "METHODS: Methods text."
        ),
        "doi": "10.1000/example.doi",
        "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/99999999/",
    }
    base.update(overrides)
    return PubMedArticle(**base)  # type: ignore[arg-type]


def _record(**overrides: object) -> EvidenceRecord:
    article = _article()
    base = {
        "claim": "A single patient with ECD is described.",
        "pmid": article.pmid,
        "source_title": article.title,
        "source_url": str(article.pubmed_url),
        "publication_date": article.publication_date,
        "journal": article.journal,
        "doi": article.doi,
        "study_type": StudyType.CASE_REPORT,
        "sample_size": 1,
        "population": "one patient with ECD",
        "intervention": None,
        "comparator": None,
        "outcome": None,
        "supporting_text": "Background text about one patient with ECD.",
        "source_fields_used": ["abstract"],
        "limitations": ["Single-patient case report"],
        "evidence_strength": EvidenceStrength.VERY_LOW,
        "reasoning_note": "Case report; abstract-limited.",
        "abstract_limited": True,
        "extractor_model": "test-model",
        "extractor_prompt_version": EXTRACTOR_PROMPT_VERSION,
        "validation_status": "pending",
    }
    base.update(overrides)
    return EvidenceRecord(**base)  # type: ignore[arg-type]


def test_normalize_and_corpus() -> None:
    assert normalize_text("  Foo\u00a0BAR  ") == "foo bar"
    article = _article()
    corpus = build_source_corpus(article)
    assert "Complete Erdheim-Chester disease example article" in corpus
    assert "BACKGROUND: Background text" in corpus


def test_validate_evidence_record_accepts_grounded_claim() -> None:
    result = validate_evidence_record(_record(), _article())
    assert result.ok
    assert result.record is not None
    assert result.record.validation_status == "validated"


def test_reject_fabricated_pmid() -> None:
    result = validate_evidence_record(_record(pmid="11111111"), _article())
    assert not result.ok
    assert any("PMID mismatch" in e for e in result.errors)
    assert result.record is not None
    assert result.record.validation_status == "rejected"


def test_reject_modified_doi_and_title() -> None:
    bad_doi = validate_evidence_record(_record(doi="10.9999/fake"), _article())
    assert not bad_doi.ok
    assert any("DOI mismatch" in e for e in bad_doi.errors)

    bad_title = validate_evidence_record(
        _record(source_title="Totally different title"),
        _article(),
    )
    assert not bad_title.ok
    assert any("source_title" in e for e in bad_title.errors)


def test_reject_wrong_source_url() -> None:
    result = validate_evidence_record(
        _record(source_url="https://pubmed.ncbi.nlm.nih.gov/00000000/"),
        _article(),
    )
    assert not result.ok
    assert any("source_url" in e for e in result.errors)


def test_reject_supporting_text_not_in_source() -> None:
    result = validate_evidence_record(
        _record(supporting_text="Patient carried a BRAF V600E mutation."),
        _article(),
    )
    assert not result.ok
    assert any("supporting_text not found" in e for e in result.errors)


def test_whitespace_normalized_supporting_text_still_matches() -> None:
    result = validate_evidence_record(
        _record(supporting_text="Background   text   about   one   patient   with   ECD."),
        _article(),
    )
    assert result.ok


def test_adversarial_case_report_must_not_claim_universal_efficacy_without_text() -> None:
    """If supporting text is not in the abstract, universal-efficacy claims fail."""
    article = _article(
        abstract="We report one patient with ECD treated with cobimetinib."
    )
    record = _record(
        claim="Cobimetinib is universally effective for all ECD patients.",
        supporting_text="Cobimetinib is universally effective for all ECD patients.",
        study_type=StudyType.CASE_REPORT,
        sample_size=1,
        source_title=article.title,
        pmid=article.pmid,
        doi=article.doi,
        source_url=str(article.pubmed_url),
    )
    result = validate_evidence_record(record, article)
    assert not result.ok


def test_adversarial_title_mentions_braf_does_not_prove_mutation_in_patient() -> None:
    article = _article(
        title="BRAF pathway review in histiocytosis",
        abstract="This review discusses BRAF inhibitors as a class of drugs.",
        doi=None,
    )
    record = _record(
        claim="The patient carried a BRAF V600E mutation.",
        supporting_text="The patient carried a BRAF V600E mutation.",
        source_title=article.title,
        pmid=article.pmid,
        doi=None,
        source_url=str(article.pubmed_url),
        study_type=StudyType.SYSTEMATIC_REVIEW,
    )
    result = validate_evidence_record(record, article)
    assert not result.ok


def test_extract_evidence_filters_invalid_records(monkeypatch: pytest.MonkeyPatch) -> None:
    article = _article()
    payload = _ExtractionPayload(
        records=[
            _ExtractedClaim(
                claim="A single patient with ECD is described.",
                study_type=StudyType.CASE_REPORT,
                sample_size=1,
                supporting_text="Background text about one patient with ECD.",
                source_fields_used=["abstract"],
                limitations=["n=1"],
                evidence_strength=EvidenceStrength.VERY_LOW,
                reasoning_note="case report",
            ),
            _ExtractedClaim(
                claim="Invented mutation claim.",
                study_type=StudyType.CASE_REPORT,
                supporting_text="Patient had a fabricated KRAS mutation.",
                source_fields_used=["abstract"],
                limitations=[],
                evidence_strength=EvidenceStrength.LOW,
                reasoning_note="should be rejected",
            ),
        ]
    )

    mock_client = MagicMock()
    monkeypatch.setattr(
        "ecd_research.evidence.extractor._call_openai",
        lambda **kwargs: payload,
    )

    records = extract_evidence(
        article,
        "What does this article report about ECD?",
        client=mock_client,
    )
    assert len(records) == 1
    assert records[0].validation_status == "validated"
    assert "single patient" in records[0].claim.lower()


def test_extract_evidence_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="research_question"):
        extract_evidence(_article(), "   ")
