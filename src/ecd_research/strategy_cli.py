"""CLI: expand a research question into PubMed search queries."""

from __future__ import annotations

import argparse
import sys

from ecd_research.research.search_strategy import generate_search_strategy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate PubMed search queries from a research question."
    )
    parser.add_argument("--question", required=True, help="Research question")
    parser.add_argument(
        "--max-queries",
        type=int,
        default=12,
        help="Maximum number of PubMed queries (default: 12)",
    )
    args = parser.parse_args(argv)

    strategy = generate_search_strategy(args.question, max_queries=args.max_queries)
    print(f"Question: {strategy.question}")
    print(f"Focus categories: {', '.join(strategy.focus_categories) or '(none)'}")
    print(f"Matched terms: {', '.join(strategy.matched_terms) or '(none)'}")
    print("PubMed queries:")
    for i, query in enumerate(strategy.pubmed_queries, start=1):
        print(f"  {i}. {query}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
