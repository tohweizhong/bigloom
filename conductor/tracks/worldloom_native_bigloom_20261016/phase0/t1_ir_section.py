"""Phase 0, T1: add a BigLoom table section to one WorldLoom IR and render it.

Run from the BigLoom root:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t1_ir_section.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from worldloom.models import ArtifactSection, Cell, Column, Row, Table
from worldloom.native_artifacts import inspect_artifact
from worldloom.world import World

CORPUS = Path("runs/phase0/corpus")
OUT = Path("runs/phase0/t1")
TARGET_IDS = ("ART-0003", "ART-0010")
GOLDEN = "SGD 7,413,286"
LABEL = "Approved programme reserve"


def evidence_section() -> ArtifactSection:
    """Return one BigLoom-owned table section that holds the golden value."""
    table = Table(
        key="bigloom-evidence",
        title="Programme reserve position",
        columns=[Column(key="measure", label="Measure"), Column(key="value", label="Value")],
        rows=[
            Row(
                key="r1",
                label=LABEL,
                cells={"measure": Cell(value=LABEL), "value": Cell(value=GOLDEN)},
            )
        ],
    )
    return ArtifactSection(heading="Programme reserve position", table=table)


def main() -> int:
    world = World.load(CORPUS)
    irs = list(world.artifact_irs)
    for idx, ir in enumerate(irs):
        if ir.id not in TARGET_IDS:
            continue
        sections = list(ir.sections)
        insert_at = min(6, len(sections))
        sections.insert(insert_at, evidence_section())
        irs[idx] = ir.model_copy(update={"sections": sections})
        print(f"IR {ir.id} '{ir.title}': {len(ir.sections)} sections, inserted at {insert_at}")

    staged = replace(world, _artifact_irs=tuple(irs))
    rendered = staged.render("docx", "pdf", "pptx")
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {}
    for item in rendered._rendered:
        if item.artifact_id not in TARGET_IDS:
            continue
        name = Path(item.path).name
        (OUT / name).write_bytes(item.payload)
        ext = name.rsplit(".", 1)[-1]
        if ext in ("docx", "pptx"):
            snap = inspect_artifact(item.payload, ext)
            hits = [(i, u.locator) for i, u in enumerate(snap.units, 1) if GOLDEN in u.text]
            results[name] = {"bytes": len(item.payload), "units": len(snap.units), "hits": hits}
        elif ext == "pdf":
            reader = PdfReader(BytesIO(item.payload))
            pages = [p.extract_text() or "" for p in reader.pages]
            hits = [i for i, t in enumerate(pages, 1) if GOLDEN.replace(" ", "") in t.replace(" ", "").replace("\n", "")]
            results[name] = {"bytes": len(item.payload), "pages": len(pages), "hit_pages": hits}
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
