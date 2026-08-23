"""CLI: run Quick or Deep ECD literature research."""

from __future__ import annotations

import argparse
import sys

from ecd_research.research.loop import ResearchMode, run_research
from ecd_research.storage import default_db_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run multi-round ECD research (PubMed + optional trials). "
            "Research aid only — not medical advice."
        )
    )
    parser.add_argument("--question", required=True, help="Research question")
    parser.add_argument(
        "--mode",
        choices=[m.value for m in ResearchMode],
        default=ResearchMode.DEEP.value,
        help="quick=1 round, deep=2 rounds (default: deep)",
    )
    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=8,
        help="PubMed retmax per query (default: 8)",
    )
    parser.add_argument(
        "--max-extract",
        type=int,
        default=5,
        help="Max articles to run evidence extraction on (default: 5)",
    )
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Skip LLM evidence extraction",
    )
    parser.add_argument(
        "--no-trials",
        action="store_true",
        help="Skip ClinicalTrials.gov search",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Persist run audit + validated evidence to SQLite",
    )
    parser.add_argument("--db", default=None, help=f"SQLite path (default: {default_db_path()})")
    args = parser.parse_args(argv)

    print("Disclaimer: research aid only. Not a diagnosis or treatment recommendation.\n")

    result = run_research(
        args.question,
        mode=ResearchMode(args.mode),
        max_results_per_query=args.max_results_per_query,
        max_articles_to_extract=args.max_extract,
        extract=not args.no_extract,
        include_trials=not args.no_trials,
        save=args.save,
        db_path=args.db,
    )

    print(f"Question: {result.question}")
    print(f"Mode: {result.mode.value} ({len(result.rounds)} round(s))")
    print(f"Strategy queries: {len(result.strategy.pubmed_queries)}")
    for rnd in result.rounds:
        print(
            f"  Round {rnd.round_index}: {len(rnd.queries)} queries, "
            f"{len(rnd.new_pmids)} new PMIDs"
        )
    print(f"Unique PMIDs: {len(result.pmids)}")
    print(f"Articles fetched: {len(result.articles)}")
    print(f"Validated evidence records: {len(result.evidence)}")
    print(f"Trials: {len(result.trials)}")
    if result.run_id is not None:
        print(f"Saved search run id: {result.run_id}")

    print("\nTop articles:")
    for i, article in enumerate(result.articles[:10], start=1):
        print(f"  {i}. {article.pmid} | {article.title or '(no title)'} | {article.pubmed_url}")

    if result.trials:
        print("\nTrials:")
        for i, trial in enumerate(result.trials[:5], start=1):
            print(
                f"  {i}. {trial.nct_id} | {trial.status or '(status n/a)'} | "
                f"{trial.title or '(no title)'} | {trial.url}"
            )

    if result.evidence:
        print("\nEvidence samples:")
        for i, record in enumerate(result.evidence[:5], start=1):
            print(f"  {i}. [{record.evidence_strength.value}] {record.claim}")

    return 0 if result.pmids or result.trials else 1


if __name__ == "__main__":
    raise SystemExit(main())
