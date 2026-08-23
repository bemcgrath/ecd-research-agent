"""CLI: search case reports, extract structured fields, and aggregate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ecd_research.cases.corpus import run_case_corpus
from ecd_research.cases.report import render_case_corpus_markdown
from ecd_research.storage import default_db_path

DEFAULT_QUESTION = (
    "Across published CNS-ECD and relevant mixed histiocytosis cases, what does "
    "the literature report about timing of BRAF/MEK-targeted therapy and neurologic "
    "outcomes?"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search PubMed for case reports, extract structured case fields, "
            "and aggregate into a citation-bound table. Research aid only — not medical advice."
        )
    )
    parser.add_argument(
        "--question",
        default=DEFAULT_QUESTION,
        help="Research question guiding case selection and extraction",
    )
    parser.add_argument(
        "--max-results-per-query",
        type=int,
        default=15,
        help="Max PubMed results per search query (default: 15)",
    )
    parser.add_argument(
        "--max-extract",
        type=int,
        default=10,
        help="Max case-report articles to extract (default: 10)",
    )
    parser.add_argument(
        "--scan-limit",
        type=int,
        default=40,
        help="Candidate articles to scan before selection (default: 40)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Persist articles and validated case records to SQLite",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"SQLite path (default: {default_db_path()})",
    )
    parser.add_argument(
        "--output",
        default="case_corpus_report.md",
        help="Markdown output path (default: case_corpus_report.md)",
    )
    args = parser.parse_args(argv)

    print(
        "Disclaimer: research aid only. Not a diagnosis or treatment recommendation.\n"
    )
    print(f"Question: {args.question}\n")

    result = run_case_corpus(
        args.question,
        max_results_per_query=args.max_results_per_query,
        max_articles_to_extract=args.max_extract,
        extraction_scan_limit=args.scan_limit,
        save=args.save,
        db_path=args.db,
    )

    if result.aggregation is None:
        print("No aggregation produced.", file=sys.stderr)
        return 1

    markdown = render_case_corpus_markdown(
        result.aggregation,
        warnings=result.warnings,
        notes=result.notes,
    )
    output_path = Path(args.output)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"PMIDs found: {len(result.pmids)}")
    print(f"Case reports selected: {len(result.selected_articles)}")
    print(f"Case records extracted: {len(result.case_records)}")
    print(f"Validated records: {result.aggregation.records_analyzed}")
    print(f"Report written to: {output_path.resolve()}")
    if args.save and result.run_id is not None:
        print(f"Saved to database (run id: {result.run_id})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
