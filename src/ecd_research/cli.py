"""CLI: search the newest Erdheim-Chester disease papers on PubMed."""

from __future__ import annotations

import argparse
import sys

from ecd_research.tools.pubmed import get_pubmed_articles, search_pubmed

DEFAULT_QUERY = "Erdheim-Chester disease"
DEFAULT_MAX_RESULTS = 10


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Search PubMed for Erdheim-Chester disease papers (newest first)."
    )
    parser.add_argument(
        "--query",
        default=DEFAULT_QUERY,
        help=f'Search query (default: "{DEFAULT_QUERY}")',
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum number of papers (default: {DEFAULT_MAX_RESULTS})",
    )
    args = parser.parse_args(argv)

    pmids = search_pubmed(args.query, max_results=args.max_results)
    if not pmids:
        print("No PubMed results found.", file=sys.stderr)
        return 1

    articles = get_pubmed_articles(pmids)
    for i, article in enumerate(articles, start=1):
        print(f"{i}. PMID: {article.pmid}")
        print(f"   Title: {article.title or '(not available)'}")
        print(f"   Publication date: {article.publication_date or '(not available)'}")
        print(f"   Journal: {article.journal or '(not available)'}")
        print(f"   PubMed URL: {article.pubmed_url}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
