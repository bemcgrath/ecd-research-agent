"""Tests for the iterative research loop."""

from __future__ import annotations

from ecd_research.models import ClinicalTrial, PubMedArticle
from ecd_research.research.loop import ResearchMode, run_research


def _article(pmid: str, title: str) -> PubMedArticle:
    return PubMedArticle(
        pmid=pmid,
        title=title,
        authors=[],
        journal=None,
        publication_date=None,
        abstract=f"Abstract for {pmid}.",
        doi=None,
        pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def test_deep_mode_runs_two_rounds(tmp_path) -> None:
    calls: list[str] = []

    def fake_search(query: str, max_results: int = 20) -> list[str]:
        calls.append(query)
        # Distinct PMIDs per query so round novelty is observable.
        idx = len(calls)
        return [f"{10000000 + idx}", f"{20000000 + idx}"]

    def fake_fetch(pmids: list[str]) -> list[PubMedArticle]:
        return [_article(p, f"Title {p}") for p in pmids]

    def fake_trials(condition: str, status=None, page_size: int = 20):
        return [
            ClinicalTrial(
                nct_id="NCT05001828",
                title="Example",
                status="RECRUITING",
                url="https://clinicaltrials.gov/study/NCT05001828",
            )
        ]

    result = run_research(
        "What is the evidence for treating neurological ECD with BRAF/MEK therapy?",
        mode=ResearchMode.DEEP,
        extract=False,
        include_trials=True,
        save=True,
        db_path=str(tmp_path / "run.db"),
        search_fn=fake_search,
        fetch_fn=fake_fetch,
        trials_fn=fake_trials,
    )

    assert result.mode == ResearchMode.DEEP
    assert len(result.rounds) == 2
    assert result.rounds[0].queries
    assert result.rounds[1].queries
    assert result.pmids
    assert result.articles
    assert result.trials[0].nct_id == "NCT05001828"
    assert result.run_id is not None
    assert result.question_id is not None


def test_quick_mode_single_round() -> None:
    def fake_search(query: str, max_results: int = 20) -> list[str]:
        return ["42082348"]

    def fake_fetch(pmids: list[str]) -> list[PubMedArticle]:
        return [_article(p, "Live-shaped title") for p in pmids]

    result = run_research(
        "CNS ECD treatments",
        mode=ResearchMode.QUICK,
        extract=False,
        include_trials=False,
        search_fn=fake_search,
        fetch_fn=fake_fetch,
    )
    assert len(result.rounds) == 1
    assert result.pmids == ["42082348"]
    assert result.trials == []
