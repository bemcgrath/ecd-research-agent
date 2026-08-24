"""PubMed Central full-text access via official NCBI E-utilities."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Any

import requests
from dotenv import load_dotenv

from ecd_research.models import FullTextDocument, FullTextSection

load_dotenv()

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "ecd-research-agent"
DEFAULT_TIMEOUT = 60
PMID_PATTERN = re.compile(r"^\d+$")
WHITESPACE_RE = re.compile(r"\s+")


def _ncbi_params(**extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"tool": TOOL_NAME, **extra}
    email = os.getenv("NCBI_EMAIL", "").strip()
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    return params


def _get(endpoint: str, params: dict[str, Any]) -> requests.Response:
    response = requests.get(
        f"{EUTILS_BASE}/{endpoint}",
        params=params,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response


def _normalize_space(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def _element_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return _normalize_space("".join(element.itertext()))


def resolve_pmcid(pmid: str) -> str | None:
    """Map a PubMed PMID to a PMCID via ELink, or None if not in PMC."""
    if not PMID_PATTERN.match(pmid):
        raise ValueError(f"Invalid PMID: {pmid!r}")

    response = _get(
        "elink.fcgi",
        _ncbi_params(
            dbfrom="pubmed",
            db="pmc",
            id=pmid,
            retmode="json",
        ),
    )
    payload = response.json()
    for linkset in payload.get("linksets", []):
        for db in linkset.get("linksetdbs", []):
            if db.get("dbto") != "pmc":
                continue
            links = db.get("links") or []
            if links:
                pmc_id = str(links[0])
                return pmc_id if pmc_id.startswith("PMC") else f"PMC{pmc_id}"
    return None


def _parse_sections(article: ET.Element) -> list[FullTextSection]:
    sections: list[FullTextSection] = []

    abstract = article.find("./front/article-meta/abstract")
    if abstract is not None:
        text = _element_text(abstract)
        if text:
            sections.append(
                FullTextSection(title="Abstract", text=text, section_type="abstract")
            )

    body = article.find("body")
    if body is not None:
        top_secs = list(body.findall("sec"))
        if top_secs:
            for sec in top_secs:
                _collect_sec(sec, sections, parent_title=None)
        else:
            # Flat body paragraphs without nested <sec>
            text = _element_text(body)
            if text:
                sections.append(
                    FullTextSection(title="Body", text=text, section_type="body")
                )

    return sections


def _collect_sec(
    sec: ET.Element,
    sections: list[FullTextSection],
    *,
    parent_title: str | None,
) -> None:
    title_el = sec.find("title")
    title = _element_text(title_el) or None
    if parent_title and title:
        title = f"{parent_title} > {title}"
    elif parent_title and not title:
        title = parent_title

    # Direct paragraphs only (not nested sec children)
    para_parts: list[str] = []
    for child in list(sec):
        if child.tag == "p":
            t = _element_text(child)
            if t:
                para_parts.append(t)
        elif child.tag in {"fig", "table-wrap", "boxed-text"}:
            # Skip figures/tables for extraction corpus (keep prose)
            continue

    if para_parts:
        sections.append(
            FullTextSection(
                title=title,
                text="\n\n".join(para_parts),
                section_type="body",
            )
        )

    for child in sec.findall("sec"):
        _collect_sec(child, sections, parent_title=title)


def parse_pmc_xml(xml_text: str, *, pmid: str | None = None) -> FullTextDocument | None:
    """Parse PMC JATS XML into a FullTextDocument. Returns None if unusable."""
    root = ET.fromstring(xml_text)
    article = root.find(".//article")
    if article is None:
        return None

    meta = article.find("./front/article-meta")
    if meta is None:
        return None

    pmcid = None
    doi = None
    pmid_from_xml = None
    for art_id in meta.findall("article-id"):
        id_type = art_id.get("pub-id-type")
        value = (art_id.text or "").strip()
        if not value:
            continue
        if id_type in {"pmcid", "pmc"}:
            pmcid = value if value.startswith("PMC") else f"PMC{value}"
        elif id_type == "doi":
            doi = value
        elif id_type == "pmid":
            pmid_from_xml = value

    resolved_pmid = pmid or pmid_from_xml
    if not resolved_pmid or not pmcid:
        return None

    title = _element_text(meta.find("./title-group/article-title")) or None
    sections = _parse_sections(article)
    raw_parts: list[str] = []
    if title:
        raw_parts.append(title)
    for section in sections:
        header = section.title or "Section"
        raw_parts.append(f"## {header}\n{section.text}")
    raw_text = "\n\n".join(raw_parts).strip()
    if not raw_text:
        return None

    return FullTextDocument(
        pmid=resolved_pmid,
        pmcid=pmcid,
        title=title,
        doi=doi,
        source_url=f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/",
        sections=sections,
        raw_text=raw_text,
        abstract_limited=False,
    )


def fetch_pmc_full_text(pmid: str) -> FullTextDocument | None:
    """Fetch open-access PMC full text for a PMID, or None if unavailable."""
    if not PMID_PATTERN.match(pmid):
        raise ValueError(f"Invalid PMID: {pmid!r}")

    pmcid = resolve_pmcid(pmid)
    if pmcid is None:
        return None

    pmc_numeric = pmcid.removeprefix("PMC")
    response = _get(
        "efetch.fcgi",
        _ncbi_params(
            db="pmc",
            id=pmc_numeric,
            rettype="xml",
            retmode="xml",
        ),
    )
    return parse_pmc_xml(response.text, pmid=pmid)


def build_fulltext_corpus(
    document: FullTextDocument,
    *,
    max_chars: int = 60000,
) -> str:
    """Build a provenance corpus from full text, preferring case/result sections."""
    priority_keywords = (
        "case",
        "presentation",
        "outcome",
        "treatment",
        "result",
        "discussion",
        "abstract",
    )

    def score(section: FullTextSection) -> int:
        hay = (section.title or "").lower()
        for i, keyword in enumerate(priority_keywords):
            if keyword in hay:
                return 100 - i
        return 0

    ordered = sorted(document.sections, key=score, reverse=True)
    parts: list[str] = []
    if document.title:
        parts.append(document.title)

    used = sum(len(p) for p in parts)
    for section in ordered:
        block = section.text
        if section.title:
            block = f"{section.title}\n{section.text}"
        if used + len(block) + 2 > max_chars:
            remaining = max_chars - used - 2
            if remaining > 200:
                parts.append(block[:remaining])
            break
        parts.append(block)
        used += len(block) + 2

    return "\n\n".join(parts)
