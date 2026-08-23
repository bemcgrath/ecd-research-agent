"""Tests for PubMed E-utilities client and XML parsing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ecd_research.tools.pubmed import (
    get_pubmed_articles,
    parse_pubmed_xml,
    search_pubmed,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_XML = (FIXTURES / "pubmed_sample.xml").read_text(encoding="utf-8")


def test_parse_pubmed_xml_full_and_sparse_articles() -> None:
    articles = parse_pubmed_xml(SAMPLE_XML)
    assert len(articles) == 2

    full = articles[0]
    assert full.pmid == "99999999"
    assert full.title == "Complete Erdheim-Chester disease example article"
    assert full.authors == ["Smith J", "Doe JA", "ECD Study Group"]
    assert full.journal == "Example Journal of Rare Diseases"
    assert full.publication_date == "2026 Aug 15"
    assert full.abstract == "BACKGROUND: Background text.\n\nMETHODS: Methods text."
    assert full.doi == "10.1000/example.doi"
    assert str(full.pubmed_url) == "https://pubmed.ncbi.nlm.nih.gov/99999999/"

    sparse = articles[1]
    assert sparse.pmid == "88888888"
    assert sparse.title == "Sparse article with minimal metadata"
    assert sparse.authors == []
    assert sparse.journal is None
    assert sparse.publication_date == "2025 Spring"
    assert sparse.abstract is None
    assert sparse.doi is None
    assert str(sparse.pubmed_url) == "https://pubmed.ncbi.nlm.nih.gov/88888888/"


def test_parse_pubmed_xml_empty_input() -> None:
    assert parse_pubmed_xml("") == []
    assert parse_pubmed_xml("   ") == []


def test_search_pubmed_newest_first_preserves_api_order() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "esearchresult": {"idlist": ["42626609", "42624824", "42620745"]}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("ecd_research.tools.pubmed._get", return_value=mock_response) as mock_get:
        pmids = search_pubmed("Erdheim-Chester disease", max_results=3)

    assert pmids == ["42626609", "42624824", "42620745"]
    _, kwargs = mock_get.call_args
    params = kwargs["params"] if "params" in kwargs else mock_get.call_args[0][1]
    assert params["sort"] == "pub_date"
    assert params["retmax"] == 3
    assert params["term"] == "Erdheim-Chester disease"
    assert params["db"] == "pubmed"


def test_get_pubmed_articles_pmid_retrieval() -> None:
    mock_response = MagicMock()
    mock_response.text = SAMPLE_XML
    mock_response.raise_for_status = MagicMock()

    with patch("ecd_research.tools.pubmed._get", return_value=mock_response) as mock_get:
        articles = get_pubmed_articles(["99999999", "88888888"])

    assert [a.pmid for a in articles] == ["99999999", "88888888"]
    assert articles[0].title == "Complete Erdheim-Chester disease example article"
    called_params = mock_get.call_args[0][1]
    assert called_params["id"] == "99999999,88888888"
    assert called_params["retmode"] == "xml"


def test_get_pubmed_articles_preserves_requested_order() -> None:
    mock_response = MagicMock()
    mock_response.text = SAMPLE_XML
    mock_response.raise_for_status = MagicMock()

    with patch("ecd_research.tools.pubmed._get", return_value=mock_response):
        articles = get_pubmed_articles(["88888888", "99999999"])

    assert [a.pmid for a in articles] == ["88888888", "99999999"]


def test_invalid_search_input() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        search_pubmed("")
    with pytest.raises(ValueError, match="non-empty"):
        search_pubmed("   ")
    with pytest.raises(ValueError, match="max_results"):
        search_pubmed("ECD", max_results=0)
    with pytest.raises(ValueError, match="max_results"):
        search_pubmed("ECD", max_results=-1)


def test_invalid_pmid_input() -> None:
    with pytest.raises(ValueError, match="invalid PMID"):
        get_pubmed_articles(["abc"])
    with pytest.raises(ValueError, match="invalid PMID"):
        get_pubmed_articles(["12345", "12a"])
    with pytest.raises(ValueError, match="list"):
        get_pubmed_articles("12345")  # type: ignore[arg-type]


def test_empty_pmid_list_skips_network() -> None:
    with patch("ecd_research.tools.pubmed._get") as mock_get:
        assert get_pubmed_articles([]) == []
        mock_get.assert_not_called()
