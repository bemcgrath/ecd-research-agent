"""Render case corpus aggregation as Markdown."""

from __future__ import annotations

from ecd_research.cases.aggregation import CaseAggregationResult, CaseTableRow


def _render_table(rows: list[CaseTableRow], *, show_duplicate_col: bool) -> list[str]:
    lines: list[str] = []
    header = (
        "| PMID | Disease | n | CNS | Mutation | Therapies | "
        "Sx→Dx | Dx→Rx | Timing | Neuro outcome |"
    )
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    if show_duplicate_col:
        header = header[:-1] + " Likely dup of |"
        sep = sep + " --- |"
    lines.extend([header, sep])
    for row in rows:
        cells = (
            f"| [{row.pmid}]({row.source_url}) | "
            f"{row.disease_label or '—'} | "
            f"{row.case_count if row.case_count is not None else '—'} | "
            f"{row.cns_involvement} | "
            f"{row.mutation or '—'} | "
            f"{row.therapies or '—'} | "
            f"{row.symptoms_to_diagnosis or '—'} | "
            f"{row.diagnosis_to_treatment or '—'} | "
            f"{row.therapy_timing or '—'} | "
            f"{row.neurologic_outcome or '—'} |"
        )
        if show_duplicate_col:
            cells = cells[:-1] + f" {row.likely_duplicate_of or '—'} |"
        lines.append(cells)
    lines.append("")
    return lines


def render_case_corpus_markdown(
    aggregation: CaseAggregationResult,
    *,
    warnings: list[str] | None = None,
    notes: list[str] | None = None,
) -> str:
    """Render a citation-bound case corpus report."""
    unique_n = aggregation.records_analyzed_unique
    lines: list[str] = [
        "# Case Corpus Report",
        "",
        "> Research aid only — not medical advice. Do not use for treatment decisions.",
        "",
        "## Research question",
        "",
        aggregation.research_question,
        "",
        "## Summary",
        "",
        f"- Validated case records: **{aggregation.records_analyzed}**",
    ]
    if unique_n is not None and unique_n != aggregation.records_analyzed:
        lines.append(
            f"- Unique single-case / small-series (excl. marked duplicates & reviews): "
            f"**{unique_n}**"
        )

    if aggregation.total_patients_reported is not None:
        lines.append(
            f"- Total patients in unique single-case/small-series rows (when stated): "
            f"**{aggregation.total_patients_reported}**"
        )

    lines.extend(
        [
            f"- CNS involvement (yes / no / not reported): "
            f"**{aggregation.cns_involvement_yes}** / "
            f"**{aggregation.cns_involvement_no}** / "
            f"**{aggregation.cns_involvement_unknown}**",
            f"- Mutation reported: **{aggregation.mutation_reported}**",
            f"- Targeted BRAF/MEK therapy reported: **{aggregation.targeted_therapy_reported}**",
            f"- Therapy timing reported: **{aggregation.timing_reported}** "
            f"(early: {aggregation.early_therapy}, delayed: {aggregation.delayed_therapy})",
            f"- Neurologic outcome reported: **{aggregation.neurologic_outcome_reported}**",
            f"- Abstract-limited records: "
            f"**{sum(1 for r in aggregation.records if r.abstract_limited)}** / "
            f"**{aggregation.records_analyzed}**",
            "",
        ]
    )

    if aggregation.duplicate_pairs:
        lines.append("### Likely same-patient duplicates")
        lines.append("")
        lines.append(
            "Marked only — rows are kept; unique-patient counts exclude the secondary PMID."
        )
        lines.append("")
        for kept, dup in aggregation.duplicate_pairs:
            lines.append(f"- {dup} likely same patient as {kept}")
        lines.append("")

    if aggregation.disease_label_counts:
        lines.append("### Disease labels (unique single-case / small-series)")
        lines.append("")
        for label, count in sorted(aggregation.disease_label_counts.items()):
            lines.append(f"- {label}: {count}")
        lines.append("")

    case_rows = aggregation.case_table_rows or [
        r for r in aggregation.table_rows if r.row_kind == "case"
    ]
    review_rows = aggregation.review_series_table_rows or [
        r for r in aggregation.table_rows if r.row_kind == "review_or_series"
    ]
    show_dup = any(r.likely_duplicate_of for r in case_rows)

    if case_rows:
        lines.extend(["## Single-case / small-series table", ""])
        lines.extend(_render_table(case_rows, show_duplicate_col=show_dup))

    if review_rows:
        lines.extend(
            [
                "## Reviews / large series",
                "",
                "Large-n or review-style rows are listed separately so they are not "
                "counted as individual patients in the summary timing tallies.",
                "",
            ]
        )
        lines.extend(_render_table(review_rows, show_duplicate_col=False))

    if not case_rows and not review_rows and aggregation.table_rows:
        lines.extend(["## Case table", ""])
        lines.extend(
            _render_table(
                aggregation.table_rows,
                show_duplicate_col=any(
                    r.likely_duplicate_of for r in aggregation.table_rows
                ),
            )
        )

    if warnings:
        lines.extend(["## Critic warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if aggregation.gaps:
        lines.extend(["## Evidence gaps", ""])
        for gap in aggregation.gaps:
            lines.append(f"- {gap}")
        lines.append("")

    if notes:
        lines.extend(["## Run notes", ""])
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    if aggregation.records:
        lines.extend(["## Sources", ""])
        seen: set[str] = set()
        for record in aggregation.records:
            if record.pmid in seen:
                continue
            seen.add(record.pmid)
            title = record.source_title or "(title not available)"
            lines.append(f"- [{record.pmid}]({record.source_url}) — {title}")
        lines.append("")

    return "\n".join(lines)
