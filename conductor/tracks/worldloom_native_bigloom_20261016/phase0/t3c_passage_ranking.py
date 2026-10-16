"""Phase 0, T3c: rank passages, not whole files. A file takes the position of its best passage.

Run from the BigLoom root after t3_ranking.py:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t3c_passage_ranking.py
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from worldloom.evaluate.bm25 import Bm25
from worldloom.evaluate.tfidf import TfIdf
from worldloom.native_artifacts import inspect_artifact

FILES = Path("runs/phase0/t3")
QUESTIONS = Path("runs/phase0/t3_out.txt")
TOP_K = 3
WORDS_PER_CHUNK = 250


def chunk_words(lines: list[str]) -> list[str]:
    """Group lines into passages of about WORDS_PER_CHUNK words."""
    out: list[str] = []
    buf: list[str] = []
    count = 0
    for line in lines:
        buf.append(line)
        count += len(line.split())
        if count >= WORDS_PER_CHUNK:
            out.append("\n".join(buf))
            buf, count = [], 0
    if buf:
        out.append("\n".join(buf))
    return out


def passages_of(path: Path) -> list[str]:
    """Split one file into passages: a page for PDF, a slide for PPTX, a sheet for XLSX, word chunks for DOCX."""
    ext = path.suffix.lstrip(".")
    data = path.read_bytes()
    if ext == "pdf":
        return [p.extract_text() or "" for p in PdfReader(BytesIO(data)).pages]
    units = [
        u for u in inspect_artifact(data, ext).units
        if u.text and not u.locator.endswith(("/type", "/state")) and not u.text.startswith("=")
    ]
    if ext in ("pptx", "xlsx"):
        groups: OrderedDict[str, list[str]] = OrderedDict()
        for u in units:
            groups.setdefault(u.locator.split("/")[0], []).append(u.text)
        result: list[str] = []
        for lines in groups.values():
            result.extend(chunk_words(lines))
        return result
    return chunk_words([u.text for u in units])


def main() -> int:
    questions = json.loads(QUESTIONS.read_text())
    paths = sorted(FILES.iterdir())
    owners: list[str] = []
    texts: list[str] = []
    for p in paths:
        for passage in passages_of(p):
            owners.append(p.name)
            texts.append(passage)
    engines = {"bm25": Bm25(texts), "tfidf": TfIdf(texts)}
    print(f"{len(texts)} passages from {len(paths)} files")
    for key, row in questions.items():
        art = key.split()[0].lower()
        target = next(n for n in (p.name for p in paths) if n.startswith("target-" + art))
        trap = next(n for n in (p.name for p in paths) if n.startswith("trap-" + art))
        line = []
        ok = False
        for name, engine in engines.items():
            file_order: list[str] = []
            for idx, _ in engine.rank(row["question"], limit=len(texts)):
                if owners[idx] not in file_order:
                    file_order.append(owners[idx])
            t = file_order.index(target) + 1 if target in file_order else None
            r = file_order.index(trap) + 1 if trap in file_order else None
            ok = ok or (t is not None and r is not None and t <= TOP_K and r <= TOP_K)
            line.append(f"{name} target={t} trap={r}")
        print(f"{key:14} | {' | '.join(line)} | pass={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
