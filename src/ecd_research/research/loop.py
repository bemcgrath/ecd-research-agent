"""Iterative research loop over PubMed and ClinicalTrials.gov."""

from __future__ import annotations

from enum import Enum
from typing import Callable

from pydantic import BaseModel, Field

from ecd_research.evidence.extractor import EXTRACTOR_PROMPT_VERSION, extract_evidence
from ecd_research.models import ClinicalTrial, EvidenceRecord, PubMedArticle
from ecd_research.research.search_strategy import SearchStrategy, generate_search_strategy
from ecd_research.storage import EvidenceRepository
from ecd_research.tools.clinical_trials import search_clinical_trials
from ecd_research.tools.pubmed import get_pubmed_articles, search_pubmed


class ResearchMode(str, Enum):
    QUICK = "quick"  # one search round
    DEEP = "deep"  # two search rounds (minimum deep-research behavior)


class ResearchRoundResult(BaseModel):
    round_index: int
    queries: list[str] = Field(default_factory=list)
    pmids_found: list[str] = Field(default_factory=list)
    new_pmids: list[str] = Field(default_factory=list)


class ResearchRunResult(BaseModel):
    """Outcome of a multi-round research run (audit-friendly)."""

    question: str
    mode: ResearchMode
    strategy: SearchStrategy
    rounds: list[ResearchRoundResult] = Field(default_factory=list)
    pmids: list[str] = Field(default_factory=list)
    articles: list[PubMedArticle] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    trials: list[ClinicalTrial] = Field(default_factory=list)
    question_id: int | None = None
    run_id: int | None = None
    notes: list[str] = Field(default_factory=list)


def _chunk_queries(queries: list[str], mode: ResearchMode) -> list[list[str]]:
    if not queries:
        return [[]]
    if mode == ResearchMode.QUICK:
        return [queries[: min(4, len(queries))]]
    # Deep: two rounds — first half then remainder (at least one query each when possible).
    mid = max(1, min(len(queries) // 2, len(queries) - 1)) if len(queries) > 1 else 1
    round1 = queries[:mid]
    round2 = queries[mid:]
    return [round1, round2] if round2 else [round1]


def run_research(
    question: str,
    *,
    mode: ResearchMode = ResearchMode.DEEP,
    max_results_per_query: int = 10,
    max_articles_to_extract: int = 5,
    extract: bool = True,
    include_trials: bool = True,
    save: bool = False,
    db_path: str | None = None,
    search_fn: Callable[[str, int], list[str]] = search_pubmed,
    fetch_fn: Callable[[list[str]], list[PubMedArticle]] = get_pubmed_articles,
    trials_fn: Callable[..., list[ClinicalTrial]] = search_clinical_trials,
    extract_fn: Callable[..., list[EvidenceRecord]] = extract_evidence,
) -> ResearchRunResult:
    """Run Quick (1 round) or Deep (2 round) literature research.

    Extraction uses abstracts only and provenance validation. Missing stays missing.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    strategy = generate_search_strategy(question)
    query_rounds = _chunk_queries(strategy.pubmed_queries, mode)

    seen: set[str] = set()
    ordered_pmids: list[str] = []
    rounds: list[ResearchRoundResult] = []

    for idx, queries in enumerate(query_rounds, start=1):
        found: list[str] = []
        new: list[str] = []
        for query in queries:
            pmids = search_fn(query, max_results_per_query)
            for pmid in pmids:
                if pmid not in found:
                    found.append(pmid)
                if pmid not in seen:
                    seen.add(pmid)
                    ordered_pmids.append(pmid)
                    new.append(pmid)
        rounds.append(
            ResearchRoundResult(
                round_index=idx,
                queries=list(queries),
                pmids_found=found,
                new_pmids=new,
            )
        )

    articles = fetch_fn(ordered_pmids) if ordered_pmids else []

    evidence: list[EvidenceRecord] = []
    if extract and articles:
        for article in articles[:max_articles_to_extract]:
            evidence.extend(extract_fn(article, question.strip()))

    trials: list[ClinicalTrial] = []
    if include_trials:
        trials = trials_fn("Erdheim-Chester disease", page_size=10)

    notes = [
        f"mode={mode.value}",
        f"rounds={len(rounds)}",
        f"unique_pmids={len(ordered_pmids)}",
        f"articles_fetched={len(articles)}",
        f"evidence_records={len(evidence)}",
        f"trials={len(trials)}",
        "Evidence extraction is abstract-limited until full-text support exists.",
        "Research aid only — not a diagnosis or treatment recommendation.",
    ]

    question_id: int | None = None
    run_id: int | None = None
    if save:
        with EvidenceRepository(db_path) as repo:
            question_id = repo.get_or_create_question(question.strip())
            model_name = evidence[0].extractor_model if evidence else None
            run_id = repo.start_search_run(
                question_id,
                extractor_model=model_name,
                extractor_prompt_version=EXTRACTOR_PROMPT_VERSION if evidence else None,
                notes=f"research_loop mode={mode.value}",
            )
            for round_result in rounds:
                for query in round_result.queries:
                    repo.add_search_query(
                        run_id,
                        query=query,
                        source="pubmed",
                        pmids=round_result.pmids_found,
                    )
            for article in articles:
                repo.upsert_article(article)
            for record in evidence:
                if record.validation_status == "validated":
                    repo.save_evidence_record(
                        record, question_id=question_id, run_id=run_id
                    )
            repo.finish_search_run(run_id)

    return ResearchRunResult(
        question=question.strip(),
        mode=mode,
        strategy=strategy,
        rounds=rounds,
        pmids=ordered_pmids,
        articles=articles,
        evidence=evidence,
        trials=trials,
        question_id=question_id,
        run_id=run_id,
        notes=notes,
    )
