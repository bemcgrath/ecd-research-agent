"""Shared data models for ECD research tools."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class PubMedArticle(BaseModel):
    """A PubMed article with metadata taken only from NCBI responses."""

    pmid: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_date: str | None = None
    abstract: str | None = None
    doi: str | None = None
    pubmed_url: HttpUrl


class StudyType(str, Enum):
    """Study design labels; never invent a design not supported by the source."""

    PROSPECTIVE_CONTROLLED_TRIAL = "prospective_controlled_trial"
    PROSPECTIVE_SINGLE_ARM_TRIAL = "prospective_single_arm_trial"
    RETROSPECTIVE_COHORT = "retrospective_cohort"
    CASE_SERIES = "case_series"
    CASE_REPORT = "case_report"
    SYSTEMATIC_REVIEW = "systematic_review"
    SCOPING_REVIEW = "scoping_review"
    CONSENSUS_STATEMENT = "consensus_statement"
    EXPERT_OPINION = "expert_opinion"
    PREPRINT = "preprint"
    CONFERENCE_ABSTRACT = "conference_abstract"
    ANIMAL_STUDY = "animal_study"
    IN_VITRO_STUDY = "in_vitro_study"
    OTHER = "other"
    UNKNOWN = "unknown"


class EvidenceStrength(str, Enum):
    """User-facing categorical strength (not a validated clinical grade)."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"
    INSUFFICIENT = "insufficient"


class EvidenceRecord(BaseModel):
    """Atomic claim grounded in a single retrieved source article."""

    claim: str

    pmid: str
    source_title: str | None = None
    source_url: str
    publication_date: str | None = None
    journal: str | None = None
    doi: str | None = None

    study_type: StudyType | None = None
    sample_size: int | None = None
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str | None = None

    supporting_text: str
    supporting_text_start: int | None = None
    supporting_text_end: int | None = None
    source_fields_used: list[Literal["title", "abstract"]] = Field(default_factory=list)

    limitations: list[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    reasoning_note: str

    abstract_limited: bool = True
    extractor_model: str
    extractor_prompt_version: str
    validation_status: Literal["pending", "validated", "rejected"] = "pending"


class ValidationResult(BaseModel):
    """Outcome of provenance validation for one EvidenceRecord."""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    record: EvidenceRecord | None = None


class DiseaseLabel(str, Enum):
    """Disease context as reported in source (never inferred beyond text)."""

    ECD = "ecd"
    LCH = "lch"
    MIXED = "mixed"
    HISTIOCYTOSIS_UNSPECIFIED = "histiocytosis_unspecified"
    UNKNOWN = "unknown"


class TherapyTiming(str, Enum):
    """Timing of targeted therapy relative to diagnosis/symptoms, when source supports."""

    EARLY = "early"
    DELAYED = "delayed"
    NOT_REPORTED = "not_reported"
    UNCLEAR = "unclear"


class FullTextSection(BaseModel):
    """One section of a full-text article with provenance retained."""

    title: str | None = None
    text: str
    section_type: str | None = None  # e.g. body / abstract / back


class FullTextDocument(BaseModel):
    """Open-access full text retrieved from PubMed Central (or compatible source)."""

    pmid: str
    pmcid: str
    title: str | None = None
    doi: str | None = None
    source_url: str
    sections: list[FullTextSection] = Field(default_factory=list)
    raw_text: str = ""
    abstract_limited: bool = False


class CaseRecord(BaseModel):
    """Structured fields from a case report or small case series."""

    pmid: str
    source_title: str | None = None
    source_url: str
    publication_date: str | None = None
    journal: str | None = None
    doi: str | None = None

    disease_label: DiseaseLabel | None = None
    case_count: int | None = None
    organ_involvement: list[str] = Field(default_factory=list)
    cns_involvement: bool | None = None

    mutation: str | None = None
    therapies: list[str] = Field(default_factory=list)

    symptoms_to_diagnosis: str | None = None
    diagnosis_to_treatment: str | None = None
    therapy_timing: TherapyTiming | None = None

    neurologic_outcome: str | None = None
    other_outcomes: str | None = None

    supporting_text: str
    source_fields_used: list[Literal["title", "abstract", "full_text"]] = Field(
        default_factory=list
    )
    limitations: list[str] = Field(default_factory=list)

    abstract_limited: bool = True
    extractor_model: str
    extractor_prompt_version: str
    validation_status: Literal["pending", "validated", "rejected"] = "pending"
    pmcid: str | None = None


class CaseValidationResult(BaseModel):
    """Outcome of provenance validation for one CaseRecord."""

    ok: bool
    errors: list[str] = Field(default_factory=list)
    record: CaseRecord | None = None


class ClinicalTrial(BaseModel):
    """A ClinicalTrials.gov study record (API v2 fields only; never inferred)."""

    nct_id: str
    title: str | None = None
    status: str | None = None
    phase: str | None = None
    interventions: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    eligibility: str | None = None
    minimum_age: str | None = None
    maximum_age: str | None = None
    locations: list[str] = Field(default_factory=list)
    sponsor: str | None = None
    investigators: list[str] = Field(default_factory=list)
    start_date: str | None = None
    completion_date: str | None = None
    last_update_date: str | None = None
    url: str
