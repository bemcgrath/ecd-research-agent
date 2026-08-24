# ECD Research Agent — Roadmap

This document is the north-star roadmap. **Milestones 1–8 and A–F are complete.** **M9 (case aggregation) is next.** Milestones 10–18 carry the original long-term vision with full detail.

See also [MISSION.md](MISSION.md), [USER_GUIDE.md](USER_GUIDE.md), and [GLOSSARY.md](GLOSSARY.md).

---

## Status Snapshot

### Core milestones (M1–M18)

| Milestone | Status | Notes |
| --- | --- | --- |
| M1 PubMed foundation | **Done** | Live E-utilities search/fetch; nullable metadata; field `pubmed_url` |
| M1.1 Date-range search | **Done** | `search_pubmed_by_date` via NCBI mindate/maxdate |
| M2 Atomic evidence extraction | **Done** | `EvidenceRecord`, extract, provenance validator, adversarial tests |
| M3 Evidence repository (SQLite) | **Done** | Persist articles, evidence, research questions/runs |
| M4 Search strategy + histiocytosis vocabulary | **Done** | Config-driven YAML (ECD, LCH, mixed disease) + query expansion |
| M5 ClinicalTrials.gov | **Done** | Official API v2 search/fetch; no inferred status |
| M6 Research loop | **Done** | Quick=1 round, Deep=2 rounds + trials + optional extract/save |
| M7 Evidence critic | **Done** | Deterministic critic labels before synthesis |
| M8 Synthesis + CLI report | **Done** | Markdown report from critiqued EvidenceRecords |
| M9 Case corpus aggregation | **Done** (this branch) | `CaseRecord`, extract, aggregate, critic, `cases_cli` |
| M10 Evidence strength scoring | **Planned** | Internal heuristic ranking; categorical user-facing labels |
| M11 Full-text research | **In progress** | PMC open-access via E-utilities; `--full-text` on `cases_cli` |
| M12 Citation network research | **Planned** | References, citing articles, author search, seminal-paper traversal |
| M13 Researcher & institution mapping | **Planned** | Expert/trial investigator discovery; label metrics honestly |
| M14 Knowledge graph | **Planned** | Relational entities first (PostgreSQL); Neo4j only if justified |
| M15 Time-aware evidence | **Planned** | Supersession, guideline versions, “what changed since …?” |
| M16 Patient-context evidence matching | **Planned** | Local-only structured profile → relevant literature (not prescribing) |
| M17 Continuous monitoring | **Planned** | Scheduled PubMed/trials scans; novelty and contradiction alerts |
| M18 User interface | **Planned** | Streamlit/web UI on top of proven CLI pipeline |

### Near-term checkpoints (A–F)

These are evaluation gates, not separate features. **All complete** — stop-and-evaluate at F was the right call before M9.

| Checkpoint | Status | Definition |
| --- | --- | --- |
| A Live PubMed ECD search | **Done** | Real PMIDs from NCBI E-utilities |
| B One article → validated EvidenceRecords | **Done** | Extract + provenance validator |
| C Ten papers → small evidence corpus | **Done** | Multi-paper extract + SQLite persist |
| D Question → multi-query evidence build | **Done** | Search strategy + research loop |
| E Critic verifies before synthesis | **Done** | Adversarial labels on every claim |
| F First deep research report | **Done** | Neurological ECD + molecular benchmark (`research_report.md`) |

### Numbering note

The original draft had **17 numbered milestones** (M1–M17) plus **A–F checkpoints** — **23 milestone markers total**. During shipping we condensed M10+ into one line. **M9 Case corpus aggregation** was added after Milestone F because the benchmark exposed a gap: questions like “across all CNS cases, does earlier BRAF/MEK therapy correlate with better recovery?” need structured aggregation, not one-paper synthesis. Original **M9 Evidence Strength** is now **M10**; subsequent milestones shift by one.

---

## Mission

Build an open-source AI research system centered on **Erdheim-Chester disease (ECD)** that systematically discovers, evaluates, connects, updates, and cites medical evidence — including related **histiocytosis** literature (LCH, mixed disease) when relevant to a research question.

The system should behave like a rigorous research analyst, not a generic medical chatbot.

Core design principle:

> The agent's job is not to "know" ECD. Its job is to reliably discover, verify, organize, and synthesize evidence about ECD.

---

## Architecture (North Star)

