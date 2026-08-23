"""Orchestrate case corpus search, extraction, and aggregation."""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, Field

from ecd_research.cases.aggregation import CaseAggregationResult, aggregate_case_records
from ecd_research.cases.critic import critique_case_corpus
from ecd_research.cases.extractor import EXTRACTOR_PROMPT_VERSION, extract_case_records
from ecd_research.cases.selection import select_case_report_articles
from ecd_research.models import CaseRecord, PubMedArticle
from ecd_research.research.search_strategy import SearchStrategy, generate_search_strategy
from ecd_research.storage import EvidenceRepository
from ecd_research.tools.pubmed import get_pubmed_articles, search_pubmed


class CaseCorpusRunResult(BaseModel):
    """Outcome of a case corpus research run."""

    question: str
    strategy: SearchStrategy
    pmids: list[str] = Field(default_factory=list)
    articles: list[PubMedArticle] = Field(default_factory=list)
    selected_articles: list[PubMedArticle] = Field(default_factory=list)
    case_records: list[CaseRecord] = Field(default_factory=list)
    aggregation: CaseAggregationResult | None = None
    warnings: list[str] = Field(default_factory=list)
    question_id: int | None = None
    run_id: int | None = None
    notes: list[str] = Field(default_factory=list)


def run_case_corpus(
    question: str,
    *,
    max_results_per_query: int = 15,
    max_articles_to_extract: int = 10,
    extraction_scan_limit: int = 40,
    save: bool = False,
    db_path: str | None = None,
    search_fn: Callable[[str, int], list[str]] = search_pubmed,
    fetch_fn: Callable[[list[str]], list[PubMedArticle]] = get_pubmed_articles,
    extract_fn: Callable[..., list[CaseRecord]] = extract_case_records,
) -> CaseCorpusRunResult:
    """Search PubMed, extract structured case records, and aggregate."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    cleaned = question.strip()
    strategy = generate_search_strategy(cleaned)

    seen: set[str] = set()
    ordered_pmids: list[str] = []
    for query in strategy.pubmed_queries:
        for pmid in search_fn(query, max_results_per_query):
            if pmid not in seen:
                seen.add(pmid)
                ordered_pmids.append(pmid)

    articles = fetch_fn(ordered_pmids) if ordered_pmids else []
    selected = select_case_report_articles(
        articles,
        cleaned,
        max_articles=max_articles_to_extract,
        scan_limit=extraction_scan_limit,
    )

    case_records: list[CaseRecord] = []
    for article in selected:
        case_records.extend(extract_fn(article, cleaned))

    aggregation = aggregate_case_records(case_records, research_question=cleaned)
    warnings = critique_case_corpus(aggregation)

    notes = [
        f"unique_pmids={len(ordered_pmids)}",
        f"articles_fetched={len(articles)}",
        f"case_reports_selected={len(selected)}",
        f"case_records={len(case_records)}",
        f"validated_records={aggregation.records_analyzed}",
        "Case extraction is abstract-limited until full-text support exists.",
        "Research aid only — not a diagnosis or treatment recommendation.",
    ]

    question_id: int | None = None
    run_id: int | None = None
    if save:
        with EvidenceRepository(db_path) as repo:
            question_id = repo.get_or_create_question(cleaned)
            model_name = case_records[0].extractor_model if case_records else None
            run_id = repo.start_search_run(
                question_id,
                extractor_model=model_name,
                extractor_prompt_version=EXTRACTOR_PROMPT_VERSION if case_records else None,
                notes="case_corpus run",
            )
            for query in strategy.pubmed_queries:
                repo.add_search_query(
                    run_id,
                    query=query,
                    source="pubmed",
                    pmids=ordered_pmids,
                )
            for article in articles:
                repo.upsert_article(article)
            for record in case_records:
                if record.validation_status == "validated":
                    repo.save_case_record(
                        record, question_id=question_id, run_id=run_id
                    )
            repo.finish_search_run(run_id)

    return CaseCorpusRunResult(
        question=cleaned,
        strategy=strategy,
        pmids=ordered_pmids,
        articles=articles,
        selected_articles=selected,
        case_records=case_records,
        aggregation=aggregation,
        warnings=warnings,
        question_id=question_id,
        run_id=run_id,
        notes=notes,
    )
