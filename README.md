# ECD Research Agent

Open-source AI research agent for Erdheim-Chester disease, built to find, evaluate, connect, and cite the latest medical evidence.

> This is a research aid, not a doctor. It does not diagnose, prescribe, or tell anyone to start, stop, or change treatment. Urgent symptoms require urgent medical care.

## Why This Exists

Erdheim-Chester disease (ECD) is an exceptionally rare and complex disease.

For context, only about **40–50 people are diagnosed with ECD each year in the United States**, and the formal U.S. ECD referral network includes only about **a dozen named physicians with specialized ECD experience**.

That scarcity creates an information problem.

Relevant knowledge is distributed across a relatively small number of specialists, research centers, clinical trials, molecular studies, case series, and even individual case reports. Important findings may be separated across different organ systems, mutations, treatments, and institutions.

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

The goal of this project is to build an AI research system that can search deeply, evaluate evidence carefully, and make every important conclusion traceable back to its source.

The system is **not intended to replace physicians or make treatment decisions**.

It is intended to improve the research process surrounding those decisions.

> The model should not be trusted because it sounds knowledgeable. The system should be trusted only to the extent that its conclusions can be traced back to evidence.

---

## How to use it

Full setup and walkthrough: **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**

Roadmap and design: [docs/MASTER_PLAN.md](docs/MASTER_PLAN.md) · [docs/MISSION.md](docs/MISSION.md)

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
| Search strategy + ECD vocabulary | Available |
| ClinicalTrials.gov API v2 | Available |
| Multi-round research loop (Quick/Deep) | Available |
| Evidence critic + synthesis report | Available |
| Streamlit UI / full-text / Agents SDK | Not yet |

## Contributing

You do not need to be an ECD specialist to help. Useful areas: PubMed tooling, ClinicalTrials.gov, evidence extraction, adversarial tests, documentation, ECD vocabulary, CLI/UI, research methodology review.

Please never commit patient records, API keys, private medical information, or licensed article PDFs without redistribution rights.
