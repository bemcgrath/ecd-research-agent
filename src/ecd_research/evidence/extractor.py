"""LLM-backed atomic evidence extraction from PubMed articles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from ecd_research.evidence.validator import validate_evidence_record
from ecd_research.models import (
    EvidenceRecord,
    EvidenceStrength,
    PubMedArticle,
    StudyType,
)

load_dotenv()

EXTRACTOR_PROMPT_VERSION = "v1"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
PROMPT_PATH = (
    Path(__file__).resolve().parent.parent / "prompts" / "evidence_extraction.md"
)


class _ExtractedClaim(BaseModel):
    claim: str
    study_type: StudyType | None = None
    sample_size: int | None = None
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    outcome: str | None = None
    supporting_text: str
    source_fields_used: list[Literal["title", "abstract"]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_strength: EvidenceStrength
    reasoning_note: str


class _ExtractionPayload(BaseModel):
    records: list[_ExtractedClaim] = Field(default_factory=list)


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
) -> _ExtractionPayload:
    user_content = json.dumps(
        {
            "research_question": research_question,
            "article": _article_payload(article),
            "instructions": (
                "Extract only claims grounded in the supplied article fields. "
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
        response_format=_ExtractionPayload,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        return _ExtractionPayload(records=[])
    return parsed


def _to_evidence_record(
    claim: _ExtractedClaim,
    article: PubMedArticle,
    *,
    model: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        claim=claim.claim,
        pmid=article.pmid,
        source_title=article.title,
        source_url=str(article.pubmed_url),
        publication_date=article.publication_date,
        journal=article.journal,
        doi=article.doi,
        study_type=claim.study_type,
        sample_size=claim.sample_size,
        population=claim.population,
        intervention=claim.intervention,
        comparator=claim.comparator,
        outcome=claim.outcome,
        supporting_text=claim.supporting_text,
        source_fields_used=claim.source_fields_used,
        limitations=claim.limitations,
        evidence_strength=claim.evidence_strength,
        reasoning_note=claim.reasoning_note,
        abstract_limited=True,
        extractor_model=model,
        extractor_prompt_version=EXTRACTOR_PROMPT_VERSION,
        validation_status="pending",
    )


def extract_evidence(
    article: PubMedArticle,
    research_question: str,
    *,
    model: str | None = None,
    client: OpenAI | None = None,
    validate: bool = True,
) -> list[EvidenceRecord]:
    """Extract atomic evidence claims from one article for a research question.

    Only validated records are returned when ``validate`` is True (default).
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
    )

    results: list[EvidenceRecord] = []
    for claim in payload.records:
        record = _to_evidence_record(claim, article, model=model_name)
        if not validate:
            results.append(record)
            continue
        outcome = validate_evidence_record(record, article)
        if outcome.ok and outcome.record is not None:
            results.append(outcome.record)
    return results
