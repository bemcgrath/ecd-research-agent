"""CLI: search ClinicalTrials.gov for ECD-related studies."""

from __future__ import annotations

import argparse
import sys

from ecd_research.tools.clinical_trials import get_clinical_trial, search_clinical_trials


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Search ClinicalTrials.gov (API v2). Research aid only — not medical advice."
        )
    )
    parser.add_argument(
        "--condition",
        default="Erdheim-Chester disease",
        help='Condition query (default: "Erdheim-Chester disease")',
    )
    parser.add_argument(
        "--status",
        default=None,
        help="Optional overallStatus filter (e.g. RECRUITING)",
    )
    parser.add_argument("--nct", default=None, help="Fetch a single NCT ID instead")
    parser.add_argument("--max-results", type=int, default=10)
    args = parser.parse_args(argv)

    print("Disclaimer: research aid only. Not a diagnosis or treatment recommendation.\n")

    if args.nct:
        trial = get_clinical_trial(args.nct)
        trials = [trial] if trial else []
    else:
        trials = search_clinical_trials(
            args.condition, status=args.status, page_size=args.max_results
        )

    if not trials:
        print("No trials found.", file=sys.stderr)
        return 1

    for i, trial in enumerate(trials, start=1):
        print(f"{i}. {trial.nct_id}")
        print(f"   Title: {trial.title or '(not available)'}")
        print(f"   Status: {trial.status or '(not available)'}")
        print(f"   Phase: {trial.phase or '(not available)'}")
        print(f"   Interventions: {', '.join(trial.interventions) or '(not available)'}")
        print(f"   URL: {trial.url}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
