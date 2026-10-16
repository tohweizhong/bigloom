"""Phase 0, T1b: try a hidden BigLoom section and a profile whose appendix is "append".

Run from the BigLoom root:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t1b_hidden_section.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
from dataclasses import replace
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from worldloom.models import ArtifactSection, Cell, Column, Row, Table
from worldloom.native_artifacts import inspect_artifact
from worldloom.presentation import READER
from worldloom.recipe import with_presentation
from worldloom.world import World

CORPUS = Path("runs/phase0/corpus")
OUT = Path("runs/phase0/t1b")
TARGET_ID = "ART-0010"
GOLDEN = "SGD 7,413,286"
LABEL = "Approved programme reserve"


def hidden_section() -> ArtifactSection:
    """Return one hidden BigLoom table section that holds the golden value."""
    table = Table(
        key="bigloom-evidence",
        title="Programme reserve position",
        columns=[Column(key="measure", label="Measure"), Column(key="value", label="Value")],
        rows=[Row(key="r1", label=LABEL, cells={"measure": Cell(value=LABEL), "value": Cell(value=GOLDEN)})],
    )
    return ArtifactSection(heading="Programme reserve position", table=table, hidden=True)


def main() -> int:
    world = World.load(CORPUS)
    irs = list(world.artifact_irs)
    idx = next(i for i, ir in enumerate(irs) if ir.id == TARGET_ID)
    irs[idx] = irs[idx].model_copy(update={"sections": [*irs[idx].sections, hidden_section()]})
    profile = dataclasses.replace(READER, appendix="append")
    staged = replace(world, _artifact_irs=tuple(irs), _recipe=with_presentation(world.recipe, profile))
    rendered = staged.render("docx", "pdf", "pptx")
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {}
    for item in rendered._rendered:
        if item.artifact_id != TARGET_ID:
            continue
        name = Path(item.path).name
        (OUT / name).write_bytes(item.payload)
        ext = name.rsplit(".", 1)[-1]
        if ext in ("docx", "pptx"):
            snap = inspect_artifact(item.payload, ext)
            hits = [(i, u.locator) for i, u in enumerate(snap.units, 1) if GOLDEN in u.text]
            results[name] = {"units": len(snap.units), "hits": hits}
        else:
            pages = [p.extract_text() or "" for p in PdfReader(BytesIO(item.payload)).pages]
            hits = [i for i, t in enumerate(pages, 1) if GOLDEN.replace(" ", "") in t.replace(" ", "").replace("\n", "")]
            results[name] = {"pages": len(pages), "hit_pages": hits}
    print(json.dumps(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
