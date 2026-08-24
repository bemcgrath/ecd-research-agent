"""Tests for PubMed citation neighborhood (ELink)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ecd_research.tools.citations import (
    expand_citation_neighborhood,
    find_citing_articles,
    find_pubmed_references,
)


def _elink_payload(linkname: str, ids: list[str]) -> dict:
    return {
        "linksets": [
            {
                "linksetdbs": [
                    {"dbto": "pubmed", "linkname": linkname, "links": ids},
                ]
            }
        ]
    }


def test_find_pubmed_references_parses_elink_order() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = _elink_payload(
        "pubmed_pubmed_refs", ["111", "222", "111", "333"]
    )
    with patch("ecd_research.tools.citations._get", return_value=mock_response):
        pmids = find_pubmed_references("41562816", max_results=10)
    assert pmids == ["111", "222", "333"]


def test_find_citing_articles_caps_results() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = _elink_payload(
        "pubmed_pubmed_citedin", ["1", "2", "3", "4"]
    )
    with patch("ecd_research.tools.citations._get", return_value=mock_response):
        pmids = find_citing_articles("41562816", max_results=2)
    assert pmids == ["1", "2"]


def test_expand_citation_neighborhood_excludes_seeds_and_dedupes() -> None:
    def fake_refs(pmid: str, *, max_results: int = 50) -> list[str]:
        if pmid == "100":
            return ["100", "200", "300"]
        return ["300", "400"]

    def fake_cites(pmid: str, *, max_results: int = 50) -> list[str]:
        return ["200", "500"]

    with (
        patch("ecd_research.tools.citations.find_pubmed_references", side_effect=fake_refs),
        patch("ecd_research.tools.citations.find_citing_articles", side_effect=fake_cites),
    ):
        neighbors, audit = expand_citation_neighborhood(
            ["100", "100"],
            max_per_seed=10,
            max_total=10,
        )

    assert "100" not in neighbors
    assert neighbors == ["200", "300", "500"]
    assert audit["100"] == ["200", "300", "500"]


def test_invalid_pmid_raises() -> None:
    with pytest.raises(ValueError, match="invalid PMID"):
        find_pubmed_references("not-a-pmid")
