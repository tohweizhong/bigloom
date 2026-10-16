"""Phase 0, T3b: test workbook question forms against the files that T3 saved.

Run from the BigLoom root after t3_ranking.py:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t3b_workbook_questions.py
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from worldloom.evaluate.bm25 import Bm25
from worldloom.evaluate.tfidf import TfIdf
from worldloom.native_artifacts import inspect_artifact

FILES = Path("runs/phase0/t3")
TARGET = "target-art-0002-month-end-model.xlsx"
TRAP = "trap-art-0002-month-end-model.xlsx"
QUESTIONS = (
    "What is the approved revenue reserve in the Ironvale Singapore Pte Ltd — Month-End Model for 2026-03?",
    "On the Approved revenue reserve sheet of the 2026-03 Month-End Model workbook, what is the approved revenue reserve?",
    "In the Month-End Model workbook for 2026-03, what value does the Approved revenue reserve sheet show?",
    "What approved revenue reserve does the Month-End Model workbook record?",
)


def text_of(path: Path) -> str:
    """Return the readable text of one file, without workbook type markers and formulas."""
    ext = path.suffix.lstrip(".")
    data = path.read_bytes()
    if ext == "pdf":
        return "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(data)).pages)
    units = inspect_artifact(data, ext).units
    return "\n".join(
        u.text for u in units if u.text and not u.locator.endswith(("/type", "/state")) and not u.text.startswith("=")
    )


def main() -> int:
    paths = sorted(FILES.iterdir())
    names = [p.name for p in paths]
    texts = [text_of(p) for p in paths]
    engines = {"bm25": Bm25(texts), "tfidf": TfIdf(texts)}
    for question in QUESTIONS:
        row = []
        for name, engine in engines.items():
            order = [i for i, _ in engine.rank(question, limit=len(texts))]
            t = order.index(names.index(TARGET)) + 1 if names.index(TARGET) in order else None
            r = order.index(names.index(TRAP)) + 1 if names.index(TRAP) in order else None
            row.append(f"{name} target={t} trap={r}")
        print(f"{' | '.join(row)} | {question}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
