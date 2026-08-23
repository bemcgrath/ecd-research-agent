# ECD Research Agent

Open-source research tooling for [Erdheim-Chester disease](https://pubmed.ncbi.nlm.nih.gov/?term=Erdheim-Chester+disease).

## Milestone 1: PubMed foundation

Search and fetch PubMed articles via official NCBI E-utilities. Missing metadata is never inferred.

### Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

Optional: copy `.env.example` to `.env` and set `NCBI_EMAIL` / `NCBI_API_KEY`.

### CLI

Search the 10 newest papers for Erdheim-Chester disease:

```bash
ecd-pubmed
```

### Tests

```bash
pytest
```

### Library usage

```python
from ecd_research.tools.pubmed import search_pubmed, get_pubmed_articles

pmids = search_pubmed("Erdheim-Chester disease", max_results=10)
articles = get_pubmed_articles(pmids)
```
