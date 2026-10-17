"""The shared contract for one target format.

`build.py` runs one pipeline for all formats: it resolves the world, chooses the documents,
plans the values and the questions, renders, and writes the manifest. A handler holds the
steps that differ by format: where the text fact goes, how the picture goes in, which file
is the trap, and how the file reaches its size.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal

from ..evidence import evidence_section, fact_chart_png, with_evidence

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.models import ArtifactIR

Format = Literal["docx", "xlsx", "pptx", "pdf"]
EVIDENCE_DEPTH = 6


@dataclass(frozen=True)
class Target:
    """One planned target file: the WorldLoom document and the values BigLoom adds to it."""

    file_id: str
    fmt: Format
    size_bytes: int
    ir_id: str
    artifact_type: str
    label: str
    chart_title: str
    chart_categories: tuple[str, ...]
    chart_peak: int
    text_question: str
    image_question: str
    text_golden: str
    text_canary: str
    image_golden: str
    image_canary: str

    @property
    def heading(self) -> str:
        return self.label.capitalize()

    @property
    def peak_name(self) -> str:
        return self.chart_categories[self.chart_peak]

    @property
    def caption(self) -> str:
        return f"Figure: {self.chart_title}"

    def chart(self, seed: int, value: str | None = None) -> bytes:
        """Return the chart picture. The peak bar carries `value`, or the image golden value."""
        return fact_chart_png(
            self.chart_title, self.chart_categories, value or self.image_golden, seed, peak=self.chart_peak
        )


class FormatHandler:
    """The steps for one format. Subclasses change only the steps that differ."""

    fmt: ClassVar[Format]
    #: The trap is the draft main file, so its title carries this suffix.
    draft_suffix: ClassVar[str] = " (draft)"

    def golden_ir(self, t: Target, ir: ArtifactIR) -> ArtifactIR:
        """Return a copy of the IR with the text fact section at unit 6 or deeper."""
        return with_evidence(ir, evidence_section(t.heading, [(t.heading, t.text_golden)]), depth=EVIDENCE_DEPTH)

    def canary_ir(self, t: Target, ir: ArtifactIR) -> ArtifactIR:
        """Return a copy of the IR with the canary values, for the trap render pass."""
        rows = [(t.heading, t.text_canary), (f"{t.chart_title}: {t.peak_name}", t.image_canary)]
        return with_evidence(ir, evidence_section(t.heading, rows), depth=EVIDENCE_DEPTH, title_suffix=self.draft_suffix)

    def trap_kind(self) -> str:
        """Return the file kind of the trap in the canary render pass."""
        return self.fmt

    def add_picture(self, t: Target, payload: bytes, seed: int) -> bytes:
        raise NotImplementedError

    def pad(self, payload: bytes, size_bytes: int, seed: int) -> bytes:
        raise NotImplementedError

    def finish_target(self, t: Target, payload: bytes, seed: int) -> bytes:
        """Add the image fact to a rendered target, then pad it to its size."""
        return self.pad(self.add_picture(t, payload, seed), t.size_bytes, seed)

    def finish_trap(self, t: Target, payload: bytes) -> bytes:
        """Return the trap file. The default keeps the rendered canary file."""
        return payload
