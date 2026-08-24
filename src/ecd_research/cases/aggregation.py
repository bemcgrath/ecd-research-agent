"""Aggregate validated case records into counts, tables, and gaps."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from ecd_research.cases.dedupe import (
    duplicate_of_map,
    find_likely_duplicate_pairs,
    is_review_or_large_series,
)
from ecd_research.models import CaseRecord, TherapyTiming

_TARGETED_THERAPY_RE = re.compile(
    r"\b(braf|mek|dabrafenib|trametinib|vemurafenib|cobimetinib|encorafenib|binimetinib)\b",
    re.IGNORECASE,
)


class CaseTableRow(BaseModel):
    """One row in the case corpus table."""

    pmid: str
    source_title: str | None = None
    source_url: str
    disease_label: str | None = None
    case_count: int | None = None
    cns_involvement: str
    mutation: str | None = None
    therapies: str | None = None
    symptoms_to_diagnosis: str | None = None
    diagnosis_to_treatment: str | None = None
    therapy_timing: str | None = None
    neurologic_outcome: str | None = None
    row_kind: Literal["case", "review_or_series"] = "case"
    likely_duplicate_of: str | None = None


class CaseAggregationResult(BaseModel):
    """Deterministic summary over validated case records — no invented statistics."""

    research_question: str
    records_analyzed: int
    records_analyzed_unique: int | None = None
    total_patients_reported: int | None = None
    disease_label_counts: dict[str, int] = Field(default_factory=dict)
    cns_involvement_yes: int = 0
    cns_involvement_no: int = 0
    cns_involvement_unknown: int = 0
    mutation_reported: int = 0
    targeted_therapy_reported: int = 0
    timing_reported: int = 0
    early_therapy: int = 0
    delayed_therapy: int = 0
    neurologic_outcome_reported: int = 0
    field_coverage: dict[str, int] = Field(default_factory=dict)
    gaps: list[str] = Field(default_factory=list)
    table_rows: list[CaseTableRow] = Field(default_factory=list)
    case_table_rows: list[CaseTableRow] = Field(default_factory=list)
    review_series_table_rows: list[CaseTableRow] = Field(default_factory=list)
    duplicate_pairs: list[tuple[str, str]] = Field(default_factory=list)
    records: list[CaseRecord] = Field(default_factory=list)


def _has_targeted_therapy(record: CaseRecord) -> bool:
    blob = " ".join(record.therapies)
    return bool(_TARGETED_THERAPY_RE.search(blob))


def _fmt_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "not reported"


def _count_field(records: list[CaseRecord], attr: str) -> int:
    count = 0
    for record in records:
        value = getattr(record, attr)
        if value is None:
            continue
        if isinstance(value, list) and not value:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        count += 1
    return count


def _to_row(
    record: CaseRecord,
    *,
    row_kind: Literal["case", "review_or_series"],
    likely_duplicate_of: str | None,
) -> CaseTableRow:
    return CaseTableRow(
        pmid=record.pmid,
        source_title=record.source_title,
        source_url=record.source_url,
        disease_label=record.disease_label.value if record.disease_label else None,
        case_count=record.case_count,
        cns_involvement=_fmt_bool(record.cns_involvement),
        mutation=record.mutation,
        therapies=", ".join(record.therapies) if record.therapies else None,
        symptoms_to_diagnosis=record.symptoms_to_diagnosis,
        diagnosis_to_treatment=record.diagnosis_to_treatment,
        therapy_timing=(
            record.therapy_timing.value if record.therapy_timing else None
        ),
        neurologic_outcome=record.neurologic_outcome,
        row_kind=row_kind,
        likely_duplicate_of=likely_duplicate_of,
    )


def aggregate_case_records(
    records: list[CaseRecord],
    *,
    research_question: str,
) -> CaseAggregationResult:
    """Summarize validated case records with explicit gaps — never infer missing data."""
    validated = [r for r in records if r.validation_status == "validated"]
    dup_map = duplicate_of_map(validated)
    dup_pairs = find_likely_duplicate_pairs(validated)

    # Unique-patient counts exclude marked secondary duplicates among single cases.
    unique_for_counts = [
        r
        for r in validated
        if r.pmid not in dup_map and not is_review_or_large_series(r)
    ]
    # Fall back to all non-duplicates if everything classified as review.
    count_pool = unique_for_counts or [
        r for r in validated if r.pmid not in dup_map
    ]

    disease_counts: dict[str, int] = {}
    cns_yes = cns_no = cns_unknown = 0
    mutation_count = targeted_count = timing_count = 0
    early_count = delayed_count = 0
    neuro_outcome_count = 0
    patient_total: int | None = 0 if count_pool else None

    for record in count_pool:
        label = record.disease_label.value if record.disease_label else "not reported"
        disease_counts[label] = disease_counts.get(label, 0) + 1

        if record.cns_involvement is True:
            cns_yes += 1
        elif record.cns_involvement is False:
            cns_no += 1
        else:
            cns_unknown += 1

        if record.mutation:
            mutation_count += 1
        if _has_targeted_therapy(record):
            targeted_count += 1

        if record.therapy_timing and record.therapy_timing != TherapyTiming.NOT_REPORTED:
            timing_count += 1
            if record.therapy_timing == TherapyTiming.EARLY:
                early_count += 1
            elif record.therapy_timing == TherapyTiming.DELAYED:
                delayed_count += 1

        if record.neurologic_outcome:
            neuro_outcome_count += 1

        if patient_total is not None:
            if record.case_count is not None:
                patient_total += record.case_count
            else:
                patient_total += 1

    table_rows: list[CaseTableRow] = []
    case_rows: list[CaseTableRow] = []
    review_rows: list[CaseTableRow] = []
    for record in validated:
        kind: Literal["case", "review_or_series"] = (
            "review_or_series" if is_review_or_large_series(record) else "case"
        )
        row = _to_row(
            record,
            row_kind=kind,
            likely_duplicate_of=dup_map.get(record.pmid),
        )
        table_rows.append(row)
        if kind == "review_or_series":
            review_rows.append(row)
        else:
            case_rows.append(row)

    field_coverage = {
        "disease_label": _count_field(count_pool, "disease_label"),
        "mutation": _count_field(count_pool, "mutation"),
        "therapies": sum(1 for r in count_pool if r.therapies),
        "symptoms_to_diagnosis": _count_field(count_pool, "symptoms_to_diagnosis"),
        "diagnosis_to_treatment": _count_field(count_pool, "diagnosis_to_treatment"),
        "therapy_timing": timing_count,
        "neurologic_outcome": neuro_outcome_count,
        "cns_involvement": cns_yes + cns_no,
    }

    gaps: list[str] = []
    if not validated:
        gaps.append("No validated case records were extracted.")
    else:
        n = len(count_pool)
        if field_coverage["therapy_timing"] < n:
            gaps.append(
                f"Therapy timing not reported in {n - field_coverage['therapy_timing']} "
                f"of {n} unique single-case/small-series records (abstract-limited)."
            )
        if field_coverage["neurologic_outcome"] < n:
            gaps.append(
                f"Neurologic outcome not reported in {n - field_coverage['neurologic_outcome']} "
                f"of {n} unique single-case/small-series records."
            )
        if field_coverage["symptoms_to_diagnosis"] < n:
            gaps.append(
                f"Symptoms-to-diagnosis interval not reported in "
                f"{n - field_coverage['symptoms_to_diagnosis']} of {n} unique records."
            )
        if field_coverage["diagnosis_to_treatment"] < n:
            gaps.append(
                f"Diagnosis-to-treatment interval not reported in "
                f"{n - field_coverage['diagnosis_to_treatment']} of {n} unique records."
            )
        if cns_unknown > 0:
            gaps.append(
                f"CNS involvement unclear or not reported in {cns_unknown} of {n} unique records."
            )
        if dup_pairs:
            pair_txt = ", ".join(f"{a}≈{b}" for a, b in dup_pairs)
            gaps.append(
                f"Likely same-patient duplicates marked (not merged): {pair_txt}. "
                "Unique-patient counts exclude secondary rows."
            )
        if review_rows:
            gaps.append(
                f"{len(review_rows)} review/large-series row(s) listed separately; "
                "not mixed into unique single-case timing counts."
            )
        gaps.append(
            "Abstract-only extraction may miss timing and outcome details present only in full text."
        )
        gaps.append(
            "Case reports and small series cannot establish population-level causation."
        )

    return CaseAggregationResult(
        research_question=research_question,
        records_analyzed=len(validated),
        records_analyzed_unique=len(count_pool) if validated else None,
        total_patients_reported=patient_total if validated else None,
        disease_label_counts=disease_counts,
        cns_involvement_yes=cns_yes,
        cns_involvement_no=cns_no,
        cns_involvement_unknown=cns_unknown,
        mutation_reported=mutation_count,
        targeted_therapy_reported=targeted_count,
        timing_reported=timing_count,
        early_therapy=early_count,
        delayed_therapy=delayed_count,
        neurologic_outcome_reported=neuro_outcome_count,
        field_coverage=field_coverage,
        gaps=gaps,
        table_rows=table_rows,
        case_table_rows=case_rows,
        review_series_table_rows=review_rows,
        duplicate_pairs=dup_pairs,
        records=validated,
    )
