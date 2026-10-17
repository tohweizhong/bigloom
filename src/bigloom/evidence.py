"""Test evidence that all formats share.

BigLoom writes no prose. It adds three things to a WorldLoom document:

1. A text fact: a small table section in a copy of the IR, before rendering.
2. An image fact: a chart picture in the rendered file, after rendering. The value is in
   the picture only, never in the file text.
3. Byte padding, so that each file reaches its target size.

This module holds the parts that all formats share: the text fact section, the chart
picture, and padding for OOXML packages. Each module in `bigloom.formats` holds the steps
for one format.
"""

from __future__ import annotations

import random
import zipfile
from collections.abc import Iterator, Sequence
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.models import ArtifactIR, ArtifactSection

EVIDENCE_KEY = "bigloom-evidence"
BALLAST_NAME = "customXml/bigloom-ballast.bin"
_CHUNK = 1 << 20


# ---------------------------------------------------------------------------
# Text fact in the IR
# ---------------------------------------------------------------------------


def evidence_section(heading: str, rows: Sequence[tuple[str, str]]) -> ArtifactSection:
    """Return one table section with (measure, value) rows."""
    from worldloom.models import ArtifactSection, Cell, Column, Row, Table

    table = Table(
        key=EVIDENCE_KEY,
        title=heading,
        columns=[Column(key="measure", label="Measure"), Column(key="value", label="Value")],
        rows=[
            Row(key=f"r{i}", label=label, cells={"measure": Cell(value=label), "value": Cell(value=value)})
            for i, (label, value) in enumerate(rows, 1)
        ],
    )
    return ArtifactSection(heading=heading, table=table)


def evidence_position(ir: ArtifactIR, depth: int) -> int:
    """Return where the text fact section goes: at `depth`, but never after the prose body.

    A document ends with sign-off and appendix sections (approval tables, hidden supporting
    facts). A person expects a figure inside the body, so the section goes before them.
    """
    body = [i for i, sec in enumerate(ir.sections) if not sec.hidden and sec.body]
    end = body[-1] + 1 if body else len(ir.sections)
    return min(depth, end)


def with_evidence(ir: ArtifactIR, section: ArtifactSection, *, depth: int = 6, title_suffix: str = "") -> ArtifactIR:
    """Return a copy of the IR with the section inserted at `evidence_position(ir, depth)`."""
    sections = list(ir.sections)
    sections.insert(evidence_position(ir, depth), section)
    update: dict[str, object] = {"sections": sections}
    if title_suffix:
        update["title"] = f"{ir.title}{title_suffix}"
    return ir.model_copy(update=update)


# ---------------------------------------------------------------------------
# Image fact
# ---------------------------------------------------------------------------


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("DejaVuSans.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fact_chart_png(title: str, categories: Sequence[str], value_label: str, seed: int, peak: int = 0) -> bytes:
    """Draw a bar chart. The bar at index `peak` is the tallest and carries `value_label`.

    `value_label` is the image fact. Other bar heights come from a seeded generator, so the
    same seed draws the same chart.
    """
    if not categories:
        raise ValueError("A chart needs at least one category.")
    rng = random.Random(seed)
    cats = [c[:18] for c in categories][:6]
    peak = peak % len(cats)
    heights = [rng.randint(180, 520) for _ in cats]
    heights[peak] = 640
    img = Image.new("RGB", (1600, 1000), "white")
    draw = ImageDraw.Draw(img)
    draw.text((80, 40), title[:80], fill=(20, 20, 20), font=_font(40))
    base_y = 860
    slot = 1400 // len(cats)
    for i, (cat, h) in enumerate(zip(cats, heights, strict=True)):
        x0 = 120 + i * slot + slot // 6
        x1 = x0 + slot * 2 // 3
        draw.rectangle([x0, base_y - h, x1, base_y], fill=(0, 84, 147) if i != peak else (200, 16, 46))
        draw.text((x0, base_y + 16), cat, fill=(40, 40, 40), font=_font(26))
        if i == peak:
            draw.text((x0, base_y - h - 56), value_label, fill=(20, 20, 20), font=_font(40))
    draw.line([100, base_y, 1520, base_y], fill=(0, 0, 0), width=4)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Byte padding
# ---------------------------------------------------------------------------


def random_chunks(total: int, seed: int) -> Iterator[bytes]:
    """Yield seeded random bytes in chunks of up to 1 MiB, `total` bytes in all."""
    rng = random.Random(seed)
    left = total
    while left > 0:
        step = min(left, _CHUNK)
        yield rng.randbytes(step)
        left -= step


def _pad_ooxml_once(data: bytes, need: int, seed: int) -> bytes:
    buf = BytesIO(data)
    with zipfile.ZipFile(buf, "a", zipfile.ZIP_STORED, allowZip64=True) as zf:
        info = zipfile.ZipInfo(BALLAST_NAME, date_time=(2026, 1, 1, 0, 0, 0))
        with zf.open(info, "w", force_zip64=need > (1 << 31)) as fh:
            for chunk in random_chunks(need, seed):
                fh.write(chunk)
    return buf.getvalue()


def pad_ooxml(data: bytes, target_bytes: int, seed: int) -> bytes:
    """Add an unreferenced, stored ZIP member so that the package reaches `target_bytes`.

    Office applications ignore a part that no relationship names. The member holds seeded
    random bytes, so it does not compress and the same seed gives the same file. The result
    is at least `target_bytes` long and at most a few hundred bytes longer.
    """
    if len(data) >= target_bytes:
        return data
    out = _pad_ooxml_once(data, target_bytes - len(data), seed)
    overhead = len(out) - target_bytes
    if overhead > 0:
        out = _pad_ooxml_once(data, max(1, target_bytes - len(data) - overhead), seed)
    return out
