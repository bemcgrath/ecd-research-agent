"""Debug first-N extraction for benchmark question."""
from ecd_research.evidence.extractor import extract_evidence
from ecd_research.research.loop import ResearchMode, run_research

QUESTION = (
    "What is the current evidence for treating neurological involvement in "
    "Erdheim-Chester disease, and how does molecular status affect treatment evidence?"
)


def main() -> None:
    result = run_research(
        QUESTION,
        mode=ResearchMode.DEEP,
        max_results_per_query=8,
        max_articles_to_extract=5,
        extract=False,
        include_trials=False,
    )
    print("first 8 articles:")
    for a in result.articles[:8]:
        print(
            a.pmid,
            "abstract",
            len(a.abstract or ""),
            "|",
            (a.title or "")[:70],
        )
    print("\nextract each of first 5:")
    total = 0
    for a in result.articles[:5]:
        recs = extract_evidence(a, QUESTION)
        print(f"  {a.pmid}: {len(recs)} validated")
        total += len(recs)
    print("total validated from first 5:", total)


if __name__ == "__main__":
    main()
