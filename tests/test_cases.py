"""Tests for case extraction, validation, aggregation, and selection."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ecd_research.cases.aggregation import aggregate_case_records
from ecd_research.cases.critic import critique_case_corpus
from ecd_research.cases.extractor import (
    EXTRACTOR_PROMPT_VERSION,
    _CaseExtractionPayload,
    _ExtractedCase,
    extract_case_records,
)
from ecd_research.cases.selection import select_case_report_articles
from ecd_research.cases.validator import build_case_source_corpus, validate_case_record
from ecd_research.models import (
    CaseRecord,
    DiseaseLabel,
    FullTextDocument,
    FullTextSection,
    PubMedArticle,
    TherapyTiming,
)


def _article(**overrides: object) -> PubMedArticle:
    base = {
        "pmid": "88888888",
        "title": "Case report: CNS Erdheim-Chester disease with BRAF V600E",
        "authors": ["Jones A"],
        "journal": "Neurology Case Reports",
        "publication_date": "2025 Jan",
        "abstract": (
            "We report a 45-year-old patient with CNS Erdheim-Chester disease. "
            "BRAF V600E was identified. Dabrafenib and trametinib were started "
            "6 months after symptom onset with partial neurologic improvement."
        ),
        "doi": "10.1000/case.doi",
        "pubmed_url": "https://pubmed.ncbi.nlm.nih.gov/88888888/",
    }
    base.update(overrides)
    return PubMedArticle(**base)  # type: ignore[arg-type]


def _case_record(**overrides: object) -> CaseRecord:
    article = _article()
    base = {
        "pmid": article.pmid,
        "source_title": article.title,
        "source_url": str(article.pubmed_url),
        "publication_date": article.publication_date,
        "journal": article.journal,
        "doi": article.doi,
        "disease_label": DiseaseLabel.ECD,
        "case_count": 1,
        "organ_involvement": ["CNS"],
        "cns_involvement": True,
        "mutation": "BRAF V600E",
        "therapies": ["dabrafenib", "trametinib"],
        "symptoms_to_diagnosis": "not reported",
        "diagnosis_to_treatment": "6 months after symptom onset",
        "therapy_timing": TherapyTiming.DELAYED,
        "neurologic_outcome": "partial neurologic improvement",
        "other_outcomes": None,
        "supporting_text": (
            "Dabrafenib and trametinib were started 6 months after symptom onset "
            "with partial neurologic improvement."
        ),
        "source_fields_used": ["abstract"],
        "limitations": ["Single case report; abstract-limited"],
        "abstract_limited": True,
        "extractor_model": "test-model",
        "extractor_prompt_version": EXTRACTOR_PROMPT_VERSION,
        "validation_status": "pending",
    }
    base.update(overrides)
    return CaseRecord(**base)  # type: ignore[arg-type]


def test_validate_case_record_accepts_full_text_grounding() -> None:
    article = _article()
    full_text = FullTextDocument(
        pmid=article.pmid,
        pmcid="PMC12821489",
        title=article.title,
        doi=article.doi,
        source_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12821489/",
        sections=[
            FullTextSection(
                title="Outcome",
                text=(
                    "After seven months of dabrafenib and trametinib, partial neurologic "
                    "improvement was observed."
                ),
            )
        ],
        raw_text=(
            "After seven months of dabrafenib and trametinib, partial neurologic "
            "improvement was observed."
        ),
        abstract_limited=False,
    )
    record = _case_record(
        supporting_text=(
            "After seven months of dabrafenib and trametinib, partial neurologic "
            "improvement was observed."
        ),
        source_fields_used=["full_text"],
        abstract_limited=False,
        pmcid="PMC12821489",
    )
    outcome = validate_case_record(record, article, full_text=full_text)
    assert outcome.ok is True
    assert outcome.record is not None
    assert outcome.record.validation_status == "validated"


def test_build_case_source_corpus_prefers_full_text() -> None:
    article = _article()
    full_text = FullTextDocument(
        pmid=article.pmid,
        pmcid="PMC999",
        source_url="https://example.com/pmc/PMC999/",
        sections=[FullTextSection(title="Body", text="Full text only sentence here.")],
        raw_text="Full text only sentence here.",
    )
    corpus = build_case_source_corpus(article, full_text)
    assert "Full text only sentence here." in corpus


def test_validate_case_record_accepts_grounded_record() -> None:
    article = _article()
    record = _case_record()
    outcome = validate_case_record(record, article)
    assert outcome.ok is True
    assert outcome.record is not None
    assert outcome.record.validation_status == "validated"


def test_validate_case_record_rejects_fabricated_supporting_text() -> None:
    article = _article()
    record = _case_record(supporting_text="This text is not in the abstract.")
    outcome = validate_case_record(record, article)
    assert outcome.ok is False
    assert outcome.record is not None
    assert outcome.record.validation_status == "rejected"


def test_extract_case_records_with_mock_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    article = _article()
    payload = _CaseExtractionPayload(
        records=[
            _ExtractedCase(
                disease_label=DiseaseLabel.ECD,
                case_count=1,
                cns_involvement=True,
                mutation="BRAF V600E",
                therapies=["dabrafenib", "trametinib"],
                diagnosis_to_treatment="6 months after symptom onset",
                therapy_timing=TherapyTiming.DELAYED,
                neurologic_outcome="partial neurologic improvement",
                supporting_text=(
                    "Dabrafenib and trametinib were started 6 months after symptom onset "
                    "with partial neurologic improvement."
                ),
                source_fields_used=["abstract"],
                limitations=["n=1"],
            )
        ]
    )

    def fake_call(**kwargs: object) -> _CaseExtractionPayload:
        return payload

    monkeypatch.setattr(
        "ecd_research.cases.extractor._call_openai",
        fake_call,
    )
    monkeypatch.setattr(
        "ecd_research.cases.extractor.OpenAI",
        MagicMock,
    )

    records = extract_case_records(article, "CNS ECD BRAF therapy timing")
    assert len(records) == 1
    assert records[0].disease_label == DiseaseLabel.ECD
    assert records[0].validation_status == "validated"


def test_aggregate_case_records_counts_and_gaps() -> None:
    records = [
        _case_record(validation_status="validated"),
        _case_record(
            pmid="77777777",
            source_url="https://pubmed.ncbi.nlm.nih.gov/77777777/",
            supporting_text="We report a patient with ECD.",
            therapies=[],
            therapy_timing=TherapyTiming.NOT_REPORTED,
            neurologic_outcome=None,
            validation_status="validated",
        ),
    ]
    result = aggregate_case_records(records, research_question="Timing and outcomes?")
    assert result.records_analyzed == 2
    assert result.total_patients_reported == 2
    assert result.targeted_therapy_reported == 1
    assert result.timing_reported == 1
    assert result.delayed_therapy == 1
    assert len(result.table_rows) == 2
    assert any("population-level causation" in gap for gap in result.gaps)


def test_critique_case_corpus_warns_on_small_n() -> None:
    records = [_case_record(validation_status="validated")]
    aggregation = aggregate_case_records(records, research_question="test")
    warnings = critique_case_corpus(aggregation)
    assert any("too few" in w.lower() for w in warnings)
    assert any("cannot prove" in w.lower() for w in warnings)


def test_select_case_report_articles_prefers_case_reports() -> None:
    case_article = _article(pmid="11111111", pubmed_url="https://pubmed.ncbi.nlm.nih.gov/11111111/")
    review = _article(
        pmid="22222222",
        title="Systematic review of Erdheim-Chester disease",
        abstract="This review summarizes treatment options across many studies.",
        pubmed_url="https://pubmed.ncbi.nlm.nih.gov/22222222/",
    )
    selected = select_case_report_articles(
        [review, case_article],
        "CNS ECD BRAF therapy",
        max_articles=1,
    )
    assert len(selected) == 1
    assert selected[0].pmid == "11111111"
