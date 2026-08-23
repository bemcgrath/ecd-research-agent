"""CLI: critique evidence and render a synthesis report from a research run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ecd_research.research.critic import critique_evidence_set
from ecd_research.research.loop import ResearchMode, run_research
from ecd_research.research.synthesis import render_report_markdown, synthesize_report
from ecd_research.storage import default_db_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run research, critique evidence, and write a citation-bound report. "
            "Research aid only — not medical advice."
        )
    )
    parser.add_argument("--question", required=True)
    parser.add_argument(
        "--mode",
        choices=[m.value for m in ResearchMode],
        default=ResearchMode.DEEP.value,
    )
    parser.add_argument("--max-results-per-query", type=int, default=8)
    parser.add_argument("--max-extract", type=int, default=5)
    parser.add_argument(
        "--no-extract",
        action="store_true",
        help="Skip LLM extraction (report will have little/no evidence sections)",
    )
    parser.add_argument("--no-trials", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--db", default=None)
    parser.add_argument(
        "--output",
        default="research_report.md",
        help="Markdown output path (default: research_report.md)",
    )
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
        db_path=args.db or str(default_db_path()),
    )

    critiques = critique_evidence_set(result.evidence, result.articles)
    report = synthesize_report(args.question, critiques, trials=result.trials)
    markdown = render_report_markdown(report)

    out = Path(args.output)
    out.write_text(markdown, encoding="utf-8")

    print(f"Rounds: {len(result.rounds)}")
    print(f"PMIDs: {len(result.pmids)}")
    selected = next(
        (n.split("=", 1)[1] for n in result.notes if n.startswith("articles_selected_for_extraction=")),
        "?",
    )
    print(f"Articles scanned for extraction: {selected} (with abstracts + relevance)")
    print(f"Evidence records: {len(result.evidence)}")
    if len(result.evidence) == 0 and not args.no_extract:
        print(
            "\nNote: 0 evidence records usually means the top papers had no usable abstract "
            "or no claims in the abstract matched your question. Try --max-extract 8 or re-run "
            "after updating the tool.",
            file=sys.stderr,
        )
    print(f"Critique summary: {report.critique_summary}")
    print(f"Wrote report: {out.resolve()}")
    print("\nBOTTOM LINE")
    print(report.bottom_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
