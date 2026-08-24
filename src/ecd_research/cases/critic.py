"""Critic warnings for case corpus aggregation."""

from __future__ import annotations

from ecd_research.cases.aggregation import CaseAggregationResult


def critique_case_corpus(aggregation: CaseAggregationResult) -> list[str]:
    """Return deterministic warnings about over-interpretation of case corpora."""
    warnings: list[str] = []
    n = aggregation.records_analyzed
    unique_n = aggregation.records_analyzed_unique or n

    if n == 0:
        warnings.append("No validated cases to analyze; cannot answer aggregation questions.")
        return warnings

    if unique_n < 5:
        warnings.append(
            f"Only {unique_n} unique single-case/small-series record(s) after cleanup — "
            "far too few for population-level inference."
        )

    if aggregation.timing_reported == 0:
        warnings.append(
            "No unique records report therapy timing; early-vs-late comparisons are not "
            "possible from this corpus."
        )
    elif aggregation.timing_reported < unique_n:
        warnings.append(
            f"Therapy timing reported in only {aggregation.timing_reported} of {unique_n} "
            "unique records; any timing comparison is incomplete."
        )

    if aggregation.early_therapy > 0 and aggregation.delayed_therapy > 0:
        warnings.append(
            f"Corpus includes {aggregation.early_therapy} unique record(s) labeled early "
            f"therapy and {aggregation.delayed_therapy} labeled delayed — descriptive "
            "counts only; not a controlled comparison."
        )

    if aggregation.neurologic_outcome_reported < unique_n:
        warnings.append(
            "Neurologic outcomes are incompletely reported; recovery comparisons are limited."
        )

    if aggregation.duplicate_pairs:
        warnings.append(
            f"{len(aggregation.duplicate_pairs)} likely same-patient duplicate pair(s) "
            "were marked; do not double-count those PMIDs as independent patients."
        )

    if aggregation.review_series_table_rows:
        warnings.append(
            f"{len(aggregation.review_series_table_rows)} review/large-series row(s) are "
            "separated from single-case tallies — do not treat large n as one patient."
        )

    warnings.append(
        "Case reports cannot prove that earlier therapy causes better neurologic recovery."
    )

    return warnings
