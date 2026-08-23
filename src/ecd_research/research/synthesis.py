"""Research synthesis from critiqued EvidenceRecords (no invented claims)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from ecd_research.models import ClinicalTrial, EvidenceRecord, EvidenceStrength
from ecd_research.research.critic import CritiqueLabel, CritiqueResult


DISCLAIMER = (
    "Research aid only. Not a diagnosis or treatment recommendation. "
    "Do not start, stop, or change therapy based on this report. "
    "Discuss findings with an ECD specialist. Seek urgent care for urgent symptoms."
)


class ReportSection(BaseModel):
    title: str
    body: str
    evidence_pmids: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    question: str
    generated_at: str
    disclaimer: str = DISCLAIMER
    bottom_line: str
    sections: list[ReportSection] = Field(default_factory=list)
    specialist_questions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    critique_summary: dict[str, int] = Field(default_factory=dict)


def _strength_rank(strength: EvidenceStrength) -> int:
    order = {
        EvidenceStrength.HIGH: 4,
        EvidenceStrength.MODERATE: 3,
        EvidenceStrength.LOW: 2,
        EvidenceStrength.VERY_LOW: 1,
        EvidenceStrength.INSUFFICIENT: 0,
    }
    return order.get(strength, 0)


def _format_claim(result: CritiqueResult) -> str:
    record = result.record
    study = record.study_type.value if record.study_type else "unknown_study_type"
    bits = [
        f"- [{result.label.value}] {record.claim}",
        f"  PMID {record.pmid}; strength={record.evidence_strength.value}; study={study}",
        f"  Source: {record.source_url}",
    ]
    if record.abstract_limited:
        bits.append("  Note: abstract-limited extraction.")
    if result.findings:
        codes = ", ".join(sorted({f.code for f in result.findings}))
        bits.append(f"  Critic flags: {codes}")
    return "\n".join(bits)


def synthesize_report(
    question: str,
    critiques: list[CritiqueResult],
    *,
    trials: list[ClinicalTrial] | None = None,
) -> ResearchReport:
    """Build a structured report only from provided critiqued evidence."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    trials = trials or []
    summary = {label.value: 0 for label in CritiqueLabel}
    for item in critiques:
        summary[item.label.value] = summary.get(item.label.value, 0) + 1

    usable = [
        c
        for c in critiques
        if c.label
        in {
            CritiqueLabel.SUPPORTED,
            CritiqueLabel.PARTIALLY_SUPPORTED,
            CritiqueLabel.CONTRADICTED,
        }
    ]
    unsupported = [c for c in critiques if c.label == CritiqueLabel.UNSUPPORTED]
    contradicted = [c for c in critiques if c.label == CritiqueLabel.CONTRADICTED]

    established = sorted(
        [
            c
            for c in usable
            if c.record.evidence_strength
            in {EvidenceStrength.HIGH, EvidenceStrength.MODERATE}
            and c.label != CritiqueLabel.CONTRADICTED
        ],
        key=lambda c: _strength_rank(c.record.evidence_strength),
        reverse=True,
    )
    emerging = [
        c
        for c in usable
        if c.record.evidence_strength
        in {EvidenceStrength.LOW, EvidenceStrength.VERY_LOW, EvidenceStrength.INSUFFICIENT}
        or c.label == CritiqueLabel.PARTIALLY_SUPPORTED
    ]

    molecular = [
        c
        for c in usable
        if any(
            tok in (c.record.claim + " " + (c.record.population or "")).lower()
            for tok in ("braf", "mek", "mapk", "map2k1", "kras", "mutation")
        )
    ]
    treatment = [c for c in usable if c.record.intervention]

    if not critiques:
        bottom = (
            "No validated evidence records were available for synthesis. "
            "This does not mean no literature exists — only that none was extracted/validated in this run."
        )
    else:
        bottom = (
            f"Synthesized {len(usable)} usable claim(s) "
            f"({summary.get('SUPPORTED', 0)} supported, "
            f"{summary.get('PARTIALLY_SUPPORTED', 0)} partial, "
            f"{summary.get('CONTRADICTED', 0)} contradicted); "
            f"{summary.get('UNSUPPORTED', 0)} unsupported claim(s) excluded. "
            "All claims remain source-bound and may be abstract-limited."
        )

    def section(title: str, items: list[CritiqueResult], empty: str) -> ReportSection:
        if not items:
            return ReportSection(title=title, body=empty, evidence_pmids=[])
        body = "\n\n".join(_format_claim(c) for c in items)
        return ReportSection(
            title=title,
            body=body,
            evidence_pmids=sorted({c.record.pmid for c in items}),
        )

    sections = [
        section(
            "ESTABLISHED EVIDENCE",
            established,
            "No moderate/high-strength non-contradicted claims in this run.",
        ),
        section(
            "EMERGING EVIDENCE",
            emerging,
            "No low/very-low or partial claims in this run.",
        ),
        section(
            "MOLECULAR FINDINGS",
            molecular,
            "No molecular-focused claims extracted in this run.",
        ),
        section(
            "TREATMENT EVIDENCE",
            treatment,
            "No intervention-linked claims extracted in this run.",
        ),
        section(
            "CONFLICTING EVIDENCE",
            contradicted,
            "No explicit contradictions flagged among extracted claims.",
        ),
    ]

    if unsupported:
        sections.append(
            section(
                "UNSUPPORTED / EXCLUDED CLAIMS",
                unsupported,
                "",
            )
        )

    trial_lines: list[str] = []
    for trial in trials:
        trial_lines.append(
            f"- {trial.nct_id}: {trial.title or '(title not available)'} "
            f"| status={trial.status or 'not available'} | {trial.url}"
        )
    sections.append(
        ReportSection(
            title="CLINICAL TRIALS",
            body="\n".join(trial_lines)
            if trial_lines
            else "No ClinicalTrials.gov records included in this run.",
            evidence_pmids=[],
        )
    )

    sections.append(
        ReportSection(
            title="LIMITATIONS OF THE EVIDENCE",
            body=(
                "- Synthesis uses only validated EvidenceRecords from this run.\n"
                "- Early pipeline evidence is often abstract-limited.\n"
                "- Case reports are informative in rare disease but are not broad efficacy proof.\n"
                "- Missing fields were not inferred."
            ),
        )
    )
    sections.append(
        ReportSection(
            title="RESEARCH GAPS",
            body=(
                "- Gaps listed only when observable from this run's corpus.\n"
                f"- Unsupported excluded claims: {len(unsupported)}.\n"
                f"- Usable claims available: {len(usable)}.\n"
                "- Full-text review, larger cohorts, and prospective data may still be needed."
            ),
        )
    )

    specialist_questions = [
        "Which of these cited studies are most relevant to this specific clinical context?",
        "Do any abstract-limited claims change after full-text review?",
        "How should case-report findings be weighed relative to any available trials or series?",
        "Are there molecularly matched options or trials not captured in this run?",
    ]

    sources = sorted(
        {
            f"PMID {c.record.pmid}: {c.record.source_url}"
            for c in critiques
            if c.label != CritiqueLabel.UNSUPPORTED
        }
        | {f"{t.nct_id}: {t.url}" for t in trials}
    )

    return ResearchReport(
        question=question.strip(),
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        bottom_line=bottom,
        sections=sections,
        specialist_questions=specialist_questions,
        sources=sources,
        critique_summary=summary,
    )


def render_report_markdown(report: ResearchReport) -> str:
    """Render a ResearchReport to markdown text."""
    lines = [
        "# ECD Research Report",
        "",
        f"**Generated:** {report.generated_at}",
        "",
        f"**Disclaimer:** {report.disclaimer}",
        "",
        "## RESEARCH QUESTION",
        "",
        report.question,
        "",
        "## BOTTOM LINE",
        "",
        report.bottom_line,
        "",
    ]
    for section in report.sections:
        lines.extend([f"## {section.title}", "", section.body, ""])

    lines.extend(["## QUESTIONS FOR AN ECD SPECIALIST", ""])
    for q in report.specialist_questions:
        lines.append(f"- {q}")
    lines.extend(["", "## SOURCES", ""])
    if report.sources:
        for src in report.sources:
            lines.append(f"- {src}")
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)
