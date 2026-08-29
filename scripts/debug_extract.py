"""One-off debug script for evidence extraction."""
from openai import OpenAI

from ecd_research.evidence.extractor import (
    DEFAULT_MODEL,
    _call_openai,
    extract_evidence,
)
from ecd_research.evidence.extractor import _to_evidence_record
from ecd_research.evidence.validator import validate_evidence_record
from ecd_research.tools.pubmed import get_pubmed_articles, search_pubmed

QUESTION = (
    "What is the current evidence for treating neurological involvement in "
    "Erdheim-Chester disease, and how does molecular status affect treatment evidence?"
)


def main() -> None:
    pmids = search_pubmed('"Erdheim-Chester disease" AND neurologic', max_results=8)
    print("pmids:", pmids)
    client = OpenAI()
    for pmid in pmids:
        article = get_pubmed_articles([pmid])[0]
        abstract_len = len(article.abstract or "")
        print(f"\n{pmid} abstract_len={abstract_len} title={article.title!r}")
        if abstract_len < 40:
            continue
        payload = _call_openai(
            research_question=QUESTION,
            article=article,
            model=DEFAULT_MODEL,
            client=client,
        )
        print("  model records:", len(payload.records))
        for i, claim in enumerate(payload.records[:2]):
            print(f"    [{i}] {claim.claim[:120]}")
        validated = extract_evidence(article, QUESTION, client=client)
        print("  validated:", len(validated))
        if payload.records and not validated:
            rec = _to_evidence_record(payload.records[0], article, model=DEFAULT_MODEL)
            v = validate_evidence_record(rec, article)
            print("  validation errors:", v.errors)
        if validated:
            return


if __name__ == "__main__":
    main()
