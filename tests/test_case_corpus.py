"""Tests for case corpus orchestration."""

from __future__ import annotations

from ecd_research.cases.corpus import run_case_corpus
from ecd_research.cases.extractor import EXTRACTOR_PROMPT_VERSION
from ecd_research.models import (
    CaseRecord,
    DiseaseLabel,
    FullTextDocument,
    FullTextSection,
    PubMedArticle,
    TherapyTiming,
)


def _article(pmid: str) -> PubMedArticle:
    return PubMedArticle(
        pmid=pmid,
        title=f"Case report: CNS ECD patient {pmid}",
        authors=["Author"],
        journal="Case Reports",
        publication_date="2025",
        abstract=(
            "We report a patient with CNS Erdheim-Chester disease and BRAF V600E. "
            "Dabrafenib and trametinib were started early with neurologic improvement."
        ),
        doi=None,
        pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def _case_record(pmid: str) -> CaseRecord:
    article = _article(pmid)
    return CaseRecord(
        pmid=pmid,
        source_title=article.title,
        source_url=str(article.pubmed_url),
        publication_date=article.publication_date,
        journal=article.journal,
        doi=article.doi,
        disease_label=DiseaseLabel.ECD,
        case_count=1,
        cns_involvement=True,
        mutation="BRAF V600E",
        therapies=["dabrafenib", "trametinib"],
        therapy_timing=TherapyTiming.EARLY,
        neurologic_outcome="neurologic improvement",
        supporting_text=(
            "Dabrafenib and trametinib were started early with neurologic improvement."
        ),
        source_fields_used=["abstract"],
        limitations=["n=1"],
        abstract_limited=True,
        extractor_model="test-model",
        extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        validation_status="validated",
    )


def test_run_case_corpus_with_injected_dependencies(tmp_path) -> None:
    articles = [_article("11111111"), _article("22222222")]

    def search_fn(query: str, max_results: int) -> list[str]:
        return ["11111111", "22222222"]

    def fetch_fn(pmids: list[str]) -> list[PubMedArticle]:
        return articles

    def extract_fn(
        article: PubMedArticle, question: str, *, full_text=None
    ) -> list[CaseRecord]:
        return [_case_record(article.pmid)]

    result = run_case_corpus(
        "CNS ECD BRAF therapy timing",
        save=True,
        db_path=str(tmp_path / "cases.db"),
        search_fn=search_fn,
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        max_articles_to_extract=2,
    )

    assert len(result.pmids) == 2
    assert len(result.case_records) == 2
    assert result.aggregation is not None
    assert result.aggregation.records_analyzed == 2
    assert result.run_id is not None
    assert result.warnings


def test_run_case_corpus_with_full_text_injection(tmp_path) -> None:
    articles = [_article("41562816")]

    full_text = FullTextDocument(
        pmid="41562816",
        pmcid="PMC12821489",
        source_url="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12821489/",
        sections=[
            FullTextSection(
                title="Outcome",
                text="Dabrafenib and trametinib started 6 years after symptom onset.",
            )
        ],
        raw_text="Dabrafenib and trametinib started 6 years after symptom onset.",
    )

    def fetch_fn(pmids: list[str]) -> list[PubMedArticle]:
        return articles

    def full_text_fn(pmid: str) -> FullTextDocument | None:
        return full_text if pmid == "41562816" else None

    def extract_fn(
        article: PubMedArticle, question: str, *, full_text=None
    ) -> list[CaseRecord]:
        assert full_text is not None
        return [_case_record(article.pmid)]

    result = run_case_corpus(
        "CNS ECD BRAF therapy timing",
        pmids=["41562816"],
        use_full_text=True,
        fetch_fn=fetch_fn,
        full_text_fn=full_text_fn,
        extract_fn=extract_fn,
    )

    assert result.full_text_pmids == ["41562816"]
    assert len(result.case_records) == 1
    assert any("full_text_available=1" in n for n in result.notes)


def test_run_case_corpus_citation_expansion_adds_neighbors() -> None:
    seed = _article("41562816")
    neighbor = _article("99900001")

    def fetch_fn(pmids: list[str]) -> list[PubMedArticle]:
        by_id = {"41562816": seed, "99900001": neighbor}
        return [by_id[p] for p in pmids if p in by_id]

    def extract_fn(
        article: PubMedArticle, question: str, *, full_text=None
    ) -> list[CaseRecord]:
        return [_case_record(article.pmid)]

    def citation_expand_fn(seeds, **kwargs):
        assert seeds == ["41562816"]
        return ["99900001"], {"41562816": ["99900001"]}

    result = run_case_corpus(
        "CNS ECD BRAF therapy timing",
        pmids=["41562816"],
        expand_citations=True,
        citation_seeds=["41562816"],
        fetch_fn=fetch_fn,
        extract_fn=extract_fn,
        citation_expand_fn=citation_expand_fn,
        max_articles_to_extract=5,
    )

    assert "99900001" in result.pmids
    assert result.citation_expanded_pmids == ["99900001"]
    assert {a.pmid for a in result.selected_articles} >= {"41562816", "99900001"}
    assert any("citation_neighbors=1" in n for n in result.notes)
