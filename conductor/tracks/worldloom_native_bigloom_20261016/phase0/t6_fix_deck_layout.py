"""Phase 0 follow-up, T6: fix broken placeholder sizes in the WorldLoom enterprise deck template.

The enterprise PPTX template gives title and body placeholders a width of 16 in and a
height of 0 on a 13.33 in slide, so PowerPoint draws titles off the slide. This script
sets valid sizes on every layout and slide placeholder whose size is not valid.

Run from the BigLoom root after t4_post_render.py:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t6_fix_deck_layout.py
"""

from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Inches

SRC = Path("runs/phase0/t4/target-art-0010-exec-committee-summary.pptx")
OUT = Path("runs/phase0/t6/target-art-0010-exec-committee-summary.pptx")
MARGIN = Inches(0.6)
TITLES = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE}
FOOTERS = {PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.SLIDE_NUMBER}


def invalid(shape, width: int) -> bool:
    """Return True when a placeholder has no height or is wider than the slide."""
    return not shape.height or not shape.width or shape.left + shape.width > width


def fix_deck(data: bytes) -> tuple[bytes, list[str]]:
    """Set valid sizes on broken layout placeholders. Return the new bytes and a change log."""
    prs = Presentation(BytesIO(data))
    w, h = prs.slide_width, prs.slide_height
    inner = w - 2 * MARGIN
    log: list[str] = []
    containers = [(f"layout {i}", lay) for i, lay in enumerate(prs.slide_layouts)]
    containers += [(f"slide {i}", sl) for i, sl in enumerate(prs.slides, 1)]
    for where, container in containers:
        for ph in container.placeholders:
            if not invalid(ph, w):
                continue
            kind = ph.placeholder_format.type
            if kind in TITLES:
                ph.left, ph.top, ph.width, ph.height = MARGIN, Inches(0.35), inner, Inches(1.0)
            elif kind == PP_PLACEHOLDER.DATE:
                ph.left, ph.top, ph.width, ph.height = MARGIN, h - Inches(0.55), Inches(3.0), Inches(0.35)
            elif kind == PP_PLACEHOLDER.FOOTER:
                ph.left, ph.top, ph.width, ph.height = (w - Inches(6.0)) // 2, h - Inches(0.55), Inches(6.0), Inches(0.35)
            elif kind == PP_PLACEHOLDER.SLIDE_NUMBER:
                ph.left, ph.top, ph.width, ph.height = w - MARGIN - Inches(1.5), h - Inches(0.55), Inches(1.5), Inches(0.35)
            else:
                ph.left, ph.top, ph.width, ph.height = MARGIN, Inches(1.5), inner, h - Inches(2.2)
            log.append(f"{where} {kind}")
    out = BytesIO()
    prs.save(out)
    return out.getvalue(), log


def main() -> int:
    fixed, log = fix_deck(SRC.read_bytes())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(fixed)
    prs = Presentation(BytesIO(fixed))
    bad = [
        (i, sh.name)
        for i, s in enumerate(prs.slides, 1)
        for sh in s.shapes
        if sh.has_text_frame and invalid(sh, prs.slide_width)
    ]
    print(json.dumps({"changed": len(log), "first_changes": log[:6], "slides": len(prs.slides), "broken_after": bad}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