```text
USER QUESTION
      |
      v
Research Director
      |
      +-- Literature Researcher
      +-- Trials Researcher
      +-- Web / Other Sources
      |
      v
Evidence Extraction → Evidence Repository → Evidence Critic → Synthesis
      |
      v
REPORT + SOURCES + GAPS
```

Implement in validated vertical slices. Do not build the full tree empty.

---

## Technology Direction

**Now:** Python 3.12+, Pydantic, requests, python-dotenv, pytest, OpenAI Python SDK, SQLite, GitHub.

**Later:** PostgreSQL/pgvector, full-text PDF ingestion, OpenAI Agents SDK, Streamlit, scheduled monitoring, Crossref, web search for lead generation.

Do not start with Neo4j.

---

## Milestones 1–8 (Done)

### M1 — PubMed Foundation

- `search_pubmed(query, max_results=20) -> list[str]`
- `get_pubmed_articles(pmids) -> list[PubMedArticle]`
- `PubMedArticle`: `pmid`, `title`, `authors`, `journal`, `publication_date`, `abstract`, `doi`, `pubmed_url`
- Source of truth: **NCBI E-utilities only**; missing metadata stays missing

### M1.1 — Date-Range Search

```python
search_pubmed_by_date(query, start_date, end_date, max_results=100) -> list[str]
```

### M2 — Atomic Evidence Extraction

Primary stored object is an **evidence record**, not a paper summary.

```python
extract_evidence(article: PubMedArticle, research_question: str) -> list[EvidenceRecord]
validate_evidence_record(record, source_article) -> ValidationResult
```

Evidence boundary: research question + article metadata + title + abstract + DOI + URL only. No record enters trusted output without provenance validation.

### M3 — Evidence Repository

SQLite for articles, evidence, research questions/runs — audit from day one of persistence.

### M4 — Research Search Strategy

Query expansion + configurable histiocytosis vocabulary YAML (ECD, LCH, mixed disease, organ/molecular/treatment terms).

### M5 — ClinicalTrials.gov

API v2 search/fetch. **Never infer trial status** — ClinicalTrials.gov is source of truth.

### M6 — Research Loop

Iterative search: strategy → PubMed → rank → extract → follow-up queries → repeat. Deep ≥ 2 rounds; Exhaustive stops on diminishing returns (two consecutive rounds with no materially new findings).

### M7 — Evidence Critic

Adversarial review before synthesis: `SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED` / `CONTRADICTED`. Checks: source support, over-generalization from case reports, study design honesty, contradictory evidence, treatment-instruction leakage.

### M8 — Research Synthesis

Reports built from validated, critiqued EvidenceRecords only — not raw-paper → LLM → answer. Sections: bottom line, established/emerging evidence, molecular/treatment/organ findings, conflicts, trials, limitations, gaps, specialist questions, sources.

---

## Milestone 9 — Case Corpus Aggregation (Next)

**Goal:** Answer questions that require **many case reports**, not one paper at a time.

Example benchmark question:

> Across all published CNS-ECD cases, is earlier initiation of BRAF/MEK-targeted therapy associated with better neurologic recovery than delayed treatment?

Implement:

- `CaseRecord` model — fields only when present in source: disease label (ECD/LCH/mixed), organs, mutation, therapy, time from symptoms → diagnosis → treatment, neurologic outcomes, PMID, supporting text
- Extraction tuned for case reports and small series (distinct from general `EvidenceRecord` claims)
- Aggregation over validated case records: counts, tables, gaps — **never invented statistics**
- Include LCH and mixed histiocytosis when the question warrants it; tag disease context per record
- Critic rules: case reports cannot support population-level causation without sufficient series

Depends on: M2–M8 (done). Greatly improved by M11 full-text — timing/outcome fields are often missing from abstracts.

---

## Milestone 10 — Evidence Strength Scoring

Do not pretend to implement a validated clinical grading system (GRADE, etc.). Use an **internal research heuristic** for ranking only.

Factors: study design, sample size, direct relevance, replication, consistency, recency, source quality.

Potential internal formula:

```text
Evidence score = study quality × relevance × replication × consistency × recency modifier
```

User-facing output stays **categorical** (`high` / `moderate` / `low` / `very_low` / `insufficient`) and shows **why**. Partially addressed today via `EvidenceStrength` on records and critic labels; M10 adds explicit cross-study ranking.

---

## Milestone 11 — Full-Text Research

Abstract-only research is insufficient for the mature system.

Sources:

