"""Render case corpus aggregation as Markdown."""

from __future__ import annotations

from ecd_research.cases.aggregation import CaseAggregationResult


def render_case_corpus_markdown(
    aggregation: CaseAggregationResult,
    *,
    warnings: list[str] | None = None,
    notes: list[str] | None = None,
) -> str:
    """Render a citation-bound case corpus report."""
    lines: list[str] = [
        "# Case Corpus Report",
        "",
        "> Research aid only — not medical advice. Do not use for treatment decisions.",
        "",
        f"## Research question",
        "",
        aggregation.research_question,
        "",
        "## Summary",
        "",
        f"- Validated case records: **{aggregation.records_analyzed}**",
    ]

    if aggregation.total_patients_reported is not None:
        lines.append(
            f"- Total patients reported (when stated): **{aggregation.total_patients_reported}**"
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
            "",
        ]
    )

    if aggregation.disease_label_counts:
        lines.append("### Disease labels")
        lines.append("")
        for label, count in sorted(aggregation.disease_label_counts.items()):
            lines.append(f"- {label}: {count}")
        lines.append("")

    if aggregation.table_rows:
        lines.extend(["## Case table", ""])
        lines.append(
            "| PMID | Disease | n | CNS | Mutation | Therapies | "
            "Sx→Dx | Dx→Rx | Timing | Neuro outcome |"
        )
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for row in aggregation.table_rows:
            lines.append(
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
        lines.append("")

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
