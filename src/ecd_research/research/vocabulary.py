"""Configurable ECD domain vocabulary for search expansion."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

VOCAB_PATH = Path(__file__).resolve().parent.parent / "data" / "ecd_vocabulary.yaml"


@lru_cache(maxsize=1)
def load_vocabulary(path: str | None = None) -> dict[str, list[str]]:
    """Load vocabulary YAML. Categories map to term lists."""
    vocab_file = Path(path) if path else VOCAB_PATH
    raw: Any = yaml.safe_load(vocab_file.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"vocabulary root must be a mapping: {vocab_file}")
    cleaned: dict[str, list[str]] = {}
    for category, terms in raw.items():
        if not isinstance(terms, list):
            raise ValueError(f"category {category!r} must be a list of strings")
        cleaned[str(category)] = [str(t).strip() for t in terms if str(t).strip()]
    return cleaned


def all_terms(vocabulary: dict[str, list[str]] | None = None) -> list[str]:
    vocab = vocabulary or load_vocabulary()
    seen: set[str] = set()
    ordered: list[str] = []
    for terms in vocab.values():
        for term in terms:
            key = term.lower()
            if key not in seen:
                seen.add(key)
                ordered.append(term)
    return ordered
