# ECD Research Agent

Open-source AI research agent for **Erdheim-Chester disease (ECD)** and related histiocytosis disorders, built to find, evaluate, connect, and cite the latest medical evidence.

> This is a research aid, not a doctor. It does not diagnose, prescribe, or tell anyone to start, stop, or change treatment. Urgent symptoms require urgent medical care.

## What are ECD and LCH? (Plain language)

**Erdheim-Chester disease (ECD)** and **Langerhans cell histiocytosis (LCH)** are both rare disorders of **histiocytes** — cells that are part of the immune system and normally help fight infection and clean up damaged tissue.

In ECD and LCH, these cells behave abnormally and can build up in organs throughout the body (bone, brain, lungs, kidneys, heart, and others). Doctors often classify both diseases within the **histiocytic neoplasms** — a group of serious blood- and immune-cell disorders that, in everyday terms, are **discussed and treated in ways similar to blood cancers**: specialized oncology teams, molecular testing (for example BRAF mutations), and targeted therapies such as BRAF or MEK inhibitors.

They are **not the same as leukemia or lymphoma**, but the comparison helps convey how serious they are and why cancer-style research tools matter.

**ECD** usually affects adults. **LCH** more often affects children but can occur at any age. Some patients have **mixed or overlapping features** of both. Because they share biology, treatments, and medical literature, this project searches **ECD first** but also includes related histiocytosis papers when they matter for a research question (for example CNS involvement or BRAF-targeted therapy).

## Why This Exists

ECD is exceptionally rare — only about **40–50 people are diagnosed with ECD each year in the United States**, and the formal U.S. ECD referral network includes only about **a dozen named physicians with specialized ECD experience**.

That scarcity creates an information problem.

Relevant knowledge is spread across a small number of specialists, research centers, clinical trials, molecular studies, case series, and individual case reports. Important findings may be separated across organ systems, mutations, treatments, and institutions — and across **ECD, LCH, and mixed histiocytosis** labels in the literature.

This project is personal. My sister has Erdheim-Chester disease, which led me to experience firsthand how difficult it can be to find, evaluate, and connect the available research.

The problem is not simply finding information. It is determining:

- which evidence is most relevant
- how strong that evidence is
- whether newer research has changed older assumptions
- how molecular characteristics affect the evidence
- whether similar cases have been reported
- where studies disagree
- which clinical trials may be relevant
- which researchers and institutions have the deepest experience with a particular manifestation of the disease

The goal is an AI research system that searches deeply, evaluates evidence carefully, and makes every important conclusion traceable back to its source.

The system is **not intended to replace physicians or make treatment decisions**. It is intended to improve the research process surrounding those decisions.

> The model should not be trusted because it sounds knowledgeable. The system should be trusted only to the extent that its conclusions can be traced back to evidence.

## Learn more (patients, families, and contributors)

**About the diseases**

- [NIH — Erdheim-Chester disease (GARD)](https://rarediseases.info.nih.gov/diseases/6318/erdheim-chester-disease)
- [NIH — Langerhans cell histiocytosis (GARD)](https://rarediseases.info.nih.gov/diseases/6884/langerhans-cell-histiocytosis)
- [Orphanet — ECD](https://www.orpha.net/consor/cgi-bin/ICDExp.php?lng=EN&Expert=35687)
- [Orphanet — LCH](https://www.orpha.net/consor/cgi-bin/ICDExp.php?lng=EN&Expert=263730)
- [PubMed — ECD literature search](https://pubmed.ncbi.nlm.nih.gov/?term=Erdheim-Chester+disease)

**Organizations**

- [ECD Global Alliance](https://www.erdheim-chester.org/) — ECD patient advocacy, education, and community
- [Histiocytosis Association](https://www.histio.org/) — support and research for LCH, ECD, and related histiocytic disorders
- [National Organization for Rare Disorders (NORD)](https://rarediseases.org/)

---

## How to use it

Full setup and walkthrough: **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**

Roadmap and design: [docs/ROADMAP.md](docs/ROADMAP.md) · [docs/MISSION.md](docs/MISSION.md)

### Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

Copy `.env.example` to `.env`. Set `NCBI_EMAIL` / `NCBI_API_KEY` (recommended) and `OPENAI_API_KEY` (for evidence extraction and reports).

### Quick commands

Newest ECD papers on PubMed:

```bash
python -m ecd_research.cli
```

Generate a critiqued research report:

```bash
python -m ecd_research.report_cli --question "What is the current evidence for treating neurological involvement in Erdheim-Chester disease, and how does molecular status affect treatment evidence?" --mode deep --output research_report.md
```

Aggregate structured fields across case reports:

```bash
python -m ecd_research.cases_cli --question "Across published CNS-ECD cases, what does the literature report about timing of BRAF/MEK-targeted therapy and neurologic outcomes?" --output case_corpus_report.md
```

Other CLIs: query expansion (`strategy_cli`), trials (`trials_cli`), multi-round search (`research_cli`), single-paper evidence (`evidence_cli`). See the [user guide](docs/USER_GUIDE.md).

### Tests

```bash
pytest
```

## Current status

| Area | Status |
| --- | --- |
| PubMed search/fetch (NCBI E-utilities) | Available |
| Date-range PubMed search | Available |
| Atomic evidence extraction + provenance validation | Available (requires `OPENAI_API_KEY`) |
| SQLite evidence repository | Available (`--save`) |
| Search strategy + histiocytosis vocabulary (ECD, LCH, related terms) | Available |
| ClinicalTrials.gov API v2 | Available |
| Multi-round research loop (Quick/Deep) | Available |
| Evidence critic + synthesis report | Available |
| Case corpus aggregation (structured case series) | Available (`cases_cli`) |
| Streamlit UI / full-text / Agents SDK | Not yet |

## Join the effort

You do not need to be a physician or programmer to help. This project welcomes:

- **Patients and families** — benchmark questions, plain-language review, advocacy connections
- **Clinicians and researchers** — methodology review, vocabulary, evidence grading feedback
- **Developers** — PubMed/ClinicalTrials tooling, tests, CLI, future UI
- **Anyone who cares about rare histiocytic disease** — documentation, issue triage, spreading the word

Useful contribution areas: PubMed tooling, ClinicalTrials.gov, evidence extraction, adversarial tests, case-aggregation design (M9), documentation, histiocytosis vocabulary, research methodology review.

Please never commit patient records, API keys, private medical information, or licensed article PDFs without redistribution rights.

Open an issue or pull request on GitHub if you want to contribute.
