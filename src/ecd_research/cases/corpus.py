"""Orchestrate case corpus search, extraction, and aggregation."""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, Field

from ecd_research.cases.aggregation import CaseAggregationResult, aggregate_case_records
from ecd_research.cases.critic import critique_case_corpus
from ecd_research.cases.extractor import EXTRACTOR_PROMPT_VERSION, extract_case_records
from ecd_research.cases.selection import select_case_report_articles
from ecd_research.models import CaseRecord, FullTextDocument, PubMedArticle
from ecd_research.research.search_strategy import SearchStrategy, generate_search_strategy
from ecd_research.storage import EvidenceRepository
from ecd_research.tools.pmc import fetch_pmc_full_text
from ecd_research.tools.pubmed import get_pubmed_articles, search_pubmed


class CaseCorpusRunResult(BaseModel):
    """Outcome of a case corpus research run."""

    question: str
    strategy: SearchStrategy | None = None
    pmids: list[str] = Field(default_factory=list)
    articles: list[PubMedArticle] = Field(default_factory=list)
    selected_articles: list[PubMedArticle] = Field(default_factory=list)
    case_records: list[CaseRecord] = Field(default_factory=list)
    full_text_pmids: list[str] = Field(default_factory=list)
    aggregation: CaseAggregationResult | None = None
    warnings: list[str] = Field(default_factory=list)
    question_id: int | None = None
    run_id: int | None = None
    notes: list[str] = Field(default_factory=list)


def _extract_with_optional_full_text(
    article: PubMedArticle,
    question: str,
    *,
    use_full_text: bool,
    extract_fn: Callable[..., list[CaseRecord]],
    full_text_fn: Callable[[str], FullTextDocument | None],
) -> tuple[list[CaseRecord], FullTextDocument | None]:
    full_text: FullTextDocument | None = None
    if use_full_text:
        try:
            full_text = full_text_fn(article.pmid)
        except Exception:
            full_text = None
    records = extract_fn(article, question, full_text=full_text)
    return records, full_text


def run_case_corpus(
    question: str,
    *,
    max_results_per_query: int = 15,
    max_articles_to_extract: int = 10,
    extraction_scan_limit: int = 40,
    use_full_text: bool = False,
    pmids: list[str] | None = None,
    save: bool = False,
    db_path: str | None = None,
    search_fn: Callable[[str, int], list[str]] = search_pubmed,
    fetch_fn: Callable[[list[str]], list[PubMedArticle]] = get_pubmed_articles,
    extract_fn: Callable[..., list[CaseRecord]] = extract_case_records,
    full_text_fn: Callable[[str], FullTextDocument | None] = fetch_pmc_full_text,
) -> CaseCorpusRunResult:
    """Search PubMed, extract structured case records, and aggregate.

    When ``pmids`` is provided, skip search and extract only those articles.
    When ``use_full_text`` is True, attempt PMC open-access full text per article.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    cleaned = question.strip()
    strategy: SearchStrategy | None = None
    ordered_pmids: list[str]

    if pmids is not None:
        ordered_pmids = []
        seen: set[str] = set()
        for pmid in pmids:
            pmid = pmid.strip()
            if pmid and pmid not in seen:
                seen.add(pmid)
                ordered_pmids.append(pmid)
        articles = fetch_fn(ordered_pmids) if ordered_pmids else []
        selected = articles
    else:
        strategy = generate_search_strategy(cleaned)
        seen = set()
        ordered_pmids = []
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
    full_text_pmids: list[str] = []
    for article in selected:
        records, full_text = _extract_with_optional_full_text(
            article,
            cleaned,
            use_full_text=use_full_text,
            extract_fn=extract_fn,
            full_text_fn=full_text_fn,
        )
        if full_text is not None:
            full_text_pmids.append(article.pmid)
        case_records.extend(records)

    aggregation = aggregate_case_records(case_records, research_question=cleaned)
    warnings = critique_case_corpus(aggregation)

    abstract_limited_count = sum(1 for r in case_records if r.abstract_limited)
    notes = [
        f"unique_pmids={len(ordered_pmids)}",
        f"articles_fetched={len(articles)}",
        f"case_reports_selected={len(selected)}",
        f"case_records={len(case_records)}",
        f"validated_records={aggregation.records_analyzed}",
        f"use_full_text={use_full_text}",
        f"full_text_available={len(full_text_pmids)}",
        f"abstract_limited_records={abstract_limited_count}",
        "Research aid only — not a diagnosis or treatment recommendation.",
    ]
    if use_full_text and not full_text_pmids:
        notes.append("No PMC open-access full text available for selected articles.")
    elif not use_full_text:
        notes.append("Abstract-only extraction (pass --full-text to use PMC when available).")

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
                notes=(
                    f"case_corpus run use_full_text={use_full_text} "
                    f"full_text_n={len(full_text_pmids)}"
                ),
            )
            if strategy is not None:
                for query in strategy.pubmed_queries:
                    repo.add_search_query(
                        run_id,
                        query=query,
                        source="pubmed",
                        pmids=ordered_pmids,
                    )
            else:
                repo.add_search_query(
                    run_id,
                    query=f"pmids:{','.join(ordered_pmids)}",
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
        full_text_pmids=full_text_pmids,
        aggregation=aggregation,
        warnings=warnings,
        question_id=question_id,
        run_id=run_id,
        notes=notes,
    )
