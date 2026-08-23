"""Tests for SQLite evidence repository."""

from __future__ import annotations

import pytest

from ecd_research.evidence.extractor import EXTRACTOR_PROMPT_VERSION
from ecd_research.models import (
    CaseRecord,
    DiseaseLabel,
    EvidenceRecord,
    EvidenceStrength,
    PubMedArticle,
    StudyType,
    TherapyTiming,
)
from ecd_research.storage import EvidenceRepository


def _article() -> PubMedArticle:
    return PubMedArticle(
        pmid="99999999",
        title="Complete Erdheim-Chester disease example article",
        authors=["Smith J"],
        journal="Example Journal",
        publication_date="2026 Aug 15",
        abstract="BACKGROUND: Background text about one patient with ECD.",
        doi="10.1000/example.doi",
        pubmed_url="https://pubmed.ncbi.nlm.nih.gov/99999999/",
    )


def _validated_record() -> EvidenceRecord:
    article = _article()
    return EvidenceRecord(
        claim="A single patient with ECD is described.",
        pmid=article.pmid,
        source_title=article.title,
        source_url=str(article.pubmed_url),
        publication_date=article.publication_date,
        journal=article.journal,
        doi=article.doi,
        study_type=StudyType.CASE_REPORT,
        sample_size=1,
        population="one patient with ECD",
        intervention=None,
        comparator=None,
        outcome=None,
        supporting_text="Background text about one patient with ECD.",
        source_fields_used=["abstract"],
        limitations=["n=1"],
        evidence_strength=EvidenceStrength.VERY_LOW,
        reasoning_note="case report; abstract-limited",
        abstract_limited=True,
        extractor_model="test-model",
        extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        validation_status="validated",
    )


def test_upsert_article_and_get(tmp_path) -> None:
    db = tmp_path / "test.db"
    article = _article()
    with EvidenceRepository(str(db)) as repo:
        repo.upsert_article(article)
        loaded = repo.get_article("99999999")
    assert loaded is not None
    assert loaded.pmid == "99999999"
    assert loaded.title == article.title
    assert loaded.authors == ["Smith J"]
    assert loaded.doi == "10.1000/example.doi"


def test_question_run_query_and_evidence_roundtrip(tmp_path) -> None:
    db = tmp_path / "test.db"
    article = _article()
    record = _validated_record()

    with EvidenceRepository(str(db)) as repo:
        repo.upsert_article(article)
        qid = repo.get_or_create_question("What does this paper report about ECD?")
        assert repo.get_or_create_question("What does this paper report about ECD?") == qid

        run_id = repo.start_search_run(
            qid,
            extractor_model="test-model",
            extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        )
        repo.add_search_query(
            run_id, query="pmid:99999999", source="pubmed", pmids=["99999999"]
        )
        eid = repo.save_evidence_record(record, question_id=qid, run_id=run_id)
        repo.finish_search_run(run_id)

        assert eid >= 1
        assert repo.count_evidence() == 1
        by_pmid = repo.list_evidence_for_pmid("99999999")
        by_q = repo.list_evidence_for_question(qid)

    assert len(by_pmid) == 1
    assert len(by_q) == 1
    assert by_pmid[0].claim == record.claim
    assert by_pmid[0].validation_status == "validated"
    assert by_pmid[0].study_type == StudyType.CASE_REPORT
    assert by_pmid[0].extractor_prompt_version == EXTRACTOR_PROMPT_VERSION


def test_rejects_unvalidated_evidence(tmp_path) -> None:
    db = tmp_path / "test.db"
    article = _article()
    record = _validated_record().model_copy(update={"validation_status": "pending"})

    with EvidenceRepository(str(db)) as repo:
        repo.upsert_article(article)
        with pytest.raises(ValueError, match="validated"):
            repo.save_evidence_record(record)


def test_evidence_requires_article_foreign_key(tmp_path) -> None:
    db = tmp_path / "test.db"
    record = _validated_record()
    with EvidenceRepository(str(db)) as repo:
        with pytest.raises(Exception):
            repo.save_evidence_record(record)


def _validated_case_record() -> CaseRecord:
    article = _article()
    return CaseRecord(
        pmid=article.pmid,
        source_title=article.title,
        source_url=str(article.pubmed_url),
        publication_date=article.publication_date,
        journal=article.journal,
        doi=article.doi,
        disease_label=DiseaseLabel.ECD,
        case_count=1,
        cns_involvement=True,
        mutation="BRAF V600E",
        therapies=["dabrafenib"],
        neurologic_outcome="improved",
        supporting_text="Background text about one patient with ECD.",
        source_fields_used=["abstract"],
        limitations=["n=1"],
        abstract_limited=True,
        extractor_model="test-model",
        extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        validation_status="validated",
    )


def test_case_record_roundtrip(tmp_path) -> None:
    db = tmp_path / "test.db"
    article = _article()
    record = _validated_case_record()

    with EvidenceRepository(str(db)) as repo:
        repo.upsert_article(article)
        qid = repo.get_or_create_question("CNS ECD case timing?")
        run_id = repo.start_search_run(qid, notes="case test")
        cid = repo.save_case_record(record, question_id=qid, run_id=run_id)
        repo.finish_search_run(run_id)

        assert cid >= 1
        assert repo.count_case_records() == 1
        loaded = repo.list_case_records_for_question(qid)

    assert len(loaded) == 1
    assert loaded[0].disease_label == DiseaseLabel.ECD
    assert loaded[0].mutation == "BRAF V600E"
    assert loaded[0].validation_status == "validated"
