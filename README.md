# ECD Research Agent

Open-source AI research tooling for [Erdheim-Chester disease (ECD)](https://pubmed.ncbi.nlm.nih.gov/?term=Erdheim-Chester+disease).

> This is a research aid, not a doctor. It does not diagnose, prescribe, or tell anyone to start, stop, or change treatment. Urgent symptoms require urgent medical care.

---

## Why This Project Exists

This project is personal.

My sister has **Erdheim-Chester disease (ECD)**, a rare and complex disease, and she is not doing well.

When a disease is this rare, the problem is not simply finding information. The problem is finding the *right* information, understanding how strong the evidence is, knowing whether newer research has changed older assumptions, and connecting findings across mutations, organ involvement, treatments, case reports, trials, and specialist experience.

That work is difficult even for experienced researchers. It is much harder for patients and families who are trying to understand what may be relevant while also dealing with the urgency and uncertainty of serious illness.

The motivation for this project is to reduce that gap.

The goal is to build an AI research system that can search deeply, reason carefully over the evidence, and make its conclusions auditable.

It should help answer questions such as:

- What does the strongest current evidence say?
- What treatments have been studied in patients with similar disease characteristics?
- Are there rare case reports that may be relevant?
- Does mutation status change what evidence matters?
- Are there active or recently completed clinical trials?
- Has new research challenged older recommendations?
- Where do experts disagree?
- What important questions should be raised with an ECD specialist?

The system is **not** intended to replace physicians or make treatment decisions.

It is intended to improve the research process surrounding those decisions.

## The Core Problem

Rare diseases create an information problem.

Relevant evidence may be scattered across small clinical trials, retrospective cohorts, case series, individual case reports, pathology and molecular studies, imaging literature, conference publications, consensus recommendations, ClinicalTrials.gov, and work from a relatively small number of specialist researchers.

For a common disease, randomized trials and established guidelines may answer many questions.

For ECD, an important clue may instead appear in a paper involving a handful of patients or even a single unusual molecular finding.

That makes research both more valuable and more dangerous.

An AI system can search far more material than a person can, but it can also easily overgeneralize weak evidence, hallucinate citations, or turn an interesting case report into an unjustified treatment conclusion.

**This project is being designed specifically to prevent that.**

## What We Are Trying to Build

The system should function more like a rigorous research analyst than a chatbot.

Instead of:

```text
Question → LLM memory → answer
```

the intended workflow is:

```text
Question
  → research plan
  → multiple literature searches
  → source retrieval
  → evidence extraction
  → provenance validation
  → contradiction search
  → clinical-trial search
  → critical review
  → synthesis
  → answer with traceable evidence
```

The underlying principle:

> The model should not be trusted because it sounds knowledgeable. The system should be trusted only to the extent that its conclusions can be traced back to evidence.

### Why atomic evidence matters

We store individual evidence claims—not only paper summaries—so later we can ask questions like:

> Show all evidence concerning CNS ECD in patients with MAPK-pathway alterations who received MEK inhibition, ranked by strength and relevance.

Each claim should point to a study, supporting passage, PMID/DOI, study design, sample size, and limitations.

### Why contradictions matter

If ten papers suggest one interpretation and two suggest another, those two must not disappear during summarization. The Evidence Critic exists to surface disagreement, population differences, and over-generalization from case reports.

### Why time matters

ECD research has evolved with molecular understanding. Technically well-cited older answers may no longer represent the best current evidence. The system should eventually track what was believed, what changed, and what remains uncertain.

### Why patient context eventually matters

Long term, structured patient characteristics (mutation, organs involved, prior therapies) should help retrieve *matching published evidence*—not generate treatment decisions. Evidence matching is research. Prescribing is clinical care. This project stays on the research side.

## Why This Is Open Source

ECD is too rare for this to be useful only to one family.

If the system becomes effective, the same infrastructure could help other ECD patients and families, clinicians researching unusual presentations, researchers, advocacy organizations, and eventually other rare-disease communities.

Open source also makes the system auditable. Contributors and users should be able to inspect how sources are selected, how evidence is extracted, how strength is assigned, how hallucinations are prevented, and how contradictions are handled.

**For a medical research system, transparency is a feature.**

## What Success Looks Like

Someone confronting a difficult ECD question should be able to move from “I don’t know where to begin” to:

- the most relevant studies
- what they actually found
- how strong that evidence is
- where studies disagree
- what has changed recently
- relevant trials
- remaining unanswered questions
- sources so every conclusion can be independently verified

For my family, the motivation is immediate.

For the project, the ambition is broader:

> Make the world's available evidence on a rare disease easier to discover, harder to misrepresent, and more useful to the people who urgently need to understand it.

---

## How to Contribute

You do not need to be an ECD specialist to help.

Useful contribution areas:

- PubMed / NCBI tooling and tests
- ClinicalTrials.gov integration
- evidence extraction and provenance validation
- adversarial tests (hallucination / overgeneralization traps)
- documentation and ECD terminology vocabularies
- CLI / later UI work
- research methodology review

Please never commit patient records, API keys, private medical information, or licensed article PDFs without redistribution rights.

Roadmap and design notes: [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md) · [docs/MISSION.md](docs/MISSION.md)

## Current Status

| Area | Status |
| --- | --- |
| PubMed search/fetch (NCBI E-utilities) | Available |
| Date-range PubMed search | Available |
| Atomic evidence extraction + provenance validation | Available (CLI; requires `OPENAI_API_KEY`) |
| SQLite evidence repository | Available (`--save` on evidence CLI) |
| Search strategy + ECD vocabulary | Available |
| ClinicalTrials.gov API v2 | Available |
| Multi-round research loop (Quick/Deep) | Available |
| Critic, synthesis UI | Not yet |

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set optional `NCBI_EMAIL` / `NCBI_API_KEY`. For evidence extraction, set `OPENAI_API_KEY`.

## CLI

Newest ECD papers on PubMed:

```bash
python -m ecd_research.cli
# or: ecd-pubmed
```

Extract validated evidence claims for one PMID:

```bash
python -m ecd_research.evidence_cli --pmid 42624824 --question "What evidence exists for diagnosing ECD?"
```

Persist to local SQLite (`data/ecd_research.db` by default):

```bash
python -m ecd_research.evidence_cli --pmid 42624824 --question "What evidence exists for diagnosing ECD?" --save
```

Optional: set `ECD_DB_PATH` or pass `--db path/to/file.db`.

Generate PubMed query expansions from a research question:

```bash
python -m ecd_research.strategy_cli --question "What is the evidence for treating neurological ECD with BRAF/MEK therapy?"
```

Search ClinicalTrials.gov:

```bash
python -m ecd_research.trials_cli --condition "Erdheim-Chester disease" --max-results 10
```

Run Deep research (2 PubMed rounds + trials; add `--save` to persist):

```bash
python -m ecd_research.research_cli --question "What is the current evidence for treating neurological involvement in Erdheim-Chester disease, and how does molecular status affect treatment evidence?" --mode deep --no-extract
```

Omit `--no-extract` when `OPENAI_API_KEY` is set to also build validated evidence records.
## Tests

```bash
pytest
```

## Library usage

```python
from ecd_research.tools.pubmed import (
    search_pubmed,
    search_pubmed_by_date,
    get_pubmed_articles,
)

pmids = search_pubmed("Erdheim-Chester disease", max_results=10)
articles = get_pubmed_articles(pmids)
```
