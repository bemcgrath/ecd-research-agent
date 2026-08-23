"""Persistence helpers for articles, evidence, and research-run audit."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from ecd_research.models import (
    EvidenceRecord,
    EvidenceStrength,
    PubMedArticle,
    StudyType,
)
from ecd_research.storage.database import connect


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _json_list(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=True)


def _load_json_list(raw: str | None) -> list[Any]:
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        return []
    return data


class EvidenceRepository:
    """SQLite-backed store for PubMed articles and validated evidence."""

    def __init__(self, db_path: str | None = None, conn: sqlite3.Connection | None = None):
        if conn is not None:
            self.conn = conn
            self._owns_conn = False
        else:
            self.conn = connect(db_path)
            self._owns_conn = True

    def close(self) -> None:
        if self._owns_conn:
            self.conn.close()

    def __enter__(self) -> EvidenceRepository:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def upsert_article(self, article: PubMedArticle) -> None:
        now = _utcnow()
        self.conn.execute(
            """
            INSERT INTO articles (
                pmid, title, authors_json, journal, publication_date,
                abstract, doi, pubmed_url, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pmid) DO UPDATE SET
                title=excluded.title,
                authors_json=excluded.authors_json,
                journal=excluded.journal,
                publication_date=excluded.publication_date,
                abstract=excluded.abstract,
                doi=excluded.doi,
                pubmed_url=excluded.pubmed_url,
                retrieved_at=excluded.retrieved_at
            """,
            (
                article.pmid,
                article.title,
                _json_list(article.authors),
                article.journal,
                article.publication_date,
                article.abstract,
                article.doi,
                str(article.pubmed_url),
                now,
            ),
        )
        self.conn.commit()

    def get_article(self, pmid: str) -> PubMedArticle | None:
        row = self.conn.execute(
            "SELECT * FROM articles WHERE pmid = ?", (pmid,)
        ).fetchone()
        if row is None:
            return None
        return PubMedArticle(
            pmid=row["pmid"],
            title=row["title"],
            authors=_load_json_list(row["authors_json"]),
            journal=row["journal"],
            publication_date=row["publication_date"],
            abstract=row["abstract"],
            doi=row["doi"],
            pubmed_url=row["pubmed_url"],
        )

    def get_or_create_question(self, question: str) -> int:
        cleaned = question.strip()
        if not cleaned:
            raise ValueError("question must be a non-empty string")
        row = self.conn.execute(
            "SELECT id FROM research_questions WHERE question = ?", (cleaned,)
        ).fetchone()
        if row is not None:
            return int(row["id"])
        cur = self.conn.execute(
            "INSERT INTO research_questions(question, created_at) VALUES (?, ?)",
            (cleaned, _utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def start_search_run(
        self,
        question_id: int,
        *,
        extractor_model: str | None = None,
        extractor_prompt_version: str | None = None,
        notes: str | None = None,
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO search_runs (
                question_id, started_at, extractor_model,
                extractor_prompt_version, notes
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (question_id, _utcnow(), extractor_model, extractor_prompt_version, notes),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_search_run(self, run_id: int) -> None:
        self.conn.execute(
            "UPDATE search_runs SET finished_at = ? WHERE id = ?",
            (_utcnow(), run_id),
        )
        self.conn.commit()

    def add_search_query(
        self,
        run_id: int,
        query: str,
        *,
        source: str,
        pmids: list[str],
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO search_queries(run_id, query, source, pmids_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, query, source, _json_list(pmids), _utcnow()),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def save_evidence_record(
        self,
        record: EvidenceRecord,
        *,
        question_id: int | None = None,
        run_id: int | None = None,
    ) -> int:
        if record.validation_status != "validated":
            raise ValueError(
                "only validated evidence records may be stored "
                f"(got {record.validation_status!r})"
            )
        now = _utcnow()
        cur = self.conn.execute(
            """
            INSERT INTO evidence_records (
                claim, pmid, question_id, run_id, source_title, source_url,
                publication_date, journal, doi, study_type, sample_size,
                population, intervention, comparator, outcome,
                supporting_text, supporting_text_start, supporting_text_end,
                source_fields_used_json, limitations_json, evidence_strength,
                reasoning_note, abstract_limited, extractor_model,
                extractor_prompt_version, validation_status, created_at, validated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                record.claim,
                record.pmid,
                question_id,
                run_id,
                record.source_title,
                record.source_url,
                record.publication_date,
                record.journal,
                record.doi,
                record.study_type.value if record.study_type else None,
                record.sample_size,
                record.population,
                record.intervention,
                record.comparator,
                record.outcome,
                record.supporting_text,
                record.supporting_text_start,
                record.supporting_text_end,
                _json_list(list(record.source_fields_used)),
                _json_list(record.limitations),
                record.evidence_strength.value,
                record.reasoning_note,
                1 if record.abstract_limited else 0,
                record.extractor_model,
                record.extractor_prompt_version,
                record.validation_status,
                now,
                now,
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def list_evidence_for_pmid(self, pmid: str) -> list[EvidenceRecord]:
        rows = self.conn.execute(
            "SELECT * FROM evidence_records WHERE pmid = ? ORDER BY id",
            (pmid,),
        ).fetchall()
        return [self._row_to_evidence(row) for row in rows]

    def list_evidence_for_question(self, question_id: int) -> list[EvidenceRecord]:
        rows = self.conn.execute(
            "SELECT * FROM evidence_records WHERE question_id = ? ORDER BY id",
            (question_id,),
        ).fetchall()
        return [self._row_to_evidence(row) for row in rows]

    def count_evidence(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) AS n FROM evidence_records").fetchone()
        return int(row["n"]) if row else 0

    @staticmethod
    def _row_to_evidence(row: sqlite3.Row) -> EvidenceRecord:
        study_raw = row["study_type"]
        study_type = StudyType(study_raw) if study_raw else None
        fields = _load_json_list(row["source_fields_used_json"])
        return EvidenceRecord(
            claim=row["claim"],
            pmid=row["pmid"],
            source_title=row["source_title"],
            source_url=row["source_url"],
            publication_date=row["publication_date"],
            journal=row["journal"],
            doi=row["doi"],
            study_type=study_type,
            sample_size=row["sample_size"],
            population=row["population"],
            intervention=row["intervention"],
            comparator=row["comparator"],
            outcome=row["outcome"],
            supporting_text=row["supporting_text"],
            supporting_text_start=row["supporting_text_start"],
            supporting_text_end=row["supporting_text_end"],
            source_fields_used=fields,  # type: ignore[arg-type]
            limitations=_load_json_list(row["limitations_json"]),
            evidence_strength=EvidenceStrength(row["evidence_strength"]),
            reasoning_note=row["reasoning_note"],
            abstract_limited=bool(row["abstract_limited"]),
            extractor_model=row["extractor_model"],
            extractor_prompt_version=row["extractor_prompt_version"],
            validation_status=row["validation_status"],
        )
