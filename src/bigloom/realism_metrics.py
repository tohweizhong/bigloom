"""The realism metric vector for the realism improvement loop (no model calls).

Moved from the round 0 scratch script of the WorldLoom session (`realism_metrics.py`). The
text readers, the sentence rule, and the defect patterns are the same, so round 0 and later
rounds are comparable when both run through this module. Two changes:

1. Sentence reuse across files compares different documents only. Size twins (the same
   document type at two sizes) share their template sentences, so they do not count. A
   BigLoom `manifest.jsonl` names the document type of each target. Without a manifest, two
   files with a sentence Jaccard of `TWIN_JACCARD` or more are twins.
2. The output holds `grader_sha256`, the digest of this file. A loop round must not change
   the grader, so each receipt records the digest.

Rates are per 1000 words, so file size does not change them.
"""

from __future__ import annotations

import collections
import hashlib
import re
import subprocess
import zlib
from pathlib import Path
from typing import Any

SUPPORTED = (".pdf", ".docx", ".pptx")
#: Two files are size twins when this share of their sentences is the same (Jaccard).
TWIN_JACCARD = 0.8
MIN_SENTENCE_WORDS = 6

#: WorldLoom provenance IDs. A real agency report does not cite its generator's ledger keys.
WL_ID = re.compile(r"\b(?:CO-\d{3,}-[A-Z]+-ART|FACT|EV|ART|ENT|EVT|IR)-\d{3,}\b")
#: Any ID-shaped token, so the WorldLoom rate can be read against the ID density of real files.
ANY_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{3,}\b")
#: Retail words that do not belong to a public-sector agency. Real GovTech pages name "App Store" and "Play Store".
RETAIL = re.compile(
    r"\b(?:SKUs?|(?<!app )(?<!play )stores?|merchandis\w*|shrinkage|basket size|footfall|same-store|point of sale|POS)\b",
    re.IGNORECASE,
)
#: Commercial profit and loss terms. A statutory board reports income and expenditure.
COMMERCIAL = re.compile(r"\b(?:gross profit|gross margin|operating margin|EBITDA|sales volume)\b", re.IGNORECASE)
_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_DATE = re.compile(r"\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* ((?:19|20)\d{2})\b")
_DOC_DATE = re.compile(
    r"\b(?:Date(?: of this [a-z]+)?|Dated|As at)\s*:?\s*(\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (?:19|20)\d{2})"
)


def grader_digest() -> str:
    """Return the SHA-256 digest of this module, the grader identity for a loop receipt."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def text_of(path: Path) -> str:
    """Return the text a reader sees: `pdftotext -layout` for PDF, paragraphs for DOCX, text frames for PPTX."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True, check=False).stdout
    if suffix == ".docx":
        import docx

        return "\n".join(par.text for par in docx.Document(str(path)).paragraphs)
    if suffix == ".pptx":
        import pptx

        out: list[str] = []
        for slide in pptx.Presentation(str(path)).slides:
            out.extend(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)
        return "\n".join(out)
    return ""


def sentences(text: str) -> list[str]:
    """Return sentences of at least six words, with figures masked as "#"."""
    flat = re.sub(r"\s+", " ", text)
    out: list[str] = []
    for part in re.split(r"(?<=[.!?])\s+", flat):
        masked = re.sub(r"\d[\d,.%]*", "#", part).strip()
        if len(masked.split()) >= MIN_SENTENCE_WORDS:
            out.append(masked)
    return out


def _ymd(text: str) -> tuple[int, int, int] | None:
    m = _DATE.search(text)
    return (int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1))) if m else None


