"""Tests for PubMed Central full-text fetch and parsing."""

from __future__ import annotations

from pathlib import Path

from ecd_research.tools.pmc import (
    build_fulltext_corpus,
    parse_pmc_xml,
    resolve_pmcid,
)

FIXTURE = Path(__file__).parent / "fixtures" / "pmc_41562816.xml"


def test_parse_pmc_fixture() -> None:
    xml_text = FIXTURE.read_text(encoding="utf-8")
    doc = parse_pmc_xml(xml_text, pmid="41562816")
    assert doc is not None
    assert doc.pmid == "41562816"
    assert doc.pmcid == "PMC12821489"
    assert doc.doi == "10.3390/reports9010018"
    assert doc.abstract_limited is False
    assert len(doc.sections) >= 3
    assert "SARA" in doc.raw_text or any("SARA" in s.text for s in doc.sections)


def test_build_fulltext_corpus_prioritizes_case_sections() -> None:
    xml_text = FIXTURE.read_text(encoding="utf-8")
    doc = parse_pmc_xml(xml_text, pmid="41562816")
    assert doc is not None
    corpus = build_fulltext_corpus(doc)
    assert "dabrafenib" in corpus.lower() or "trametinib" in corpus.lower()
    assert len(corpus) > 500


def test_resolve_pmcid_from_fixture_xml_parsing_only() -> None:
    # Unit test only — live resolve tested separately if needed
    xml_text = FIXTURE.read_text(encoding="utf-8")
    doc = parse_pmc_xml(xml_text)
    assert doc is not None
    assert doc.pmcid.startswith("PMC")
