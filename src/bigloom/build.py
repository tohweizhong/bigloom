"""Synthesize large enterprise documents and paired canary trap files."""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from docx import Document
from docx.shared import Inches
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.util import Inches as PptxInches
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from worldloom import sdk
from worldloom.world import World

from .models import ManifestEntry

DEFAULT_TOPICS = (
    "Project Aurora Sovereign Grid",
    "Project Borealis Thermal Loop",
    "Project Cygnus Subsea Cable",
    "Project Draco Vault Storage",
    "Project Ecliptic Photonics Bus",
    "Project Falcon Cryo Substation",
    "Project Gemini Harbor Microgrid",
    "Project Helios Salt Cavern",
)


@dataclass(frozen=True)
class _WorldContext:
    """Grounded enterprise entities and currency extracted from WorldLoom."""

    topics: tuple[str, ...]
    currency: str
    governance_line: str


def _extract_seed_topics(corpus_dir: Path | None) -> list[str]:
    """Read topic phrases from markdown or text files in corpus_dir when provided."""
    if corpus_dir is None or not corpus_dir.exists():
        return list(DEFAULT_TOPICS)
    found: list[str] = []
    for path in sorted(corpus_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            cleaned = line.strip().lstrip("#").strip()
            if len(cleaned) >= 8:
                found.append(cleaned[:60])
                break
    return found + [t for t in DEFAULT_TOPICS if t not in found]


def _resolve_world_context(
    *,
    seed: int,
    corpus_dir: Path | None = None,
    world_pack: str | None = None,
    domain: str | None = None,
) -> _WorldContext:
    """Resolve WorldLoom company, business units, cost centres, systems, and currency."""
    world: World | None = None
    if world_pack:
        world = World.load(world_pack)
    elif domain:
        world = sdk.company(domain.strip().lower(), seed=seed).build().world
    elif corpus_dir is not None and (corpus_dir / "company.json").is_file():
        world = World.load(corpus_dir)

    if world is None:
        return _WorldContext(
            topics=tuple(_extract_seed_topics(corpus_dir)),
            currency="SGD",
            governance_line="All telemetry streams are logged prior to appendix verification.",
        )

    company_name = world.company.name
    currency = (world.company.currency or "SGD").strip().upper()
    topics: list[str] = [
        f"{company_name} {bu.name} Division" for bu in world.business_units
    ]
    if not topics:
        topics = [f"{company_name} Enterprise Operations"]

    cc_tags = [f"{cc.id} ({cc.name})" for cc in world.cost_centres[:3]]
    sys_tags = [f"{sys.id} ({sys.name})" for sys in world.systems[:3]]
    site_tags = [site.name for site in world.sites[:3]]
    details: list[str] = [f"Company: {company_name}"]
    if cc_tags:
        details.append(f"Cost Centres: {', '.join(cc_tags)}")
    if sys_tags:
        details.append(f"Systems: {', '.join(sys_tags)}")
    if site_tags:
        details.append(f"Sites: {', '.join(site_tags)}")
    governance_line = " | ".join(details) + "."

    return _WorldContext(
        topics=tuple(topics),
        currency=currency,
        governance_line=governance_line,
    )


def _make_chart_png(
    rng: random.Random,
    title: str,
    printed_value: str,
    raw_rgb_bytes: int,
) -> bytes:
    """Render a bar chart PNG with printed_value drawn on canvas and noisy background payload."""
    effective_bytes = raw_rgb_bytes + (260 * 64 * 3)
    pixels = max(96 * 96, math.ceil(effective_bytes / 3))
    side = max(140, math.ceil(math.sqrt(pixels)))
    noise = rng.randbytes(side * side * 3)
    img = Image.frombytes("RGB", (side, side), noise)
    draw = ImageDraw.Draw(img)
    card_w = min(side - 8, 260)
    card_h = min(side - 8, 64)
    draw.rectangle([4, 4, 4 + card_w, 4 + card_h], fill=(255, 255, 255), outline=(20, 40, 80))
    draw.text((10, 10), title[:36], fill=(10, 20, 40))
    draw.text((10, 28), f"Verified Metric: {printed_value}", fill=(0, 100, 40))
    draw.rectangle([10, 46, 140, 58], fill=(30, 110, 200))
    buf = BytesIO()
    img.save(buf, format="PNG", compress_level=1)
    return buf.getvalue()


def _split_image_budgets(target_bytes: int, max_chunk: int = 3_000_000) -> list[int]:
    """Split a byte budget into one or more raw RGB image sizes with an 8% safety margin."""
    padded = max(24_576, int(target_bytes * 1.08))
    chunks: list[int] = []
    remaining = padded
    while remaining > 0:
        step = min(remaining, max_chunk)
        chunks.append(step)
        remaining -= step
    return chunks


def _render_docx(
    rng: random.Random,
    *,
    header_line: str,
    governance_line: str,
    fact_sentence: str,
    chart_title: str,
    chart_value: str,
    target_bytes: int,
) -> tuple[bytes, int]:
    """Render a .docx file with the text fact at paragraph index >= 6 and embedded chart PNGs."""
    doc = Document()
    doc.add_heading(header_line, level=1)
    for idx in range(1, 5):
        doc.add_paragraph(
            f"Section {idx}: Operational governance and compliance review for {header_line}. "
            f"{governance_line}"
        )
    doc.add_paragraph(fact_sentence)
    text_unit_index = 6

    chunks = _split_image_budgets(target_bytes)
    for chunk_idx, chunk_bytes in enumerate(chunks):
        png = _make_chart_png(
            rng,
            title=f"{chart_title} (Panel {chunk_idx + 1})",
            printed_value=chart_value,
            raw_rgb_bytes=chunk_bytes,
        )
        doc.add_picture(BytesIO(png), width=Inches(5.5))

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue(), text_unit_index


def _render_xlsx(
    rng: random.Random,
    *,
    header_line: str,
    governance_line: str,
    fact_sentence: str,
    chart_title: str,
    chart_value: str,
    target_bytes: int,
) -> tuple[bytes, int]:
    """Render an .xlsx file with at least 6 populated rows before the deep fact and chart PNGs."""
    wb = Workbook()
    ws = wb.active
    ws.title = "AuditLedger"
    for row_idx in range(1, 6):
        ws.append(
            [
                f"ROW-{row_idx:02d}",
                header_line,
                f"Baseline telemetry checkpoint {row_idx} | {governance_line}",
            ]
        )
    ws.append(["ROW-06-DEEP", header_line, fact_sentence])
    text_unit_index = 6

    chunks = _split_image_budgets(target_bytes)
    for chunk_idx, chunk_bytes in enumerate(chunks):
        png = _make_chart_png(
            rng,
            title=f"{chart_title} (Panel {chunk_idx + 1})",
            printed_value=chart_value,
            raw_rgb_bytes=chunk_bytes,
        )
        img = XlImage(BytesIO(png))
        ws.add_image(img, f"A{10 + chunk_idx * 20}")

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue(), text_unit_index


def _render_pptx(
    rng: random.Random,
    *,
    header_line: str,
    governance_line: str,
    fact_sentence: str,
    chart_title: str,
    chart_value: str,
    target_bytes: int,
) -> tuple[bytes, int]:
    """Render a .pptx presentation with the planted fact on slide 6 and chart PNGs on slides."""
    prs = Presentation()
    blank_layout = prs.slide_layouts[6]

    for slide_idx in range(1, 6):
        slide = prs.slides.add_slide(blank_layout)
        tx = slide.shapes.add_textbox(
            PptxInches(0.8), PptxInches(0.8), PptxInches(8.0), PptxInches(2.0)
        )
        tx.text_frame.text = (
            f"Slide {slide_idx}: {header_line}\n"
            f"Preliminary architecture notes {slide_idx}. {governance_line}"
        )

    fact_slide = prs.slides.add_slide(blank_layout)
    fact_box = fact_slide.shapes.add_textbox(
        PptxInches(0.8), PptxInches(0.8), PptxInches(8.0), PptxInches(2.5)
    )
    fact_box.text_frame.text = f"Slide 6 Deep Appendix: {header_line}\n{fact_sentence}"
    text_unit_index = 6

    chunks = _split_image_budgets(target_bytes)
    for chunk_idx, chunk_bytes in enumerate(chunks):
        png = _make_chart_png(
            rng,
            title=f"{chart_title} (Panel {chunk_idx + 1})",
            printed_value=chart_value,
            raw_rgb_bytes=chunk_bytes,
        )
        chart_slide = prs.slides.add_slide(blank_layout)
        lbl = chart_slide.shapes.add_textbox(
            PptxInches(0.8), PptxInches(0.4), PptxInches(8.0), PptxInches(0.8)
        )
        lbl.text_frame.text = f"Visual Appendix {chunk_idx + 1}: {header_line} — {chart_title}"
        chart_slide.shapes.add_picture(
            BytesIO(png), PptxInches(0.8), PptxInches(1.3), width=PptxInches(6.0)
        )

    buf = BytesIO()
    prs.save(buf)
    return buf.getvalue(), text_unit_index


def _render_pdf(
    rng: random.Random,
    *,
    header_line: str,
    governance_line: str,
    fact_sentence: str,
    chart_title: str,
    chart_value: str,
    target_bytes: int,
) -> tuple[bytes, int]:
    """Render a multi-page PDF with the planted text fact on page 6 and embedded chart PNGs."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    for page_idx in range(1, 6):
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 730, f"Page {page_idx}: {header_line}")
        c.setFont("Helvetica", 10)
        c.drawString(50, 705, f"Section {page_idx}: {governance_line}")
        c.showPage()

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 730, f"Page 6 Deep Appendix: {header_line}")
    c.setFont("Helvetica", 10)
    c.drawString(50, 700, fact_sentence)
    c.showPage()
    text_unit_index = 6

    chunks = _split_image_budgets(target_bytes)
    for chunk_idx, chunk_bytes in enumerate(chunks):
        png = _make_chart_png(
            rng,
            title=f"{chart_title} (Panel {chunk_idx + 1})",
            printed_value=chart_value,
            raw_rgb_bytes=chunk_bytes,
        )
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, 730, f"Visual Telemetry {chunk_idx + 1}: {header_line} — {chart_title}")
        c.drawImage(ImageReader(BytesIO(png)), 50, 220, width=440, height=440)
        c.showPage()

    c.save()
    return buf.getvalue(), text_unit_index


def _render_by_format(
    fmt: Literal["docx", "xlsx", "pptx", "pdf"],
    rng: random.Random,
    *,
    header_line: str,
    governance_line: str,
    fact_sentence: str,
    chart_title: str,
    chart_value: str,
    target_bytes: int,
) -> tuple[bytes, int]:
    if fmt == "docx":
        return _render_docx(
            rng,
            header_line=header_line,
            governance_line=governance_line,
            fact_sentence=fact_sentence,
            chart_title=chart_title,
            chart_value=chart_value,
            target_bytes=target_bytes,
        )
    if fmt == "xlsx":
        return _render_xlsx(
            rng,
            header_line=header_line,
            governance_line=governance_line,
            fact_sentence=fact_sentence,
            chart_title=chart_title,
            chart_value=chart_value,
            target_bytes=target_bytes,
        )
    if fmt == "pptx":
        return _render_pptx(
            rng,
            header_line=header_line,
            governance_line=governance_line,
            fact_sentence=fact_sentence,
            chart_title=chart_title,
            chart_value=chart_value,
            target_bytes=target_bytes,
        )
    if fmt == "pdf":
        return _render_pdf(
            rng,
            header_line=header_line,
            governance_line=governance_line,
            fact_sentence=fact_sentence,
            chart_title=chart_title,
            chart_value=chart_value,
            target_bytes=target_bytes,
        )
    raise ValueError(f"Unsupported format: {fmt}")


def _unique_currency(rng: random.Random, used: set[str], currency: str = "SGD") -> str:
    while True:
        val = f"{currency} {rng.randint(1, 9)},{rng.randint(100, 999)},{rng.randint(100, 999)}"
        if val not in used:
            used.add(val)
            return val


def _unique_percentage(rng: random.Random, used: set[str]) -> str:
    while True:
        val = f"{rng.randint(11, 89)}.{rng.randint(11, 99)}%"
        if val not in used:
            used.add(val)
            return val


def build_corpus(
    out_dir: Path,
    *,
    sizes_mb: Sequence[float] = (18.0, 50.0, 100.0),
    seed: int = 42,
    formats: Sequence[str] = ("docx", "xlsx", "pptx", "pdf"),
    corpus_dir: Path | None = None,
    world_pack: str | None = None,
    domain: str | None = None,
) -> list[ManifestEntry]:
    """Build large native documents and paired < 1 MB distractor trap files."""
    rng = random.Random(seed)
    ctx = _resolve_world_context(
        seed=seed,
        corpus_dir=corpus_dir,
        world_pack=world_pack,
        domain=domain,
    )
    topics = ctx.topics
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "large").mkdir(parents=True, exist_ok=True)
    (out_dir / "traps").mkdir(parents=True, exist_ok=True)

    used_values: set[str] = set()
    entries: list[ManifestEntry] = []
    item_counter = 0

    for size_mb in sizes_mb:
        min_target_bytes = int(size_mb * 1024 * 1024)
        size_tag = f"{size_mb:g}mb".replace(".", "_")
        for fmt_raw in formats:
            fmt = fmt_raw.lower().strip().removeprefix(".")
            if fmt not in ("docx", "xlsx", "pptx", "pdf"):
                raise ValueError(f"Unsupported format '{fmt_raw}'.")
            typed_fmt: Literal["docx", "xlsx", "pptx", "pdf"] = fmt  # type: ignore[assignment]

            base_topic = topics[item_counter % len(topics)]
            item_counter += 1
            file_id = f"bl-{item_counter:03d}-{fmt}-{size_tag}"
            topic = f"{base_topic} Unit-{item_counter:03d}"
            period = "FY2026"
            distractor_period = "FY2025"

            text_metric_label = f"{topic} {period} Authorized Capital Reserve"
            image_chart_title = f"{topic} {period} Q4 Peak Thermal Efficiency"

            text_golden = _unique_currency(rng, used_values, currency=ctx.currency)
            text_canary = _unique_currency(rng, used_values, currency=ctx.currency)
            image_golden = _unique_percentage(rng, used_values)
            image_canary = _unique_percentage(rng, used_values)

            target_rel = f"large/{file_id}_fy2026_final.{fmt}"
            distractor_rel = f"traps/{file_id}_fy2025_draft.{fmt}"

            target_header = (
                f"{topic} {period} Final Audit Report | "
                f"{text_metric_label} | {image_chart_title}"
            )
            target_fact = (
                f"Verified {text_metric_label} for {topic} ({period} Final): {text_golden}."
            )
            target_bytes, text_unit_idx = _render_by_format(
                typed_fmt,
                rng,
                header_line=target_header,
                governance_line=ctx.governance_line,
                fact_sentence=target_fact,
                chart_title=image_chart_title,
                chart_value=image_golden,
                target_bytes=min_target_bytes,
            )

            dist_header = f"{topic} {distractor_period} Preliminary Draft Report"
            dist_fact = (
                f"Preliminary {topic} {distractor_period} Draft Capital Reserve: "
                f"{text_canary} (Chart Draft Metric: {image_canary})."
            )
            dist_bytes, _ = _render_by_format(
                typed_fmt,
                rng,
                header_line=dist_header,
                governance_line=ctx.governance_line,
                fact_sentence=dist_fact,
                chart_title=f"{topic} {distractor_period} Draft Chart",
                chart_value=image_canary,
                target_bytes=24_576,
            )

            target_path = out_dir / target_rel
            dist_path = out_dir / distractor_rel
            target_path.write_bytes(target_bytes)
            dist_path.write_bytes(dist_bytes)

            entries.append(
                ManifestEntry(
                    file_id=file_id,
                    format=typed_fmt,
                    target_file=target_rel,
                    target_size_bytes=len(target_bytes),
                    target_sha256=hashlib.sha256(target_bytes).hexdigest(),
                    distractor_file=distractor_rel,
                    distractor_size_bytes=len(dist_bytes),
                    distractor_sha256=hashlib.sha256(dist_bytes).hexdigest(),
                    topic=topic,
                    period=period,
                    distractor_period=distractor_period,
                    text_metric_label=text_metric_label,
                    text_golden_value=text_golden,
                    text_canary_value=text_canary,
                    text_unit_index=text_unit_idx,
                    image_chart_title=image_chart_title,
                    image_golden_value=image_golden,
                    image_canary_value=image_canary,
                )
            )

    manifest_path = out_dir / "manifest.jsonl"
    manifest_lines = [entry.model_dump_json() for entry in entries]
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    return entries