def defects(text: str) -> dict[str, Any]:
    """Return the countable defects of one text, per 1000 words.

    A date counts as "after the document" only against the document's own stated date.
    """
    words = max(len(text.split()), 1)

    def per_k(n: int) -> float:
        return round(1000 * n / words, 2)

    doc = _DOC_DATE.search(text)
    doc_ymd = _ymd(doc.group(1)) if doc else None
    dates = [(int(y), _MONTHS[mo.lower()], int(d)) for d, mo, y in _DATE.findall(text)]
    return {
        "wl_id_per_k": per_k(len(WL_ID.findall(text))),
        "any_id_per_k": per_k(len(ANY_ID.findall(text))),
        "retail_per_k": per_k(len(RETAIL.findall(text))),
        "commercial_per_k": per_k(len(COMMERCIAL.findall(text))),
        "doc_date": doc.group(1) if doc else None,
        "dates_after_doc_date": sum(1 for x in dates if doc_ymd and x > doc_ymd),
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def cross_document_reuse(
    sets: dict[str, set[str]], kinds: dict[str, str] | None = None
) -> tuple[float, list[tuple[str, str]]]:
    """Return the share of sentences that also occur in a different document, and the twin pairs.

    Two files are size twins when `kinds` gives them the same document type, or when their
    sentence Jaccard is `TWIN_JACCARD` or more. A sentence shared only with a twin does not
    count as reuse.
    """
    names = sorted(sets)
    kinds = kinds or {}

    def twin(a: str, b: str) -> bool:
        if a in kinds and b in kinds:
            return kinds[a] == kinds[b]
        return _jaccard(sets[a], sets[b]) >= TWIN_JACCARD

    twins = [(a, b) for i, a in enumerate(names) for b in names[i + 1 :] if twin(a, b)]
    twin_of = collections.defaultdict(set)
    for a, b in twins:
        twin_of[a].add(b)
        twin_of[b].add(a)
    total = shared = 0
    for name in names:
        others = [sets[o] for o in names if o != name and o not in twin_of[name]]
        for sentence in sets[name]:
            total += 1
            if any(sentence in other for other in others):
                shared += 1
    return round(shared / max(total, 1), 3), twins


def _manifest_kinds(folder: Path) -> dict[str, str]:
    """Return target file name to document type, from a BigLoom manifest when one exists."""
    import json

    path = folder / "manifest.jsonl"
    if not path.is_file():
        return {}
    kinds: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row.get("document_type"):
                kinds[Path(row["target_file"]).name] = row["document_type"]
    return kinds


def metrics(folder: Path) -> dict[str, Any]:
    """Return the metric vector for every supported file directly in `folder` or its `large/` folder."""
    roots = [folder, folder / "large"]
    files = sorted({f for root in roots if root.is_dir() for f in root.iterdir() if f.suffix.lower() in SUPPORTED})
    per: list[dict[str, Any]] = []
    sets: dict[str, set[str]] = {}
    for f in files:
        text = text_of(f)
        found = sentences(text)
        sets[f.name] = set(found)
        counts = collections.Counter(found)
        within = sum(n for n in counts.values() if n > 1) / max(len(found), 1)
        openers = collections.Counter(" ".join(s.split()[:3]) for s in found)
        top_open = openers.most_common(1)[0][1] / len(found) if found else 0.0
        raw = f.stat().st_size
        text_bytes = text.encode()
        per.append({
            "file": f.name, "mb": round(raw / 1e6, 2), "words": len(text.split()),
            "words_per_mb": round(len(text.split()) / max(raw / 1e6, 1e-9)),
            "sentences": len(found), "unique_sentences": len(counts),
            "within_file_repeat": round(within, 3), "top_opener_share": round(top_open, 3),
            "text_gzip_ratio": round(len(zlib.compress(text_bytes, 9)) / max(len(text_bytes), 1), 3),
            **defects(text),
        })
    reuse, twins = cross_document_reuse(sets, _manifest_kinds(folder))
    every = collections.Counter(x for s in sets.values() for x in s)
    return {
        "grader_sha256": grader_digest(),
        "files": per,
        "cross_document_reuse": reuse,
        "size_twins": twins,
        "top_shared": [(n, x[:100]) for x, n in every.most_common(5) if n > 1],
    }


def summary(result: dict[str, Any]) -> dict[str, float]:
    """Return the mean of each per-file rate, plus cross-document reuse: the vector a round compares."""
    files = result["files"]
    keys = ("wl_id_per_k", "commercial_per_k", "retail_per_k", "within_file_repeat", "top_opener_share",
            "unique_sentences", "words_per_mb", "dates_after_doc_date")
    out = {k: round(sum(float(f[k]) for f in files) / len(files), 3) if files else 0.0 for k in keys}
    out["cross_document_reuse"] = result["cross_document_reuse"]
    return out
