# ECD Research Agent — Master Implementation Plan

## Status Snapshot

| Milestone | Status | Notes |
| --- | --- | --- |
| M1 PubMed foundation | **Done** (merged to `main`) | Live E-utilities search/fetch; nullable metadata; field name `pubmed_url` |
| M1.1 Date-range search | **Done** (this branch) | `search_pubmed_by_date` via NCBI mindate/maxdate |
| M2 Atomic evidence extraction | **Done** | `EvidenceRecord`, extract, provenance validator, adversarial tests |
| M3 Evidence repository (SQLite) | **Done** | Persist articles, evidence, research questions/runs |
| M4 Search strategy + ECD vocabulary | **Done** (this branch) | Config-driven YAML synonyms + PubMed query expansion |
| M5 ClinicalTrials.gov | **Done** | Official API v2 search/fetch; no inferred status |
| M6 Research loop | **Done** | Quick=1 round, Deep=2 rounds + trials + optional extract/save |
| M7 Evidence critic | **Done** (this branch) | Deterministic critic labels before synthesis |
| M8 Synthesis + CLI report | **Done** (this branch) | Markdown report from critiqued EvidenceRecords |
| M9+ | Deferred | Full-text, citation graph, UI, monitoring, KG after F |

## Mission

Build an open-source AI research system for **Erdheim-Chester disease (ECD)** that systematically discovers, evaluates, connects, updates, and cites medical evidence.

The system should behave like a rigorous research analyst, not a generic medical chatbot.

Core design principle:

> The agent's job is not to "know" ECD. Its job is to reliably discover, verify, organize, and synthesize evidence about ECD.

See also [MISSION.md](MISSION.md).

## Architecture (North Star)

```text
USER QUESTION
      |
      v
Research Director
      |
      +-- Literature Researcher
      +-- Trials Researcher
      +-- Other sources
      |
      v
Evidence Extraction → Evidence Repository → Evidence Critic → Synthesis
      |
      v
REPORT + SOURCES + GAPS
```

Implement in validated vertical slices. Do not build the full tree empty.

## Technology Direction

**Now:** Python 3.12+, Pydantic, requests, python-dotenv, pytest, OpenAI Python SDK, SQLite, GitHub.

**Later:** PostgreSQL/pgvector, full-text PDF ingestion, Agents SDK, Streamlit, scheduled monitoring.

Do not start with Neo4j.

## Milestone 1 — PubMed Foundation (Done)

Implemented:

- `search_pubmed(query, max_results=20) -> list[str]`
- `get_pubmed_articles(pmids) -> list[PubMedArticle]`
- `PubMedArticle` with: `pmid`, `title`, `authors`, `journal`, `publication_date`, `abstract`, `doi`, `pubmed_url`

Notes reconciled with the original draft:

- Field is named **`pubmed_url`** (canonical `https://pubmed.ncbi.nlm.nih.gov/{pmid}/`), not `url`.
- Metadata fields that NCBI may omit are **`Optional` / nullable**; missing stays missing.
- Source of truth: **NCBI E-utilities only**.

## Milestone 1.1 — Date-Range Search

```python
search_pubmed_by_date(query, start_date, end_date, max_results=100) -> list[str]
```

Uses E-utilities date filters; does not invent publication dates locally.

## Milestone 2 — Atomic Evidence Extraction

Primary stored object is an **evidence record**, not a paper summary.

```python
extract_evidence(article: PubMedArticle, research_question: str) -> list[EvidenceRecord]
validate_evidence_record(record, source_article) -> ValidationResult
```

Evidence boundary: research question + article metadata + title + abstract + DOI + URL only.

No record enters trusted output without provenance validation (PMID/title/DOI/URL match; supporting text present in supplied source after normalization).

Early outputs are **abstract-limited** until full-text ingestion exists.

## Milestones 3–8 (Summary)

- **M3:** SQLite for articles, evidence, research questions/runs (audit from day one of persistence).
- **M4:** Query expansion + configurable ECD vocabulary YAML.
- **M5:** ClinicalTrials.gov API v2 (never infer trial status).
- **M6:** Iterative research loop (Deep ≥ 2 rounds; Exhaustive stops on diminishing returns).
- **M7:** Critic (`SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED` / `CONTRADICTED`).
- **M8:** Synthesis from validated records only; specialist questions section; clinical disclaimers.

Then **stop and evaluate** on the neurological ECD + molecular status benchmark before M9+.

## Deferred (After Milestone F)

Full-text PMC/PDF, citation network, researcher/institution mapping, knowledge graph, time-aware supersession, patient-context matching (local-only privacy), continuous monitoring, Streamlit UI.

## Clinical Boundary

May: summarize evidence, compare studies, identify specialist questions, identify trials, explain molecular findings as reported in sources, match literature to a structured profile.

Must not: diagnose, prescribe, instruct treatment changes, present inference as clinical recommendation, or delay urgent care.

## Testing

- Unit tests for parsing and provenance (fail closed).
- Adversarial tests: no universal efficacy from case reports; no inventing mutations; no mislabeling reviews as trials.
- Live network tests separated from deterministic unit tests.

## Open Source Guardrails

Never commit patient records, API keys, private medical information, or licensed PDFs without redistribution rights.