- PubMed Central
- Open-access journal content
- Legally obtained user PDFs
- Author manuscripts where available

Pipeline:

```text
PDF / HTML → document parsing → sections → source-aware chunks → evidence extraction
```

Every chunk retains: PMID, DOI, title, section, page (if available), source URL. Source identity must never be lost during chunking.

Critical for M9: case reports often report diagnosis-to-treatment timing and neurologic outcomes only in the full text.

---

## Milestone 12 — Citation Network Research

Research traversal beyond keyword search:

```python
find_related_articles(pmid)
find_references(pmid)
find_citing_articles(doi)
search_author(author)
search_similar_articles(pmid)
```

Research loop capability:

```text
Find recent review → follow references backward → find seminal study
    → follow citations forward → find newer evidence
```

Also consider Crossref for DOI graph edges. Tier-5 web search may generate leads but rarely serves as primary evidence.

---

## Milestone 13 — Researcher and Institution Mapping

ECD is rare enough that identifying leading experts matters.

Entities: researcher, institution, paper, trial, mutation, treatment, organ system.

Track:

```text
researcher → authored → paper
researcher → investigator_on → trial
researcher → affiliated_with → institution
```

Outputs (labeled accurately — publication count ≠ clinical expertise):

- Most prolific ECD researchers
- Researchers publishing recently on CNS / cardiovascular ECD
- Investigators on active ECD trials

---

## Milestone 14 — Knowledge Graph

Only after the evidence repository works well.

Entities: Disease, Mutation, Gene, Pathway, Drug, Organ, Symptom, ImagingFinding, Biomarker, Researcher, Institution, Study, Trial, Outcome, AdverseEvent.

Example relationships:

```text
MUTATION → AFFECTS → PATHWAY
DRUG → TARGETS → PATHWAY
DISEASE → AFFECTS → ORGAN
STUDY → INVESTIGATES → TREATMENT
TRIAL → TESTS → TREATMENT
```

Implement relationally in PostgreSQL first. Evaluate Neo4j only if graph traversal requirements justify it.

---

## Milestone 15 — Time-Aware Evidence

Medical knowledge changes. Track:

```text
published_at, retrieved_at, validated_at, guideline_version, superseded_by, evidence_status
```

Enable questions like:

- How has treatment of BRAF-positive ECD changed since 2010?
- What evidence published after 2024 changes previous understanding?
- Which older approaches have been superseded?

Do not simply rank by newest date — new case reports do not automatically supersede stronger older evidence.

---

## Milestone 16 — Patient-Context Evidence Matching

Only after the general research engine is reliable. **Patient data must not live in the public GitHub repo.**

```python
class PatientContext(BaseModel):
    mutation_status: list[str]
    current_treatments: list[str]
    previous_treatments: list[str]
    organ_involvement: list[str]
    neurological_involvement: bool | None
    # ... other organ flags, major findings, complications
```

Ask: *Which published evidence is most relevant to this profile?*

Do **not** ask: *What treatment should this patient take?*

Output: direct matches, partial matches, important differences, potentially relevant trials, questions for specialists.

---

## Milestone 17 — Continuous Monitoring

Scheduled scans of PubMed, ClinicalTrials.gov, ECD organizations, major journals, conference abstracts, selected researchers.

For each new item: relevance, novelty, evidence strength, clinical significance, relationship to known evidence, potential contradiction.

Example alert:

```text
3 new ECD publications detected.
1 may materially change current understanding.
2 are incremental case reports.
```

---

## Milestone 18 — User Interface

Start with CLI (done). Add Streamlit or web app.

Potential controls: research question, depth (Quick / Deep / Exhaustive), focus (Molecular, Treatment, Neurological, Trials, …).

Results: executive summary, evidence table, trials, contradictions, gaps, openable sources.

Every source directly openable; every claim traceable to EvidenceRecord → supporting passage.

---

## Research Modes

| Mode | Behavior |
| --- | --- |
| **Quick** | Orientation: ~5–15 highly relevant sources, 1 search cycle |
| **Deep** | Default serious mode: multiple query expansions, ≥2 search cycles, evidence extraction, critic, trials |
| **Exhaustive** | Continue until two consecutive rounds produce no materially new findings, treatments, mutations, trials, or contradictions |

---

## Source Hierarchy

