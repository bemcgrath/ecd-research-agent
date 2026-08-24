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
from ecd_research.cases.report import render_case_corpus_markdown
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


def test_build_case_source_corpus_includes_abstract_and_full_text() -> None:
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
    assert "We report a 45-year-old patient" in corpus or "CNS Erdheim-Chester" in corpus


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


def test_aggregate_marks_likely_same_patient_duplicates() -> None:
    shared_outcome = (
        "After seven months SARA score from 21/40 to 13/40 and ICARS from "
        "33/100 to 28/100; ataxia persisted after 21 months."
    )
    a = _case_record(
        pmid="41562816",
        source_url="https://pubmed.ncbi.nlm.nih.gov/41562816/",
        mutation="BRAF V600E",
        therapy_timing=TherapyTiming.DELAYED,
        neurologic_outcome=shared_outcome,
        supporting_text=shared_outcome,
        symptoms_to_diagnosis="4 years",
        diagnosis_to_treatment="2 years",
        validation_status="validated",
        abstract_limited=False,
    )
    b = _case_record(
        pmid="29096034",
        source_url="https://pubmed.ncbi.nlm.nih.gov/29096034/",
        mutation="BRAF V600E",
        therapy_timing=TherapyTiming.DELAYED,
        neurologic_outcome=(
            "SARA improved to 13/40 and ICARS to 28/100; after 21 months "
            "SARA 17/40 and ICARS 31/100 persisted."
        ),
        supporting_text=(
            "After 7 months SARA 13/40 ICARS 28/100; symptoms for 4 years; "
            "treatment delayed 2 years."
        ),
        symptoms_to_diagnosis="4 years",
        diagnosis_to_treatment="2 years",
        validation_status="validated",
        abstract_limited=True,
    )
    result = aggregate_case_records([a, b], research_question="dup test")
    assert result.records_analyzed == 2
    assert result.records_analyzed_unique == 1
    assert result.duplicate_pairs
    assert result.delayed_therapy == 1
    dup_rows = [r for r in result.case_table_rows if r.likely_duplicate_of]
    assert len(dup_rows) == 1
    assert dup_rows[0].pmid == "29096034"
    assert dup_rows[0].likely_duplicate_of == "41562816"
    assert any("same-patient duplicates" in g for g in result.gaps)


def test_aggregate_separates_review_or_large_series() -> None:
    case = _case_record(
        pmid="11111111",
        source_url="https://pubmed.ncbi.nlm.nih.gov/11111111/",
        case_count=1,
        validation_status="validated",
    )
    series = _case_record(
        pmid="22222222",
        source_title="Systematic review of Erdheim-Chester disease treatments",
        source_url="https://pubmed.ncbi.nlm.nih.gov/22222222/",
        case_count=32,
        validation_status="validated",
        therapy_timing=TherapyTiming.EARLY,
    )
    result = aggregate_case_records([case, series], research_question="split")
    assert len(result.case_table_rows) == 1
    assert result.case_table_rows[0].pmid == "11111111"
    assert len(result.review_series_table_rows) == 1
    assert result.review_series_table_rows[0].pmid == "22222222"
    assert result.records_analyzed_unique == 1
    assert result.early_therapy == 0  # series excluded from unique timing
    assert result.delayed_therapy == 1
    markdown = render_case_corpus_markdown(result)
    assert "## Single-case / small-series table" in markdown
    assert "## Reviews / large series" in markdown


def test_critique_case_corpus_warns_on_small_n() -> None:
    records = [_case_record(validation_status="validated")]
    aggregation = aggregate_case_records(records, research_question="test")
    warnings = critique_case_corpus(aggregation)
    assert any("too few" in w.lower() for w in warnings)
    assert any("cannot prove" in w.lower() for w in warnings)


def test_critique_mentions_duplicates_and_reviews() -> None:
    shared = "SARA 21/40 to 13/40 and ICARS 33/100 to 28/100 after delayed therapy."
    records = [
        _case_record(
            pmid="41562816",
            source_url="https://pubmed.ncbi.nlm.nih.gov/41562816/",
            mutation="BRAF V600E",
            therapy_timing=TherapyTiming.DELAYED,
            neurologic_outcome=shared,
            supporting_text=shared + " 4 years symptoms 2 years to treatment.",
            validation_status="validated",
        ),
        _case_record(
            pmid="29096034",
            source_url="https://pubmed.ncbi.nlm.nih.gov/29096034/",
            mutation="BRAF V600E",
            therapy_timing=TherapyTiming.DELAYED,
            neurologic_outcome=shared,
            supporting_text=shared + " 4 years symptoms 2 years to treatment.",
            validation_status="validated",
        ),
        _case_record(
            pmid="33333333",
            source_title="Systematic review of CNS ECD",
            source_url="https://pubmed.ncbi.nlm.nih.gov/33333333/",
            case_count=20,
            validation_status="validated",
        ),
    ]
    aggregation = aggregate_case_records(records, research_question="critic")
    warnings = critique_case_corpus(aggregation)
    assert any("duplicate" in w.lower() for w in warnings)
    assert any("review" in w.lower() or "large-series" in w.lower() for w in warnings)


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
