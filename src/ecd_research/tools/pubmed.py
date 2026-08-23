"""PubMed access via official NCBI E-utilities only."""

from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from typing import Any

import requests
from dotenv import load_dotenv

from ecd_research.models import PubMedArticle

load_dotenv()

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "ecd-research-agent"
PMID_PATTERN = re.compile(r"^\d+$")
DEFAULT_TIMEOUT = 30


def _ncbi_params(**extra: Any) -> dict[str, Any]:
    """Build common E-utilities query parameters from the environment."""
    params: dict[str, Any] = {"tool": TOOL_NAME, **extra}
    email = os.getenv("NCBI_EMAIL", "").strip()
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    if email:
        params["email"] = email
    if api_key:
        params["api_key"] = api_key
    return params


def _get(endpoint: str, params: dict[str, Any]) -> requests.Response:
    url = f"{EUTILS_BASE}/{endpoint}"
    response = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response


def _text(element: ET.Element | None, path: str | None = None) -> str | None:
    if element is None:
        return None
    node = element if path is None else element.find(path)
    if node is None or node.text is None:
        return None
    value = "".join(node.itertext()).strip()
    return value or None


def _parse_publication_date(article: ET.Element) -> str | None:
    """Return PubDate / MedlineDate text as present in XML; never invent dates."""
    pub_date = article.find("./Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None

    medline = _text(pub_date, "MedlineDate")
    if medline:
        return medline

    parts: list[str] = []
    for tag in ("Year", "Month", "Day", "Season"):
        value = _text(pub_date, tag)
        if value:
            parts.append(value)
    return " ".join(parts) if parts else None


def _parse_authors(article: ET.Element) -> list[str]:
    authors: list[str] = []
    for author in article.findall("./AuthorList/Author"):
        collective = _text(author, "CollectiveName")
        if collective:
            authors.append(collective)
            continue
        last = _text(author, "LastName")
        initials = _text(author, "Initials")
        if last and initials:
            authors.append(f"{last} {initials}")
        elif last:
            authors.append(last)
        else:
            # Incomplete author node — skip rather than fabricate a name.
            continue
    return authors


def _parse_abstract(article: ET.Element) -> str | None:
    texts: list[str] = []
    for abstract_text in article.findall("./Abstract/AbstractText"):
        label = abstract_text.get("Label")
        body = "".join(abstract_text.itertext()).strip()
        if not body:
            continue
        if label:
            texts.append(f"{label}: {body}")
        else:
            texts.append(body)
    if not texts:
        return None
    return "\n\n".join(texts)


def _parse_doi(pubmed_article: ET.Element) -> str | None:
    for article_id in pubmed_article.findall("./PubmedData/ArticleIdList/ArticleId"):
        if article_id.get("IdType") == "doi" and article_id.text:
            return article_id.text.strip() or None
    article = pubmed_article.find("./MedlineCitation/Article")
    if article is None:
        return None
    for elocation in article.findall("./ELocationID"):
        if elocation.get("EIdType") == "doi" and elocation.text:
            return elocation.text.strip() or None
    return None


def _parse_one_article(pubmed_article: ET.Element) -> PubMedArticle | None:
    medline = pubmed_article.find("./MedlineCitation")
    if medline is None:
        return None
    pmid = _text(medline, "PMID")
    if not pmid:
        return None

    article = medline.find("./Article")
    title = _text(article, "ArticleTitle") if article is not None else None
    journal = None
    authors: list[str] = []
    publication_date = None
    abstract = None
    if article is not None:
        journal = _text(article, "./Journal/Title") or _text(
            article, "./Journal/ISOAbbreviation"
        )
        authors = _parse_authors(article)
        publication_date = _parse_publication_date(article)
        abstract = _parse_abstract(article)

    return PubMedArticle(
        pmid=pmid,
        title=title,
        authors=authors,
        journal=journal,
        publication_date=publication_date,
        abstract=abstract,
        doi=_parse_doi(pubmed_article),
        pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def parse_pubmed_xml(xml_text: str) -> list[PubMedArticle]:
    """Parse PubMed efetch XML into PubMedArticle models."""
    if not xml_text or not xml_text.strip():
        return []
    root = ET.fromstring(xml_text)
    articles: list[PubMedArticle] = []
    for node in root.findall(".//PubmedArticle"):
        parsed = _parse_one_article(node)
        if parsed is not None:
            articles.append(parsed)
    return articles


def search_pubmed(query: str, max_results: int = 20) -> list[str]:
    """Search PubMed and return PMIDs newest-first (NCBI pub_date sort)."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if not isinstance(max_results, int) or max_results < 1:
        raise ValueError("max_results must be an integer >= 1")

    params = _ncbi_params(
        db="pubmed",
        term=query.strip(),
        retmax=max_results,
        retmode="json",
        sort="pub_date",
    )
    response = _get("esearch.fcgi", params)
    payload = response.json()
    id_list = payload.get("esearchresult", {}).get("idlist", [])
    if not isinstance(id_list, list):
        return []
    return [str(pmid) for pmid in id_list]


def get_pubmed_articles(pmids: list[str]) -> list[PubMedArticle]:
    """Fetch PubMed article records for the given PMIDs."""
    if not isinstance(pmids, list):
        raise ValueError("pmids must be a list of PMID strings")
    if not pmids:
        return []

    cleaned: list[str] = []
    for pmid in pmids:
        if not isinstance(pmid, str) or not PMID_PATTERN.fullmatch(pmid.strip()):
            raise ValueError(f"invalid PMID: {pmid!r}")
        cleaned.append(pmid.strip())

    params = _ncbi_params(
        db="pubmed",
        id=",".join(cleaned),
        rettype="abstract",
        retmode="xml",
    )
    response = _get("efetch.fcgi", params)
    articles = parse_pubmed_xml(response.text)

    # Preserve requested PMID order when NCBI returns a subset/reordered set.
    by_pmid = {article.pmid: article for article in articles}
    return [by_pmid[pmid] for pmid in cleaned if pmid in by_pmid]
