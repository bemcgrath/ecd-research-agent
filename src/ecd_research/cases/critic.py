"""Critic warnings for case corpus aggregation."""

from __future__ import annotations

from ecd_research.cases.aggregation import CaseAggregationResult


def critique_case_corpus(aggregation: CaseAggregationResult) -> list[str]:
    """Return deterministic warnings about over-interpretation of case corpora."""
    warnings: list[str] = []
    n = aggregation.records_analyzed

    if n == 0:
        warnings.append("No validated cases to analyze; cannot answer aggregation questions.")
        return warnings

    if n < 5:
        warnings.append(
            f"Only {n} validated case record(s) — far too few for population-level inference."
        )

    if aggregation.timing_reported == 0:
        warnings.append(
            "No records report therapy timing; early-vs-late comparisons are not possible "
            "from this corpus."
        )
    elif aggregation.timing_reported < n:
        warnings.append(
            f"Therapy timing reported in only {aggregation.timing_reported} of {n} records; "
            "any timing comparison is incomplete."
        )

    if aggregation.early_therapy > 0 and aggregation.delayed_therapy > 0:
        warnings.append(
            f"Corpus includes {aggregation.early_therapy} record(s) labeled early therapy and "
            f"{aggregation.delayed_therapy} labeled delayed — descriptive counts only; "
            "not a controlled comparison."
        )

    if aggregation.neurologic_outcome_reported < n:
        warnings.append(
            "Neurologic outcomes are incompletely reported; recovery comparisons are limited."
        )

    warnings.append(
        "Case reports cannot prove that earlier therapy causes better neurologic recovery."
    )

    return warnings