| Tier | Examples | Use |
| --- | --- | --- |
| 1 — Primary | PubMed original research, trials, FDA/NIH, ClinicalTrials.gov | Primary evidence |
| 2 — Synthesis | Guidelines, systematic reviews, UpToDate clinical topics, major academic centers | High-quality secondary (link only; do not scrape paywalled text) |
| 3 — ECD-specialized | ECD Global Alliance, registries, specialty conferences | Context + leads |
| 4 — Emerging | Case reports, conference abstracts, preprints | Valuable in rare disease; label strength honestly |
| 5 — Discovery | General web, communities, social media | Research leads only — rarely primary evidence |

---

## ECD-Specific Research Domains

The system should eventually support focused research in:

- **Molecular:** BRAF V600E, fusions, MAP2K1, KRAS/NRAS/ARAF, MAPK pathway, RNA-seq, liquid biopsy
- **Treatments:** BRAF/MEK inhibition, interferon, cladribine, cytokine-targeted therapy, surgery, emerging agents
- **Organ systems:** CNS, cardiovascular, periaortic/pericardial, renal/retroperitoneal, pulmonary, skeletal, orbital, endocrine, cutaneous
- **Diagnosis:** histopathology, IHC, molecular testing, PET/MRI/CT, differential diagnosis, mixed histiocytosis
- **Prognosis:** organ involvement, mutation, treatment response, progression, organ-specific outcomes

Vocabulary lives in configurable YAML — not hard-coded through application logic.

---

## First Benchmark Research Question

End-to-end benchmark (Milestone F — **completed**):

```text
What is the current evidence for treating neurological involvement in Erdheim-Chester disease, and how does molecular status affect treatment evidence?
```

The system should: generate multiple search strategies; identify CNS and BRAF/MEK literature; extract study-level evidence; distinguish trials from case reports; surface contradictions and gaps; produce citation-backed synthesis.

**Next benchmark (M9):**

```text
Across published CNS-ECD and relevant mixed histiocytosis cases, what does the literature report about timing of BRAF/MEK-targeted therapy and neurologic outcomes?
```

---

## Auditability

Every research run should record: question, timestamp, queries executed, sources retrieved/rejected, EvidenceRecords produced, model/prompt version, critic findings, final report.

Long-term lineage:

```text
claim → EvidenceRecord → source article → supporting passage
```

---

## Implementation Sequence (Recommended)

Do not skip ahead unless a dependency requires it.

```text
 1. PubMed retrieval                    [M1 — done]
 2. EvidenceRecord + extraction         [M2 — done]
 3. Provenance validation               [M2 — done]
 4. SQLite persistence                  [M3 — done]
 5. Search-query expansion              [M4 — done]
 6. Iterative research loop             [M6 — done]
 7. ClinicalTrials.gov                  [M5 — done]
 8. Evidence critic                     [M7 — done]
 9. Research synthesis + CLI report     [M8 — done]
10. Case corpus aggregation             [M9 — next]
11. Evidence strength scoring           [M10]
12. Full-text ingestion                 [M11]
13. Citation graph traversal            [M12]
14. Researcher/institution mapping      [M13]
15. PostgreSQL + pgvector               [supports M14+]
16. Patient-context matching            [M16]
17. Continuous monitoring               [M17]
18. Knowledge graph                     [M14]
19. Streamlit / web UI                  [M18]
```

Trustworthiness before architectural sophistication.

---

## Clinical Boundary

**May:** summarize evidence, compare studies, identify specialist questions, identify trials, explain molecular findings as reported in sources, match literature to a structured profile.

**Must not:** diagnose, prescribe, instruct treatment changes, present inference as clinical recommendation, or delay urgent care.

---

## Testing

- Unit tests for parsing and provenance (fail closed).
- Adversarial tests: no universal efficacy from case reports; no inventing mutations; no mislabeling reviews as trials.
- Live network tests separated from deterministic unit tests.

---

## Open Source Guardrails

Never commit patient records, API keys, private medical information, or licensed PDFs without redistribution rights.

Provide over time: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, architecture docs.

---

## Final Product Vision

The mature system accepts a research question and performs planning → systematic search → retrieval → citation traversal → extraction → validation → trial search → contradiction search → critical review → synthesis.

Returns: bottom line, strongest relevant evidence, molecular considerations, organ-specific evidence, emerging options, active trials, contradictions, what is not known, specialist questions, full sources.

Every conclusion traceable. Build an exceptionally reliable **ECD** research system first — generalize to a rare-disease evidence engine only after ECD quality is proven.
