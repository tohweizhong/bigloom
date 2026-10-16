"""Phase 0, T3: check that a natural question ranks the target and its trap in positions 1 to 3.

Run from the BigLoom root:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t3_ranking.py
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import replace
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from worldloom.evaluate.bm25 import Bm25
from worldloom.evaluate.tfidf import TfIdf
from worldloom.models import ArtifactSection, Cell, Column, Row, Table
from worldloom.narrative.composer import measure_noun
from worldloom.native_artifacts import inspect_artifact
from worldloom.world import World

CORPUS = Path("runs/phase0/corpus")
OUT = Path("runs/phase0/t3")
TARGETS = {"ART-0003": "docx", "ART-0007": "pdf", "ART-0010": "pptx", "ART-0002": "xlsx"}
TOP_K = 3


def evidence(label: str, value: str) -> ArtifactSection:
    """Return one BigLoom table section that holds one value."""
    table = Table(
        key="bigloom-evidence",
        title=label.capitalize(),
        columns=[Column(key="measure", label="Measure"), Column(key="value", label="Value")],
        rows=[Row(key="r1", label=label, cells={"measure": Cell(value=label), "value": Cell(value=value)})],
    )
    return ArtifactSection(heading=label.capitalize(), table=table)


def text_of(payload: bytes, ext: str) -> str:
    """Return the readable text of one rendered file."""
    if ext == "pdf":
        return "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(payload)).pages)
    units = inspect_artifact(payload, ext).units
    keep = [
        u.text
        for u in units
        if u.text
        and not u.locator.endswith(("/type", "/state"))
        and not u.text.startswith("=")
    ]
    return "\n".join(keep)


def money(rng: random.Random, ccy: str) -> str:
    return f"{ccy} {rng.randint(1, 9)},{rng.randint(100, 999)},{rng.randint(100, 999)}"


def staged_render(world: World, values: dict[str, tuple[str, str]]) -> list:
    """Render the world with one evidence section added to each target IR."""
    irs = list(world.artifact_irs)
    for i, ir in enumerate(irs):
        if ir.id in values:
            label, value = values[ir.id]
            sections = list(ir.sections)
            sections.insert(min(6, len(sections)), evidence(label, value))
            irs[i] = ir.model_copy(update={"sections": sections})
    return list(replace(world, _artifact_irs=tuple(irs)).render("docx", "pdf", "pptx", "xlsx")._rendered)


def main() -> int:
    rng = random.Random(7)
    world = World.load(CORPUS)
    ccy = world.company.currency or "SGD"
    facts = {f.id: f for f in world.facts}
    irs = {ir.id: ir for ir in world.artifact_irs}
    labels: dict[str, str] = {}
    for art_id in TARGETS:
        kinds = [facts[f].kind for f in irs[art_id].fact_ids() if f in facts]
        nouns = [measure_noun(k) for k in kinds if measure_noun(k)]
        labels[art_id] = f"approved {nouns[0]} reserve" if nouns else "approved reserve"
    golden = {a: (labels[a], money(rng, ccy)) for a in TARGETS}
    canary = {a: (labels[a], money(rng, ccy)) for a in TARGETS}

    first = staged_render(world, golden)
    second = staged_render(world, canary)
    docs: list[tuple[str, str, str]] = []  # (role, art_id, text)
    OUT.mkdir(parents=True, exist_ok=True)
    for art_id, ext in TARGETS.items():
        main_file = next(r for r in first if r.artifact_id == art_id and r.path.endswith("." + ext) and "/revisions/" not in r.path)
        if ext == "docx":
            trap_file = next(r for r in second if r.artifact_id == art_id and "/revisions/" in r.path and "-v0.1." in r.path)
        else:
            trap_file = next(r for r in second if r.artifact_id == art_id and r.path.endswith("." + ext) and "/revisions/" not in r.path)
        (OUT / f"target-{Path(main_file.path).name}").write_bytes(main_file.payload)
        (OUT / f"trap-{Path(trap_file.path).name}").write_bytes(trap_file.payload)
        docs.append(("target", art_id, text_of(main_file.payload, ext)))
        docs.append(("trap", art_id, text_of(trap_file.payload, Path(trap_file.path).suffix.lstrip("."))))

    texts = [d[2] for d in docs]
    bm25, tfidf = Bm25(texts), TfIdf(texts)
    report = {}
    for art_id, ext in TARGETS.items():
        ir = irs[art_id]
        periods = [facts[f].period for f in ir.fact_ids() if f in facts and facts[f].period]
        period = max(set(periods), key=periods.count) if periods else ""
        question = f"What is the {labels[art_id]} in the {ir.title} for {period}?"
        row: dict[str, object] = {"question": question}
        for name, engine in (("bm25", bm25), ("tfidf", tfidf)):
            order = [idx for idx, _ in engine.rank(question, limit=len(texts))]
            pos = {f"{docs[i][0]}": order.index(i) + 1 for i in range(len(docs)) if docs[i][1] == art_id and i in order}
            row[name] = pos
        row["pass"] = any(
            all(p <= TOP_K for p in row[n].values()) and len(row[n]) == 2 for n in ("bm25", "tfidf")  # type: ignore[union-attr]
        )
        report[art_id + " " + ext] = row
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
