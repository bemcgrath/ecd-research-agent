"""LLM-backed structured case extraction from PubMed case reports."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from ecd_research.cases.validator import validate_case_record
from ecd_research.models import (
    CaseRecord,
    DiseaseLabel,
    PubMedArticle,
    TherapyTiming,
)

load_dotenv()

EXTRACTOR_PROMPT_VERSION = "v1"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "case_extraction.md"


class _ExtractedCase(BaseModel):
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
    source_fields_used: list[Literal["title", "abstract"]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class _CaseExtractionPayload(BaseModel):
    records: list[_ExtractedCase] = Field(default_factory=list)


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _article_payload(article: PubMedArticle) -> dict[str, Any]:
    return {
        "pmid": article.pmid,
        "title": article.title,
        "journal": article.journal,
        "publication_date": article.publication_date,
        "abstract": article.abstract,
        "doi": article.doi,
        "pubmed_url": str(article.pubmed_url),
        "authors": article.authors,
    }


def _call_openai(
    *,
    research_question: str,
    article: PubMedArticle,
    model: str,
    client: OpenAI,
) -> _CaseExtractionPayload:
    user_content = json.dumps(
        {
            "research_question": research_question,
            "article": _article_payload(article),
            "instructions": (
                "Extract structured case fields grounded in the supplied article. "
                "Return JSON matching the schema."
            ),
        },
        ensure_ascii=True,
    )
    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _load_system_prompt()},
            {"role": "user", "content": user_content},
        ],
        response_format=_CaseExtractionPayload,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        return _CaseExtractionPayload(records=[])
    return parsed


def _to_case_record(
    extracted: _ExtractedCase,
    article: PubMedArticle,
    *,
    model: str,
) -> CaseRecord:
    return CaseRecord(
        pmid=article.pmid,
        source_title=article.title,
        source_url=str(article.pubmed_url),
        publication_date=article.publication_date,
        journal=article.journal,
        doi=article.doi,
        disease_label=extracted.disease_label,
        case_count=extracted.case_count,
        organ_involvement=extracted.organ_involvement,
        cns_involvement=extracted.cns_involvement,
        mutation=extracted.mutation,
        therapies=extracted.therapies,
        symptoms_to_diagnosis=extracted.symptoms_to_diagnosis,
        diagnosis_to_treatment=extracted.diagnosis_to_treatment,
        therapy_timing=extracted.therapy_timing,
        neurologic_outcome=extracted.neurologic_outcome,
        other_outcomes=extracted.other_outcomes,
        supporting_text=extracted.supporting_text,
        source_fields_used=extracted.source_fields_used,
        limitations=extracted.limitations,
        abstract_limited=True,
        extractor_model=model,
        extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        validation_status="pending",
    )


def extract_case_records(
    article: PubMedArticle,
    research_question: str,
    *,
    model: str | None = None,
    client: OpenAI | None = None,
    validate: bool = True,
) -> list[CaseRecord]:
    """Extract structured case records from one article for a research question."""
    if not isinstance(research_question, str) or not research_question.strip():
        raise ValueError("research_question must be a non-empty string")

    model_name = model or DEFAULT_MODEL
    openai_client = client or OpenAI()
    payload = _call_openai(
        research_question=research_question.strip(),
        article=article,
        model=model_name,
        client=openai_client,
    )

    results: list[CaseRecord] = []
    for extracted in payload.records:
        record = _to_case_record(extracted, article, model=model_name)
        if not validate:
            results.append(record)
            continue
        outcome = validate_case_record(record, article)
        if outcome.ok and outcome.record is not None:
            results.append(outcome.record)
    return results
