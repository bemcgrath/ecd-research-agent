"""CLI: extract validated evidence claims from one PubMed article."""

from __future__ import annotations

import argparse
import sys

from ecd_research.evidence.extractor import EXTRACTOR_PROMPT_VERSION, extract_evidence
from ecd_research.storage import EvidenceRepository, default_db_path
from ecd_research.tools.pubmed import get_pubmed_articles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract validated, abstract-limited evidence claims from one PubMed article. "
            "Research aid only — not medical advice."
        )
    )
    parser.add_argument("--pmid", required=True, help="PubMed PMID (digits only)")
    parser.add_argument(
        "--question",
        required=True,
        help="Research question guiding evidence extraction",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="OpenAI model override (default: OPENAI_MODEL or gpt-4.1-mini)",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Persist article and validated evidence records to SQLite",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=f"SQLite path (default: {default_db_path()})",
    )
    args = parser.parse_args(argv)

    articles = get_pubmed_articles([args.pmid])
    if not articles:
        print(f"No PubMed article found for PMID {args.pmid}", file=sys.stderr)
        return 1

    article = articles[0]
    print(
        "Disclaimer: research aid only. Not a diagnosis or treatment recommendation.\n"
    )
    print(f"PMID: {article.pmid}")
    print(f"Title: {article.title or '(not available)'}")
    print(f"URL: {article.pubmed_url}")
    print(f"Question: {args.question}\n")

    records = extract_evidence(article, args.question, model=args.model)
    if not records:
        print("No validated evidence records extracted.")
        return 0

    for i, record in enumerate(records, start=1):
        print(f"{i}. Claim: {record.claim}")
        print(
            f"   Study type: {record.study_type.value if record.study_type else '(unknown)'}"
        )
        print(f"   Strength: {record.evidence_strength.value}")
        print(f"   Abstract-limited: {record.abstract_limited}")
        print(f"   Supporting text: {record.supporting_text}")
        print(f"   Validation: {record.validation_status}")
        print()

    if args.save:
        db_path = args.db or str(default_db_path())
        with EvidenceRepository(db_path) as repo:
            repo.upsert_article(article)
            question_id = repo.get_or_create_question(args.question)
            run_id = repo.start_search_run(
                question_id,
                extractor_model=records[0].extractor_model,
                extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
                notes=f"single-pmid extract pmid={article.pmid}",
            )
            repo.add_search_query(
                run_id,
                query=f"pmid:{article.pmid}",
                source="pubmed",
                pmids=[article.pmid],
            )
            saved_ids: list[int] = []
            for record in records:
                saved_ids.append(
                    repo.save_evidence_record(
                        record, question_id=question_id, run_id=run_id
                    )
                )
            repo.finish_search_run(run_id)
        print(f"Saved {len(saved_ids)} evidence record(s) to {db_path}")
        print(f"Search run id: {run_id}; evidence ids: {saved_ids}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
