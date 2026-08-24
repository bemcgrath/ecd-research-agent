# User Guide — ECD Research Agent

This tool helps you **find, check, and organize published research** about Erdheim-Chester disease (ECD).

It is a **research aid**, not a doctor.

- It does **not** diagnose.
- It does **not** prescribe or tell anyone to start, stop, or change treatment.
- Urgent symptoms need **urgent medical care**.
- Use outputs to prepare questions for an **ECD specialist**, and verify every important claim against the cited source.

Unfamiliar terms (BRAF, MEK, PMID, Sx→Dx, abstract-limited, etc.): **[GLOSSARY.md](GLOSSARY.md)**.

---

## What you need

1. **Python 3.12+**
2. A terminal (PowerShell on Windows, Terminal on Mac/Linux)
3. Optional but recommended:
   - Free **NCBI** email / API key (for PubMed rate limits)
   - **OpenAI API key** (for evidence extraction and full reports)

Without an OpenAI key you can still search PubMed, expand queries, and list clinical trials. You cannot extract atomic evidence claims or build a full evidence report.

---

## One-time setup

From the project folder:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Install the package:

```bash
pip install -e ".[dev]"
```

Create a local env file:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env`:

| Variable | Required? | Purpose |
| --- | --- | --- |
| `NCBI_EMAIL` | Recommended | Identifies you to NCBI E-utilities |
| `NCBI_API_KEY` | Optional | Higher PubMed request limits |
| `OPENAI_API_KEY` | For reports / extraction | Evidence extraction |
| `OPENAI_MODEL` | Optional | Default `gpt-4.1-mini` |
| `ECD_DB_PATH` | Optional | Custom SQLite path (default `data/ecd_research.db`) |

Never commit `.env` or put real patient information in the repo.

---

## Quick start (recommended path)

### 1) See the newest ECD papers

```bash
python -m ecd_research.cli
```

Shows the 10 newest PubMed results for “Erdheim-Chester disease” with PMID, title, date, journal, and URL.

### 2) Expand a research question into search queries

```bash
python -m ecd_research.strategy_cli --question "What is the evidence for treating neurological ECD with BRAF or MEK therapy?"
```

This does **not** call an LLM. It uses the project’s ECD vocabulary to build multiple PubMed Boolean queries.

### 3) Search clinical trials

```bash
python -m ecd_research.trials_cli --condition "Erdheim-Chester disease" --max-results 10
```

Optional status filter (registry values only; never invented):

```bash
python -m ecd_research.trials_cli --condition "Erdheim-Chester disease" --status RECRUITING
```

Fetch one trial:

```bash
python -m ecd_research.trials_cli --nct NCT05001828
```

### 4) Run a deeper literature search (no AI extraction)

Good first Deep run while you learn the tool:

```bash
python -m ecd_research.research_cli --question "What is the current evidence for treating neurological involvement in Erdheim-Chester disease, and how does molecular status affect treatment evidence?" --mode deep --no-extract
```

- `--mode quick` → 1 search round  
- `--mode deep` → 2 search rounds  
- `--no-extract` → skip OpenAI  
- `--save` → store the run audit locally in SQLite  

### 5) Build a critiqued research report (needs OpenAI)

```bash
python -m ecd_research.report_cli --question "What is the current evidence for treating neurological involvement in Erdheim-Chester disease, and how does molecular status affect treatment evidence?" --mode deep --output research_report.md
```

This will:

1. Expand the question into searches  
2. Query PubMed (2 rounds in Deep mode)  
3. Pull ClinicalTrials.gov results  
4. Extract atomic claims from a few abstracts  
5. Validate provenance (claims must match supplied source text)  
6. Run the evidence critic  
7. Write `research_report.md`

Open the markdown file and **click through every PMID/NCT link** before trusting a conclusion.

Add `--save` if you want the run stored in your local database.

---

## Working with a single paper

Extract validated claims from one PMID:

```bash
python -m ecd_research.evidence_cli --pmid 42624824 --question "What does this paper report about diagnosing ECD?"
```

Save to SQLite:

```bash
python -m ecd_research.evidence_cli --pmid 42624824 --question "What does this paper report about diagnosing ECD?" --save
```

Only **validated** claims are saved. Invented or unsupported text is dropped.

---

## Command cheat sheet

| Goal | Command |
| --- | --- |
| Newest ECD papers | `python -m ecd_research.cli` |
| Query expansion | `python -m ecd_research.strategy_cli --question "..."` |
| Trials search | `python -m ecd_research.trials_cli` |
| Multi-round research | `python -m ecd_research.research_cli --question "..." --mode deep` |
| Full report | `python -m ecd_research.report_cli --question "..." --output research_report.md` |
| Case corpus (abstracts) | `python -m ecd_research.cases_cli --output case_corpus_report.md` |
| Case corpus + PMC full text | `python -m ecd_research.cases_cli --full-text --save --output case_corpus_fulltext.md` |
| Follow citations from a seed PMID | `python -m ecd_research.cases_cli --pmids 41562816 --expand-citations --full-text --max-extract 15` |
| Multi-seed expand → master table | `python -m ecd_research.cases_cli --pmids 41562816,30225465,40131415 --expand-citations --citation-seeds 41562816,30225465,40131415 --full-text --max-extract 20 --output case_corpus_master.md` |
| One-paper evidence | `python -m ecd_research.evidence_cli --pmid ... --question "..."` |
| Run tests | `pytest` |

Case corpus cleanup notes:

- **Multi-seed expansion** — comma-separated `--citation-seeds` / `--pmids` expand neighbors from each seed (neighbor budget is split across seeds). Explicit seeds are always kept in the extract set before neighbors fill remaining `--max-extract` slots.
- **Same-patient duplicates** — rows that share mutation, therapy timing, and overlapping neurologic scores/timeline text are **marked** (not merged). Unique-patient timing counts exclude the secondary PMID.
- **Reviews / large series** — rows with large `n` (or review-style titles) appear in a separate table so they are not counted as individual patients.

On some Windows setups, console scripts like `ecd-pubmed` may be blocked by application control. Prefer `python -m ecd_research...` if that happens.

---

## How to read the report

Typical sections:

- **BOTTOM LINE** — summary of what this run actually produced (not “the truth about ECD”)
- **ESTABLISHED / EMERGING EVIDENCE** — claims grouped by extracted strength
- **MOLECULAR / TREATMENT** — claims that mention those facets
- **CONFLICTING EVIDENCE** — critic-flagged tensions
- **CLINICAL TRIALS** — registry rows from ClinicalTrials.gov
- **LIMITATIONS / RESEARCH GAPS**
- **QUESTIONS FOR AN ECD SPECIALIST**
- **SOURCES** — PMIDs and NCT links

Critic labels you may see:

| Label | Meaning |
| --- | --- |
| `SUPPORTED` | Passed critic checks for this run |
| `PARTIALLY_SUPPORTED` | Usable with caveats (often abstract-limited or case-report limits) |
| `UNSUPPORTED` | Failed provenance / safety checks; excluded from trusted synthesis |
| `CONTRADICTED` | Possible conflict with another claim in the same run |

Early reports are often **abstract-limited**. That means the system only saw titles/abstracts, not full papers.

---

## Local database (SQLite)

When you use `--save`, results go to `data/ecd_research.db` by default (gitignored).

This is a **personal/local** store on your machine. Each developer or family member typically has their own copy. It is not a shared multi-user cloud database.

---

## Good questions to ask the tool

Better:

- “What published evidence exists for neurological ECD and BRAF/MEK therapy?”
- “Which ClinicalTrials.gov studies mention Erdheim-Chester disease?”
- “What does PMID 42624824 actually report in its abstract?”

Worse / out of scope:

- “What treatment should my sister take?”
- “Should we stop drug X?”
- “Diagnose this case from symptoms alone.”

Those are clinical decisions for the care team.

---

## Troubleshooting

| Problem | Try this |
| --- | --- |
| `python` not found | Install Python 3.12+ and reopen the terminal |
| Package import errors | Activate `.venv` and re-run `pip install -e ".[dev]"` |
| PubMed rate limits / errors | Set `NCBI_EMAIL` and `NCBI_API_KEY` in `.env` |
| Evidence/report fails on OpenAI | Set `OPENAI_API_KEY`; check billing/access |
| Empty evidence section | Confirm extraction wasn’t disabled with `--no-extract` |
| Console script blocked on Windows | Use `python -m ecd_research...` instead |

---

## Privacy and safety

- Do not put names, medical record numbers, or private clinical details into GitHub issues, commits, or shared databases.
- Do not commit licensed full-text PDFs unless you have redistribution rights.
- Treat every output as **starting material for specialist discussion**, not a care plan.

---

## Learn more

- Project story: [README.md](../README.md)
- Glossary: [GLOSSARY.md](GLOSSARY.md)
- Roadmap: [ROADMAP.md](ROADMAP.md)
- Short mission note: [MISSION.md](MISSION.md)
