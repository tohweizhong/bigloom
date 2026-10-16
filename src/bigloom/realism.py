"""Mechanical realism readings for BigLoom output: repeated sentences, header repeats, cut words, thin pages.

The readings mask figures and world names, so one template filled with different numbers counts
as one repeated sentence. They read text as a person sees it, and they call no model.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.models import ArtifactIR
    from worldloom.world import World

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_FACT_REF = re.compile(r"\{\{fact:[^}]+\}\}")
_NUMBER = re.compile(r"\d[\d,.]*")
MIN_SENTENCE_WORDS = 4


def world_names(world: World) -> list[str]:
    """Return the names a reader meets in a world, longest first, so that masking replaces whole names."""
    pools: Iterable[object] = (
        *world.business_units, *world.people, *world.systems, *world.services, *world.sites, *world.categories,
    )
    names = {str(getattr(item, "name", "")) for item in pools} | {world.company.name}
    return sorted((n for n in names if n), key=len, reverse=True)


def mask(sentence: str, names: Sequence[str] = ()) -> str:
    """Replace fact references, figures, and world names with placeholders."""
    text = _FACT_REF.sub("<n>", sentence)
    for name in names:
        if name in text:
            text = text.replace(name, "<e>")
    return _NUMBER.sub("<n>", text).strip()


def split_sentences(text: str) -> list[str]:
    """Split prose into sentences of at least MIN_SENTENCE_WORDS words."""
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if len(s.split()) >= MIN_SENTENCE_WORDS]


def document_sentences(world: World, ir: ArtifactIR) -> list[str]:
    """Return the masked sentences of one narrated WorldLoom document."""
    names = world_names(world)
    return [mask(s, names) for sec in ir.sections if sec.body for s in split_sentences(sec.body)]


def repeated_sentence_rate(sentences: Sequence[str]) -> float:
    """Return the share of sentences whose text occurs more than once in the sequence."""
    if not sentences:
        return 0.0
    counts = Counter(sentences)
    return sum(v for v in counts.values() if v > 1) / len(sentences)
