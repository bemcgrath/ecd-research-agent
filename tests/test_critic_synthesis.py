"""Tests for evidence critic and report synthesis."""

from __future__ import annotations

from ecd_research.evidence.extractor import EXTRACTOR_PROMPT_VERSION
from ecd_research.models import (
    ClinicalTrial,
    EvidenceRecord,
    EvidenceStrength,
    PubMedArticle,
    StudyType,
)
from ecd_research.research.critic import CritiqueLabel, critique_evidence_record, critique_evidence_set
from ecd_research.research.synthesis import render_report_markdown, synthesize_report


def _article(**overrides: object) -> PubMedArticle:
    base = {
        "pmid": "99999999",
        "title": "Case report of ECD treated with cobimetinib",
        "authors": ["Smith J"],
        "journal": "Example",
        "publication_date": "2026",
        "abstract": "We report one patient with ECD treated with cobimetinib who improved.",
        "doi": "10.1000/example.doi",
        "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/99999999/",
    }
    base.update(overrides)
    return PubMedArticle(**base)  # type: ignore[arg-type]


def _record(**overrides: object) -> EvidenceRecord:
    article = _article()
    base = {
        "claim": "One patient with ECD treated with cobimetinib improved.",
        "pmid": article.pmid,
        "source_title": article.title,
        "source_url": str(article.pubmed_url),
        "publication_date": article.publication_date,
        "journal": article.journal,
        "doi": article.doi,
        "study_type": StudyType.CASE_REPORT,
        "sample_size": 1,
        "population": "one patient with ECD",
        "intervention": "cobimetinib",
        "comparator": None,
        "outcome": "improved",
        "supporting_text": "We report one patient with ECD treated with cobimetinib who improved.",
        "source_fields_used": ["abstract"],
        "limitations": ["n=1"],
        "evidence_strength": EvidenceStrength.VERY_LOW,
        "reasoning_note": "case report",
        "abstract_limited": True,
        "extractor_model": "test",
        "extractor_prompt_version": EXTRACTOR_PROMPT_VERSION,
        "validation_status": "validated",
    }
    base.update(overrides)
    return EvidenceRecord(**base)  # type: ignore[arg-type]


def test_critic_partial_for_abstract_limited_case_report() -> None:
    result = critique_evidence_record(_record(), _article())
    assert result.label == CritiqueLabel.PARTIALLY_SUPPORTED
    assert any(f.code == "abstract_limited" for f in result.findings)


def test_critic_rejects_case_report_universal_efficacy() -> None:
    record = _record(
        claim="Cobimetinib is universally effective for all ECD patients.",
        supporting_text="We report one patient with ECD treated with cobimetinib who improved.",
    )
    # supporting text won't match claim text for provenance if we change supporting —
    # keep supporting as abstract span; claim overgeneralization flagged separately.
    result = critique_evidence_record(record, _article())
    assert any(f.code == "case_report_overgeneralized" for f in result.findings)


def test_critic_unsupported_when_mutation_not_in_source() -> None:
    record = _record(
        claim="The patient carried a BRAF V600E mutation.",
        supporting_text="We report one patient with ECD treated with cobimetinib who improved.",
    )
    result = critique_evidence_record(record, _article())
    assert result.label == CritiqueLabel.UNSUPPORTED
    assert any(f.code == "mutation_not_in_source" for f in result.findings)


def test_critic_detects_possible_contradiction() -> None:
    a = _record(claim="Cobimetinib was effective and the patient improved.")
    b = _record(
        pmid="88888888",
        claim="Cobimetinib was ineffective with no response.",
        source_url="https://pubmed.ncbi.nlm.nih.gov/88888888/",
        source_title="Other",
        doi=None,
        supporting_text="Cobimetinib was ineffective with no response.",
    )
    article_a = _article()
    article_b = _article(
        pmid="88888888",
        title="Other",
        abstract="Cobimetinib was ineffective with no response.",
        doi=None,
        pubmed_url="https://pubmed.ncbi.nlm.nih.gov/88888888/",
    )
    # Fix b provenance fields for its article
    b = b.model_copy(
        update={
            "source_title": article_b.title,
            "doi": None,
        }
    )
    results = critique_evidence_set([a, b], [article_a, article_b])
    labels = {r.record.pmid: r.label for r in results}
    assert CritiqueLabel.CONTRADICTED in labels.values() or any(
        f.code == "possible_contradiction" for r in results for f in r.findings
    )


def test_synthesize_report_excludes_unsupported() -> None:
    good = critique_evidence_record(_record(), _article())
    bad = critique_evidence_record(
        _record(
            claim="The patient carried a BRAF V600E mutation.",
            supporting_text="We report one patient with ECD treated with cobimetinib who improved.",
        ),
        _article(),
    )
    trial = ClinicalTrial(
        nct_id="NCT05001828",
        title="Example trial",
        status="RECRUITING",
        url="https://clinicaltrials.gov/study/NCT05001828",
    )
    report = synthesize_report(
        "What is the evidence for cobimetinib in ECD?",
        [good, bad],
        trials=[trial],
    )
    md = render_report_markdown(report)
    assert "BOTTOM LINE" in md
    assert "QUESTIONS FOR AN ECD SPECIALIST" in md
    assert "NCT05001828" in md
    assert report.critique_summary[CritiqueLabel.UNSUPPORTED.value] == 1
    assert "Research aid only" in report.disclaimer
