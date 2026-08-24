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
    FullTextDocument,
    PubMedArticle,
    TherapyTiming,
)
from ecd_research.tools.pmc import build_fulltext_corpus

load_dotenv()

EXTRACTOR_PROMPT_VERSION = "v2"
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
    source_fields_used: list[Literal["title", "abstract", "full_text"]] = Field(
        default_factory=list
    )
    limitations: list[str] = Field(default_factory=list)


class _CaseExtractionPayload(BaseModel):
    records: list[_ExtractedCase] = Field(default_factory=list)


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _article_payload(
    article: PubMedArticle,
    full_text: FullTextDocument | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pmid": article.pmid,
        "title": article.title,
        "journal": article.journal,
        "publication_date": article.publication_date,
        "abstract": article.abstract,
        "doi": article.doi,
        "pubmed_url": str(article.pubmed_url),
        "authors": article.authors,
    }
    if full_text is not None:
        payload["pmcid"] = full_text.pmcid
        payload["full_text_url"] = full_text.source_url
        payload["full_text"] = build_fulltext_corpus(full_text)
        payload["source_mode"] = "full_text"
    else:
        payload["source_mode"] = "abstract_only"
    return payload


def _call_openai(
    *,
    research_question: str,
    article: PubMedArticle,
    model: str,
    client: OpenAI,
    full_text: FullTextDocument | None = None,
) -> _CaseExtractionPayload:
    user_content = json.dumps(
        {
            "research_question": research_question,
            "article": _article_payload(article, full_text),
            "instructions": (
                "Extract structured case fields grounded only in the supplied source. "
                "When full_text is present, use it for timing and outcome detail. "
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
    full_text: FullTextDocument | None = None,
) -> CaseRecord:
    fields = list(extracted.source_fields_used)
    if full_text is not None and "full_text" not in fields:
        fields.append("full_text")

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
        source_fields_used=fields,  # type: ignore[arg-type]
        limitations=extracted.limitations,
        abstract_limited=full_text is None,
        extractor_model=model,
        extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        validation_status="pending",
        pmcid=full_text.pmcid if full_text else None,
    )


def extract_case_records(
    article: PubMedArticle,
    research_question: str,
    *,
    model: str | None = None,
    client: OpenAI | None = None,
    validate: bool = True,
    full_text: FullTextDocument | None = None,
) -> list[CaseRecord]:
    """Extract structured case records from one article for a research question.

    When ``full_text`` is provided, extraction and provenance use the full text corpus.
    """
    if not isinstance(research_question, str) or not research_question.strip():
        raise ValueError("research_question must be a non-empty string")

    model_name = model or DEFAULT_MODEL
    openai_client = client or OpenAI()
    payload = _call_openai(
        research_question=research_question.strip(),
        article=article,
        model=model_name,
        client=openai_client,
        full_text=full_text,
    )

    results: list[CaseRecord] = []
    for extracted in payload.records:
        record = _to_case_record(
            extracted, article, model=model_name, full_text=full_text
        )
        if not validate:
            results.append(record)
            continue
        outcome = validate_case_record(record, article, full_text=full_text)
        if outcome.ok and outcome.record is not None:
            results.append(outcome.record)
    return results
