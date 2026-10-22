"""Mechanical realism readings for BigLoom output: repeated sentences, header repeats, cut words, thin pages.

`file_findings` runs the readings on one rendered file. The qualification gate fails a file
for each finding.

The readings mask figures and world names, so one template filled with different numbers counts
as one repeated sentence. They read text as a person sees it, and they call no model.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.models import ArtifactIR
    from worldloom.native_artifacts import NativeSnapshot
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


def split_sentences(text: str, min_words: int = MIN_SENTENCE_WORDS) -> list[str]:
    """Split prose into sentences of at least `min_words` words."""
    return [s.strip() for s in _SENTENCE_SPLIT.split(text or "") if len(s.split()) >= min_words]


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


# ---------------------------------------------------------------------------
# File readings for the qualification gate
# ---------------------------------------------------------------------------

#: A file fails when more than this share of its prose sentences repeat.
MAX_REPEATED_SENTENCE_RATE = 0.2
#: The gate reads sentences of at least this many words. Shorter lines are table cells.
GATE_SENTENCE_WORDS = 6
#: A file fails when one three-word opener starts more than this share of its sentences.
MAX_OPENER_SHARE = 0.25
MIN_OPENER_COUNT = 5
#: A file fails when one line of at least four words occurs this many times, outside running heads.
HEADER_REPEAT_COUNT = 6
#: A file fails when it holds this many words broken across lines with no hyphen.
CUT_WORD_LIMIT = 3
#: A PDF page with fewer words than this, and no picture, is thin. The first and last pages are exempt.
THIN_PAGE_WORDS = 40
_CUT_WORD = re.compile(r"[A-Za-z]{4,}\n([a-z]{1,2})(?=\n|$)")


@dataclass(frozen=True)
class Finding:
    """One realism defect in one file."""

    code: str
    detail: str


def running_heads(pages: Sequence[str]) -> set[str]:
    """Return the lines that occur on at least half of the pages: running heads and footers."""
    if len(pages) < 4:
        return set()
    counts: Counter[str] = Counter()
    for page in pages:
        counts.update({line.strip() for line in page.splitlines() if line.strip()})
    return {line for line, n in counts.items() if n >= len(pages) / 2}


def _lines_and_prose(snap: NativeSnapshot) -> tuple[list[str], str, list[str]]:
    """Return the body lines, the prose text, and the page texts (PDF only) of a file."""
    if snap.format == "pdf":
        from .qualify import pdf_pages

        pages = pdf_pages(snap)
        # Read prose and headings only, as for DOCX paragraphs. Fall back to all text.
        # Skip the cover: the WorldLoom PDF cover quotes the first section as a summary.
        prose_pages = list(getattr(snap, "prose_pages", ()) or pages)[1:] or pages
        heads = running_heads(prose_pages)
        lines = [
            line.strip() for page in prose_pages for line in page.splitlines() if line.strip() and line.strip() not in heads
        ]
        return lines, " ".join(lines), pages
    if snap.format == "pptx":
        slides = [u.text for u in snap.units if u.locator.endswith("/text") and "/shape:" not in u.locator and u.text.strip()]
        notes = [u.text for u in snap.units if u.locator.endswith("/notes") and u.text.strip()]
        heads = running_heads(slides)
        lines = [line.strip() for part in (*slides, *notes) for line in part.splitlines() if line.strip() and line.strip() not in heads]
        return lines, " ".join(lines), []
    if snap.format == "xlsx":
        sheets: dict[str, list[str]] = {}
        for u in snap.units:
            if "/cell:" in u.locator and not u.locator.endswith("/type") and not u.text.startswith("=") and u.text.strip():
                sheets.setdefault(u.locator.split("/")[0], []).append(u.text.strip())
        heads = running_heads(["\n".join(rows) for rows in sheets.values()])
        lines = [cell for rows in sheets.values() for cell in rows if cell not in heads]
        prose_cells = [c for c in lines if c.endswith((".", "!", "?")) and len(c.split()) >= GATE_SENTENCE_WORDS]
        return prose_cells, " ".join(prose_cells), []
    paragraphs = [u.text.strip() for u in snap.units if u.locator.startswith("paragraph:") and u.text.strip()]
    return paragraphs, " ".join(paragraphs), []


def file_findings(snap: NativeSnapshot) -> list[Finding]:
    """Return the realism defects of one DOCX, PDF, PPTX, or XLSX file."""
    if snap.format not in ("docx", "pdf", "pptx", "xlsx"):
        return []
    lines, prose, pages = _lines_and_prose(snap)
    findings: list[Finding] = []
    sentences = [mask(s) for s in split_sentences(prose, GATE_SENTENCE_WORDS)]
    rate = repeated_sentence_rate(sentences)
    if rate > MAX_REPEATED_SENTENCE_RATE:
        top = Counter(sentences).most_common(1)[0][0]
        findings.append(Finding("repeated_sentences", f"{rate:.0%} of {len(sentences)} sentences repeat, for example: '{top[:90]}'."))
    if sentences:
        opener, count = Counter(" ".join(s.split()[:3]) for s in sentences).most_common(1)[0]
        if count >= MIN_OPENER_COUNT and count / len(sentences) > MAX_OPENER_SHARE:
            findings.append(Finding("template_openers", f"'{opener}' opens {count} of {len(sentences)} sentences."))
    repeats = Counter(line for line in lines if len(line.split()) >= 4)
    worst = [(line, n) for line, n in repeats.most_common(3) if n >= HEADER_REPEAT_COUNT]
    if worst:
        findings.append(Finding("header_repeats", f"'{worst[0][0][:90]}' occurs {worst[0][1]} times outside running heads."))
    if pages:
        cut = [m.group(0).replace("\n", "|") for page in pages for m in _CUT_WORD.finditer(page)]
        if len(cut) >= CUT_WORD_LIMIT:
            findings.append(Finding("cut_words", f"{len(cut)} words break across lines with no hyphen, for example {cut[:3]}."))
        thin = [
            i
            for i, page in enumerate(pages, 1)
            if 1 < i < len(pages) and len(page.split()) < THIN_PAGE_WORDS and not snap.metrics.get(f"images_page_{i}", 0)
        ]
        if thin:
            findings.append(Finding("thin_pages", f"Pages {thin} have fewer than {THIN_PAGE_WORDS} words and no picture."))
    return findings
