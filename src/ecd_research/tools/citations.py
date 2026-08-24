"""Citation neighborhood via official NCBI ELink (PubMed)."""

from __future__ import annotations

from typing import Any

from ecd_research.tools.pubmed import PMID_PATTERN, _get, _ncbi_params


def _parse_elink_pmids(payload: dict[str, Any], *, linkname: str) -> list[str]:
    """Extract PMIDs for a named PubMed-to-PubMed link, preserving NCBI order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for linkset in payload.get("linksets", []):
        for db in linkset.get("linksetdbs", []):
            if db.get("dbto") != "pubmed":
                continue
            if db.get("linkname") != linkname:
                continue
            for link in db.get("links") or []:
                pmid = str(link).strip()
                if PMID_PATTERN.fullmatch(pmid) and pmid not in seen:
                    seen.add(pmid)
                    ordered.append(pmid)
    return ordered


def find_pubmed_references(pmid: str, *, max_results: int = 50) -> list[str]:
    """PMIDs cited by this paper (references / bibliography), NCBI order."""
    if not PMID_PATTERN.fullmatch(pmid.strip()):
        raise ValueError(f"invalid PMID: {pmid!r}")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    response = _get(
        "elink.fcgi",
        _ncbi_params(
            dbfrom="pubmed",
            db="pubmed",
            id=pmid.strip(),
            retmode="json",
            linkname="pubmed_pubmed_refs",
        ),
    )
    return _parse_elink_pmids(response.json(), linkname="pubmed_pubmed_refs")[:max_results]


def find_citing_articles(pmid: str, *, max_results: int = 50) -> list[str]:
    """PMIDs that cite this paper (PubMed cited-in links), NCBI order."""
    if not PMID_PATTERN.fullmatch(pmid.strip()):
        raise ValueError(f"invalid PMID: {pmid!r}")
    if max_results < 1:
        raise ValueError("max_results must be >= 1")

    response = _get(
        "elink.fcgi",
        _ncbi_params(
            dbfrom="pubmed",
            db="pubmed",
            id=pmid.strip(),
            retmode="json",
            linkname="pubmed_pubmed_citedin",
        ),
    )
    return _parse_elink_pmids(response.json(), linkname="pubmed_pubmed_citedin")[
        :max_results
    ]


def expand_citation_neighborhood(
    seed_pmids: list[str],
    *,
    include_references: bool = True,
    include_citing: bool = True,
    max_per_seed: int = 40,
    max_total: int = 80,
) -> tuple[list[str], dict[str, list[str]]]:
    """Expand seeds with unique neighbor PMIDs (not including the seeds themselves).

    Returns (ordered new PMIDs, audit map of seed -> neighbors found).
    """
    if max_per_seed < 1 or max_total < 1:
        raise ValueError("max_per_seed and max_total must be >= 1")

    cleaned: list[str] = []
    seen_seeds: set[str] = set()
    for raw in seed_pmids:
        pmid = raw.strip()
        if not PMID_PATTERN.fullmatch(pmid):
            raise ValueError(f"invalid PMID: {raw!r}")
        if pmid not in seen_seeds:
            seen_seeds.add(pmid)
            cleaned.append(pmid)

    audit: dict[str, list[str]] = {}
    neighbors: list[str] = []
    seen_neighbors: set[str] = set()

    for seed in cleaned:
        found: list[str] = []
        if include_references:
            found.extend(find_pubmed_references(seed, max_results=max_per_seed))
        if include_citing:
            found.extend(find_citing_articles(seed, max_results=max_per_seed))
        unique_for_seed: list[str] = []
        for pmid in found:
            if pmid in seen_seeds or pmid in seen_neighbors:
                continue
            unique_for_seed.append(pmid)
            seen_neighbors.add(pmid)
            neighbors.append(pmid)
            if len(neighbors) >= max_total:
                audit[seed] = unique_for_seed
                return neighbors, audit
        audit[seed] = unique_for_seed

    return neighbors, audit
