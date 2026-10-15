"""Rich high-resolution chart and diagram drawers and tight 12% grain byte encoder."""

from __future__ import annotations

import io
import math
import random
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .prose_writer import (
    AGENCIES,
    FY_MONTHS,
    GIVEN,
    QUARTERS,
    SHORT_MARK,
    SURNAMES,
    ProseCorpus,
)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
GRAIN = 12
_FONTS: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def font(
    size: int,
    bold: bool = False,
    style: str = "",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a DejaVu TrueType font at the requested pixel size with a default fallback."""
    name = {
        "mono": "DejaVuSansMono.ttf",
        "hand": "DejaVuSansCondensed-BoldOblique.ttf",
        "serif": "DejaVuSerif.ttf",
    }.get(style)
    if not name:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    key = (name, size)
    if key not in _FONTS:
        try:
            _FONTS[key] = ImageFont.truetype(str(FONT_DIR / name), size)
        except OSError:
            _FONTS[key] = ImageFont.load_default(size)
    return _FONTS[key]


def text_size(
    d: ImageDraw.ImageDraw,
    text: str,
    f: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    """Return rendered width and height of text."""
    box = d.textbbox((0, 0), text, font=f)
    return int(box[2] - box[0]), int(box[3] - box[1])


def ctext(
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    f: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] | tuple[int, int, int, int] | str = (20, 20, 20),
) -> None:
    """Draw centered text at xy."""
    w, h = text_size(d, text, f)
    d.text((xy[0] - w / 2, xy[1] - h / 2), text, font=f, fill=fill)


def shade(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    """Return a lighter tint of color blended toward white by amount."""
    return (
        int(color[0] + (255 - color[0]) * amount),
        int(color[1] + (255 - color[1]) * amount),
        int(color[2] + (255 - color[2]) * amount),
    )


def palette(theme: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    """Return a 9-color chart palette anchored by theme."""
    return [
        theme,
        (31, 119, 180),
        (255, 127, 14),
        (44, 160, 44),
        (148, 103, 189),
        (140, 86, 75),
        (23, 190, 207),
        (188, 189, 34),
        (127, 127, 127),
    ]


def _draw_metric_badge(
    d: ImageDraw.ImageDraw,
    w: int,
    h: int,
    chart_title: str,
    printed_value: str,
    theme: tuple[int, int, int],
) -> None:
    """Stamp a crisp callout badge on the chart canvas with the verified metric."""
    label = f"{chart_title}: {printed_value}"
    f_lbl = font(24, bold=True)
    tw, th = text_size(d, label, f_lbl)
    pad_x, pad_y = 22, 12
    box_w = min(w - 160, tw + pad_x * 2)
    x1 = w - 70
    x0 = x1 - box_w
    y0 = h - 135
    y1 = y0 + th + pad_y * 2
    d.rounded_rectangle(
        (x0, y0, x1, y1),
        radius=12,
        fill=shade(theme, 0.88),
        outline=theme,
        width=3,
    )
    d.text((x0 + pad_x, y0 + pad_y), label, font=f_lbl, fill=(15, 23, 42))


def new_chart(
    w: int,
    h: int,
    title: str,
    subtitle: str,
    theme: tuple[int, int, int],
    source: str,
    chart_title: str = "",
    printed_value: str = "",
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a white RGB chart canvas with themed top bar, title, source, and marking."""
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 16), fill=theme)
    d.text((80, 44), title[:82], font=font(46, bold=True), fill=(25, 25, 25))
    d.text((80, 112), subtitle[:100], font=font(28), fill=(100, 100, 100))
    d.text((80, h - 58), f"Source: {source}", font=font(24), fill=(120, 120, 120))
    mw, _ = text_size(d, SHORT_MARK, font(24, bold=True))
    d.text((w - 80 - mw, h - 58), SHORT_MARK, font=font(24, bold=True), fill=(170, 0, 0))
    if chart_title and printed_value:
        _draw_metric_badge(d, w, h, chart_title, printed_value, theme)
    return img, d


@dataclass
class FigurePlate:
    """Rendered chart or diagram figure ready for byte-budget encoding."""

    base: Image.Image
    caption: str
    fmt: str
    kind: str
    data: bytes = b""
    size: tuple[int, int] = (0, 0)


@dataclass
class ChartContext:
    """Per-document drawing context that prevents duplicate chart topics in one document."""

    rng: random.Random
    corpus: ProseCorpus
    title: str
    date: str
    theme: tuple[int, int, int]
    chart_title: str
    printed_value: str
    used: set[str] = field(default_factory=set)

    def pick(self, pool: Sequence[tuple], key=lambda x: x[0]):  # type: ignore[no-untyped-def]
        free = [p for p in pool if str(key(p)) not in self.used] or list(pool)
        choice = self.rng.choice(free)
        self.used.add(str(key(choice)))
        return choice

    def person(self) -> str:
        for name, _ in self.corpus.people:
            if name not in self.used:
                self.used.add(name)
                return name
        name = "Tan Wei Jie"
        for _ in range(50):
            name = f"{self.rng.choice(GIVEN)} {self.rng.choice(SURNAMES)}"
            if name not in self.used:
                self.used.add(name)
                return name
        return name

    def agencies(self, n: int) -> list[str]:
        pool = list(self.corpus.effective_part_labels())
        for fallback in AGENCIES:
            if len(pool) >= max(n, 8):
                break
            if fallback not in pool:
                pool.append(fallback)
        return self.rng.sample(pool, min(n, len(pool)))

    @property
    def short(self) -> str:
        return self.title.split("|")[0].split(":")[0].strip()[:48]


LINE_METRICS = [
    ("Monthly active users", "thousand users", 300, 900, 0),
    ("Successful logins", "million", 20, 60, 1),
    ("Cloud spend", "SGD thousand", 1500, 6000, 0),
    ("Helpdesk tickets resolved", "tickets", 6000, 20000, 0),
    ("API calls through the API gateway", "million", 150, 800, 1),
    ("Median page load time", "ms", 700, 1600, 0),
    ("Open vulnerabilities", "findings", 80, 400, 0),
    ("Officers trained", "officers", 200, 1500, 0),
    ("Energy used by the data hall", "MWh", 300, 900, 0),
]


def img_line(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    name, unit, lo, hi, dp = ctx.pick(LINE_METRICS)
    start = rng.uniform(lo, (lo + hi) / 2)
    trend = rng.uniform(-0.03, 0.07)
    vals = []
    for i in range(12):
        v = (
            start
            * (1 + trend) ** i
            * (1 + 0.08 * math.sin(i / 1.7 + rng.random()))
            * rng.uniform(0.95, 1.05)
        )
        vals.append(round(v, dp))
    title = f"{name} ({ctx.short}), FY2026"
    img, d = new_chart(
        2400,
        1600,
        title,
        f"{ctx.short}. Unit: {unit}.",
        ctx.theme,
        "Operations data warehouse",
        ctx.chart_title,
        ctx.printed_value,
    )
    left, top, right, bottom = 230, 230, 2280, 1280
    peak = max(vals) * 1.15
    for g in range(6):
        y = bottom - (bottom - top) * g / 5
        d.line((left, y, right, y), fill=(225, 225, 225), width=2)
        lab = f"{peak * g / 5:,.{dp}f}"
        w, _ = text_size(d, lab, font(24))
        d.text((left - 20 - w, y - 14), lab, font=font(24), fill=(90, 90, 90))
    pts = []
    for i, v in enumerate(vals):
        x = left + 60 + i * (right - left - 120) / 11
        y = bottom - (bottom - top) * v / peak
        pts.append((x, y))
    d.line(pts, fill=ctx.theme, width=7, joint="curve")
    for (x, y), v, m in zip(pts, vals, FY_MONTHS):
        d.ellipse((x - 11, y - 11, x + 11, y + 11), fill="white", outline=ctx.theme, width=5)
        ctext(d, (x, y - 42), f"{v:,.{dp}f}", font(26, bold=True))
        ctext(d, (x, bottom + 34), m.replace(" 20", " '"), font(26))
    d.line((left, bottom, right, bottom), fill=(60, 60, 60), width=3)
    return img, title, "PNG"


BAR_METRICS = [
    ("Digital services launched by division", "services", 3, 45),
    ("Staff onboarded by division", "staff", 150, 4800),
    ("Open audit findings by division", "findings", 2, 36),
    ("Workloads migrated to cloud by division", "workloads", 8, 320),
    ("Support tickets raised by division", "tickets", 90, 2600),
    ("Staff with a cloud certification by division", "staff", 12, 460),
]


def img_bar(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    raw_name, unit, lo, hi = ctx.pick(BAR_METRICS)
    name = f"{raw_name} ({ctx.short})"
    labels = ctx.agencies(8)
    vals = sorted((rng.randint(lo, hi) for _ in labels), reverse=True)
    img, d = new_chart(
        2400,
        1600,
        name,
        f"{ctx.short}. Unit: {unit}. As at {ctx.date}.",
        ctx.theme,
        "Agency returns",
        ctx.chart_title,
        ctx.printed_value,
    )
    left, top, right = 430, 220, 2150
    row = (1280 - top) / len(labels)
    for i, (lab, v) in enumerate(zip(labels, vals)):
        y0 = top + i * row + row * 0.18
        y1 = top + (i + 1) * row - row * 0.18
        x1 = left + (right - left) * v / (max(vals) * 1.08)
        d.rectangle((left, y0, x1, y1), fill=shade(ctx.theme, 0.15 * (i % 3)))
        w, h = text_size(d, lab, font(32))
        d.text((left - 30 - w, (y0 + y1) / 2 - h / 2 - 4), lab, font=font(32), fill=(40, 40, 40))
        d.text(
            (x1 + 18, (y0 + y1) / 2 - 20),
            f"{v:,}",
            font=font(32, bold=True),
            fill=(25, 25, 25),
        )
    d.line((left, top - 20, left, 1290), fill=(60, 60, 60), width=3)
    return img, name, "PNG"


DONUT_SETS = [
    (
        "Cloud spend by service type",
        ["Compute", "Storage", "Database", "Networking", "Security services", "AI services"],
    ),
    (
        "Incident root causes",
        [
            "Change error",
            "Capacity",
            "Third-party fault",
            "Configuration drift",
            "Software defect",
            "Unknown",
        ],
    ),
    (
        "Helpdesk contacts by channel",
        ["Live chat", "Email", "Phone", "Walk-in", "Self-service portal"],
    ),
    (
        "Workforce by job family",
        [
            "Software engineering",
            "Product management",
            "Data science",
            "Cybersecurity",
            "Infrastructure",
            "Corporate",
        ],
    ),
    (
        "Contract value by procurement mode",
        [
            "Small value purchase",
            "Quotation",
            "Open tender",
            "Framework agreement",
            "Period contract",
        ],
    ),
]


def img_donut(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    raw_name, labels = ctx.pick(DONUT_SETS)
    name = f"{raw_name} ({ctx.short})"
    weights = [rng.uniform(0.5, 3) for _ in labels]
    pct = [max(2, round(100 * w / sum(weights))) for w in weights]
    pct[0] += 100 - sum(pct)
    img, d = new_chart(
        2400,
        1600,
        name,
        f"{ctx.short}. Share of total, FY2026.",
        ctx.theme,
        "Finance and operations reports",
        ctx.chart_title,
        ctx.printed_value,
    )
    cols = palette(ctx.theme)
    box = (240, 260, 1140, 1160)
    angle = -90.0
    for i, p in enumerate(pct):
        d.pieslice(box, angle, angle + 3.6 * p, fill=cols[i % len(cols)], outline="white", width=6)
        angle += 3.6 * p
    d.ellipse((470, 490, 910, 930), fill="white")
    total = rng.randint(120, 980)
    ctext(d, (690, 680), f"{total:,}", font(72, bold=True))
    ctext(d, (690, 760), "total items, FY2026", font(28), fill=(100, 100, 100))
    for i, (lab, p) in enumerate(zip(labels, pct)):
        y = 320 + i * 130
        d.rectangle((1320, y, 1380, y + 60), fill=cols[i % len(cols)])
        d.text((1410, y + 6), f"{lab}: {p}%", font=font(40), fill=(30, 30, 30))
    return img, name, "PNG"


STACK_SETS = [
    ("Incidents by severity", ["P1", "P2", "P3", "P4"], (1, 60)),
    ("Service requests by channel", ["Portal", "Email", "Phone"], (200, 1400)),
    ("Change requests by type", ["Standard", "Normal", "Emergency"], (20, 400)),
    ("Pipeline runs by result", ["Passed", "Failed", "Cancelled"], (500, 6000)),
    ("Audit findings by rating", ["High", "Medium", "Low"], (2, 40)),
]


def img_stacked(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    raw_name, series, (lo, hi) = ctx.pick(STACK_SETS)
    name = f"{raw_name} ({ctx.short})"
    vals = [[rng.randint(max(lo, hi // 6), hi) for _ in QUARTERS] for _ in series]
    img, d = new_chart(
        2400,
        1600,
        f"{name} per quarter",
        f"{ctx.short}. Count per quarter, FY2026.",
        ctx.theme,
        "Service management system",
        ctx.chart_title,
        ctx.printed_value,
    )
    cols = palette(ctx.theme)
    left, top, right, bottom = 260, 230, 1850, 1280
    peak = max(sum(v[q] for v in vals) for q in range(4)) * 1.1
    slot = (right - left) / 4
    for q, label in enumerate(QUARTERS):
        x0, x1 = left + q * slot + slot * 0.2, left + (q + 1) * slot - slot * 0.2
        y = bottom
        for s in range(len(series)):
            hgt = (bottom - top) * vals[s][q] / peak
            d.rectangle((x0, y - hgt, x1, y), fill=cols[s], outline="white", width=3)
            ctext(
                d,
                ((x0 + x1) / 2, y - hgt / 2),
                f"{vals[s][q]:,}",
                font(30, bold=True),
                fill="white",
            )
            y -= hgt
        ctext(d, ((x0 + x1) / 2, bottom + 36), label, font(30))
    d.line((left, bottom, right, bottom), fill=(60, 60, 60), width=3)
    for s, lab in enumerate(series):
        d.rectangle((1950, 300 + s * 90, 2000, 350 + s * 90), fill=cols[s])
        d.text((2025, 305 + s * 90), lab, font=font(34), fill=(30, 30, 30))
    return img, f"{name} per quarter", "PNG"


HEAT_SETS = [
    ("Open vulnerability findings by division", ["Critical", "High", "Medium", "Low"]),
    ("Security control gaps by division", ["Access", "Logging", "Encryption", "Backup", "Patching"]),
    ("Failed logins by division and hour band", ["00-06", "06-12", "12-18", "18-24"]),
    ("Sensor faults by zone and week", ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5"]),
    ("Exercise detections by division and phase", ["Recon", "Access", "Lateral", "Exfil"]),
]


def img_heatmap(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    raw_name, cols = ctx.pick(HEAT_SETS)
    name = f"{raw_name} ({ctx.short})"
    rows = ctx.agencies(7)
    vals = [[rng.randint(0, 99) for _ in cols] for _ in rows]
    img, d = new_chart(
        2400,
        1600,
        name,
        f"{ctx.short}. Count in each cell.",
        ctx.theme,
        "Security operations centre",
        ctx.chart_title,
        ctx.printed_value,
    )
    left, top = 420, 260
    cw, ch = min(360, 1850 // len(cols)), 145
    for j, c in enumerate(cols):
        ctext(d, (left + j * cw + cw / 2, top - 40), c, font(32, bold=True))
    for i, r in enumerate(rows):
        w, _ = text_size(d, r, font(32))
        d.text((left - 30 - w, top + i * ch + ch / 2 - 20), r, font=font(32), fill=(40, 40, 40))
        for j in range(len(cols)):
            v = vals[i][j]
            col = (
                int(255 - (255 - ctx.theme[0]) * (0.15 + 0.85 * v / 99)),
                int(255 - (255 - ctx.theme[1]) * (0.15 + 0.85 * v / 99)),
                int(255 - (255 - ctx.theme[2]) * (0.15 + 0.85 * v / 99)),
            )
            d.rectangle(
                (left + j * cw, top + i * ch, left + (j + 1) * cw - 4, top + (i + 1) * ch - 4),
                fill=col,
            )
            ctext(
                d,
                (left + j * cw + cw / 2, top + i * ch + ch / 2),
                str(v),
                font(40, bold=True),
                fill="white" if v > 55 else (30, 30, 30),
            )
    return img, name, "PNG"


KPI_APPS = [
    "Service Health Console",
    "Cloud Cost Explorer",
    "Identity Operations Console",
    "Developer Portal Analytics",
    "Sensor Platform Monitor",
    "Workforce Dashboard",
]
KPI_TILES = [
    ("Availability (30 days)", "{:.2f}%", 99.1, 99.99),
    ("P1 incidents open", "{:.0f}", 0, 6),
    ("Mean time to restore", "{:.0f} min", 12, 95),
    ("Active users today", "{:,.0f}", 12000, 98000),
    ("Month-to-date spend", "SGD {:,.0f}k", 300, 4200),
    ("Error rate", "{:.2f}%", 0.05, 2.5),
    ("Deployments this week", "{:.0f}", 40, 700),
    ("Queue depth", "{:,.0f}", 10, 4000),
    ("Devices online", "{:,.0f}", 800, 5200),
    ("Tickets breaching SLA", "{:.0f}", 0, 45),
    ("CSAT score", "{:.1f} / 5", 3.6, 4.9),
    ("p95 latency", "{:.0f} ms", 180, 1400),
]


def img_kpi(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    app = ctx.pick([(a,) for a in KPI_APPS])[0]
    tiles = rng.sample(KPI_TILES, 6)
    w, h = 2400, 1500
    img = Image.new("RGB", (w, h), (243, 245, 248))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 70), fill=(222, 225, 230))
    for k, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse((30 + k * 40, 22, 56 + k * 40, 48), fill=c)
    d.rounded_rectangle((200, 14, 1600, 56), 18, fill="white")
    d.text(
        (225, 20),
        f"https://ops-console.internal/{app.lower().replace(' ', '-')}",
        font=font(24),
        fill=(90, 90, 90),
    )
    d.rectangle((0, 70, w, 170), fill=ctx.theme)
    d.text((60, 98), app, font=font(44, bold=True), fill="white")
    d.text(
        (w - 620, 108),
        f"Last refreshed {ctx.date} 09:{rng.randint(10, 59)} SGT",
        font=font(26),
        fill="white",
    )
    for k, (label, fmt, lo, hi) in enumerate(tiles):
        x0, y0 = 60 + (k % 3) * 780, 210 + (k // 3) * 540
        d.rounded_rectangle(
            (x0, y0, x0 + 740, y0 + 490),
            24,
            fill="white",
            outline=(215, 218, 224),
            width=3,
        )
        d.text((x0 + 40, y0 + 36), label, font=font(34), fill=(90, 90, 90))
        v = rng.uniform(lo, hi)
        text = fmt.format(v)
        d.text((x0 + 40, y0 + 100), text, font=font(84, bold=True), fill=(25, 25, 25))
        delta = rng.uniform(-12, 12)
        d.text(
            (x0 + 40, y0 + 220),
            f"{'▲' if delta > 0 else '▼'} {abs(delta):.1f}% vs last week",
            font=font(28),
            fill=(30, 140, 60) if delta > 0 else (190, 40, 40),
        )
        pts = [(x0 + 40 + t * 22, y0 + 430 - rng.uniform(0, 130)) for t in range(30)]
        d.line(pts, fill=shade(ctx.theme, 0.2), width=4)
    _draw_metric_badge(d, w, h, ctx.chart_title, ctx.printed_value, ctx.theme)
    return img, f"{app} screenshot", "PNG"


GANTT_TASKS = [
    "Discovery",
    "Service design",
    "Build, sprints 1 to 4",
    "Security test (VAPT)",
    "User acceptance test",
    "Data migration",
    "Agency onboarding",
    "Go-live",
    "Hypercare",
    "Decommission legacy",
    "Procurement",
    "Training",
]


def img_gantt(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    tasks = rng.sample(GANTT_TASKS, 8)
    cap = f"Delivery plan: {ctx.short}"
    img, d = new_chart(
        2400,
        1600,
        cap,
        "FY2025 to FY2026. Diamonds mark milestones.",
        ctx.theme,
        "Programme office",
        ctx.chart_title,
        ctx.printed_value,
    )
    left, top, right = 600, 260, 2320
    mw = (right - left) / 12
    for m, lab in enumerate(FY_MONTHS):
        ctext(d, (left + m * mw + mw / 2, top - 40), lab.replace(" 20", " '"), font(24))
        d.line((left + m * mw, top - 10, left + m * mw, 1340), fill=(230, 230, 230), width=2)
    for i, t in enumerate(tasks):
        y = top + i * 128
        d.text((80, y + 30), t, font=font(32), fill=(40, 40, 40))
        s = rng.randint(0, 8)
        e = rng.randint(s + 1, min(12, s + 5))
        d.rounded_rectangle(
            (left + s * mw, y + 25, left + e * mw, y + 80),
            12,
            fill=shade(ctx.theme, 0.1 + 0.1 * (i % 3)),
        )
        day = rng.randint(2, 27)
        month = FY_MONTHS[e - 1]
        date = f"{day} {month.split()[0]} {month.split()[1]}"
        cx, cy = left + e * mw, y + 52
        d.polygon([(cx, cy - 30), (cx + 30, cy), (cx, cy + 30), (cx - 30, cy)], fill=(20, 20, 20))
        lx = cx + 40 if cx < right - 300 else cx - 300
        d.text((lx, cy - 18), date, font=font(28, bold=True), fill=(20, 20, 20))
    return img, cap, "PNG"


SERVICES = [
    "profile-service",
    "notification-service",
    "document-service",
    "eligibility-engine",
    "payment-adapter",
    "consent-manager",
    "audit-writer",
    "search-indexer",
    "case-router",
    "sensor-ingest",
]


def _arrow(
    d: ImageDraw.ImageDraw,
    a: tuple[int, int],
    b: tuple[int, int],
    color: tuple[int, int, int] = (70, 70, 70),
    width: int = 5,
) -> None:
    d.line((a, b), fill=color, width=width)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for s in (-0.45, 0.45):
        d.line(
            (b, (b[0] - 30 * math.cos(ang + s), b[1] - 30 * math.sin(ang + s))),
            fill=color,
            width=width,
        )


def img_architecture(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    nodes = rng.randint(6, 48)
    vcpu = rng.choice([8, 16, 32, 64])
    svcs = rng.sample(SERVICES, 4)
    name = f"Solution architecture: {ctx.short}"
    img, d = new_chart(
        2400,
        1600,
        name,
        "Logical view. Production environment, Singapore region.",
        ctx.theme,
        "Architecture review board pack",
        ctx.chart_title,
        ctx.printed_value,
    )

    def box(
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        sub: str = "",
        fill: tuple[int, int, int] = (235, 242, 250),
    ) -> None:
        d.rounded_rectangle((x, y, x + w, y + h), 18, fill=fill, outline=(80, 80, 80), width=3)
        ctext(d, (x + w / 2, y + h / 2 - (18 if sub else 0)), label, font(30, bold=True))
        if sub:
            ctext(d, (x + w / 2, y + h / 2 + 24), sub, font(24), fill=(80, 80, 80))

    box(80, 640, 300, 160, "Citizens and", "businesses", (250, 240, 225))
    box(470, 640, 280, 160, "WAF and CDN")
    box(840, 640, 280, 160, "API gateway", "internet zone")
    d.rounded_rectangle((1210, 240, 1900, 1240), 24, outline=ctx.theme, width=6)
    d.text(
        (1240, 260),
        f"Kubernetes cluster: {nodes} worker nodes",
        font=font(28, bold=True),
        fill=ctx.theme,
    )
    for i, s in enumerate(svcs):
        box(1270, 330 + i * 225, 570, 170, s, f"{rng.randint(2, 12)} replicas")
    box(2000, 360, 320, 180, "Managed PostgreSQL", f"{vcpu} vCPU", (232, 245, 233))
    box(2000, 700, 320, 180, "Object storage", "encrypted", (232, 245, 233))
    box(2000, 1040, 320, 180, "SIEM", "log forwarding", (252, 232, 232))
    _arrow(d, (380, 720), (470, 720))
    _arrow(d, (750, 720), (840, 720))
    _arrow(d, (1120, 720), (1270, 720))
    for y in (450, 790, 1130):
        _arrow(d, (1840, y), (2000, y))
    return img, name, "PNG"


ORG_ROLES = [
    "Head, Platform Engineering",
    "Head, Product Management",
    "Head, Cybersecurity Operations",
    "Head, Data Engineering",
    "Head, Service Design",
    "Head, Programme Office",
    "Lead, Site Reliability",
    "Lead, Vendor Management",
    "Head, Talent and Capability",
    "Lead, Exercise Control",
]


def img_org(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    roles = rng.sample(ORG_ROLES, 5)
    people = [ctx.person() for _ in roles]
    root = ctx.person()
    name = f"Organisation chart: {ctx.short}"
    img, d = new_chart(
        2400,
        1600,
        name,
        f"As at {ctx.date}.",
        ctx.theme,
        "Human resources",
        ctx.chart_title,
        ctx.printed_value,
    )

    def card(cx: int, y: int, who: str, role: str, fill: tuple[int, int, int]) -> None:
        d.rounded_rectangle(
            (cx - 210, y, cx + 210, y + 170),
            18,
            fill=fill,
            outline=(80, 80, 80),
            width=3,
        )
        ctext(d, (cx, y + 58), who, font(32, bold=True))
        for k, line in enumerate(textwrap.wrap(role, 24)[:2]):
            ctext(d, (cx, y + 105 + k * 32), line, font(24), fill=(70, 70, 70))

    card(1200, 240, root, "Programme Director", shade(ctx.theme, 0.7))
    d.line((1200, 410, 1200, 500), fill=(80, 80, 80), width=4)
    xs = [260 + i * 470 for i in range(5)]
    d.line((xs[0], 500, xs[-1], 500), fill=(80, 80, 80), width=4)
    for x, who, role in zip(xs, people, roles):
        d.line((x, 500, x, 580), fill=(80, 80, 80), width=4)
        card(x, 580, who, role, (245, 245, 245))
        for k in range(2):
            y = 830 + k * 210
            d.line((x, y - 40, x, y), fill=(150, 150, 150), width=3)
            card(
                x,
                y,
                ctx.person(),
                rng.choice(["Engineer", "Product Manager", "Analyst", "Designer", "Specialist"]),
                (255, 255, 255),
            )
    return img, name, "PNG"


STICKY_TEXT: dict[str, list[str]] = {
    "Pain points": [
        "Re-enter customer ID on three forms",
        "No status after I submit",
        "Upload fails on large PDF",
        "SMS OTP arrives late",
        "Cannot save and continue",
        "Jargon on eligibility page",
        "Two logins for one service",
        "Payment page times out",
    ],
    "Ideas": [
        "Pre-fill from customer profile",
        "Show a progress tracker",
        "One reminder a week",
        "Chat help in four languages",
        "Save draft on the phone",
    ],
    "Questions": [
        "Who owns the data?",
        "Can divisions share consent?",
        "What is the budget for phase 2?",
        "Offline counter option?",
    ],
}


def img_whiteboard(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    w, h = 2400, 1600
    img = Image.new("RGB", (w, h), (196, 186, 170))
    d = ImageDraw.Draw(img)
    for y in range(h):
        c = int(170 + 30 * y / h)
        d.line((0, y, w, y), fill=(c + 20, c + 12, c))
    d.rectangle((110, 110, 2310, 1470), fill=(90, 90, 90))
    d.rectangle((90, 90, 2290, 1450), fill=(246, 247, 245))
    d.text((140, 120), f"Workshop: {ctx.short}", font=font(46, style="hand"), fill=(30, 60, 150))
    cols = list(STICKY_TEXT)
    colours = [(255, 238, 120), (255, 170, 200), (160, 215, 255), (180, 240, 170)]
    for ci, col in enumerate(cols):
        x0 = 150 + ci * 720
        d.text((x0, 220), col, font=font(44, style="hand"), fill=(40, 40, 40))
        d.line((x0, 280, x0 + 600, 280), fill=(40, 40, 40), width=4)
        pool = [s for s in STICKY_TEXT[col] if s not in ctx.used] or STICKY_TEXT[col]
        notes = rng.sample(pool, min(4, len(pool)))
        ctx.used.update(notes)
        for ni, text in enumerate(notes):
            note = Image.new("RGBA", (300, 250), colours[(ci + ni) % 4] + (255,))
            nd = ImageDraw.Draw(note)
            for li, line in enumerate(textwrap.wrap(text, 14)[:4]):
                nd.text((18, 20 + li * 40), line, font=font(30, style="hand"), fill=(30, 30, 30))
            if col == "Pain points":
                votes = rng.randint(3, 29)
                nd.text((18, 200), f"{votes} votes", font=font(28, bold=True), fill=(180, 0, 0))
            note = note.rotate(rng.uniform(-7, 7), expand=True, resample=Image.BICUBIC)
            px = x0 + (ni % 2) * 330
            py = 320 + (ni // 2) * 330 + rng.randint(-15, 15)
            shadow = Image.new("RGBA", note.size, (0, 0, 0, 70))
            img.paste(shadow, (px + 10, py + 12), note)
            img.paste(note, (px, py), note)
    vignette = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vignette).ellipse((-400, -300, w + 400, h + 300), fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(200))
    img = Image.composite(img, Image.new("RGB", (w, h), (60, 55, 50)), vignette)
    d_final = ImageDraw.Draw(img)
    d_final.rectangle((0, 0, w, 16), fill=ctx.theme)
    _draw_metric_badge(d_final, w, h, ctx.chart_title, ctx.printed_value, ctx.theme)
    cap = f"Photo of the workshop whiteboard, {ctx.short}"
    return img, cap, "JPEG"


def img_memo(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    w, h = 1700, 2200
    page = Image.new("RGB", (w, h), (246, 243, 234))
    d = ImageDraw.Draw(page)
    mono = font(30, style="mono")
    d.text((140, 120), ctx.corpus.company.upper(), font=font(36, bold=True), fill=(30, 30, 30))
    d.line((140, 180, 1560, 180), fill=(30, 30, 30), width=3)
    d.text((140, 220), "MEMORANDUM", font=font(44, bold=True), fill=(30, 30, 30))
    dept = rng.choice(["PROC", "FIN", "CSG", "PEO", "GDT"])
    ref = f"GT/{dept}/26/{rng.randint(100, 9999):04d}"
    author, approver = ctx.person(), ctx.person()
    lines = [
        f"Our ref : {ref}",
        f"Date    : {ctx.date}",
        "To      : Chief Executive (Synthetic)",
        f"From    : {author}",
    ]
    subject = textwrap.wrap(f"Approval to proceed, {ctx.short}", 50)
    lines += [f"Subject : {subject[0]}"] + [f"          {s}" for s in subject[1:]] + [""]
    paras = [
        (
            f"1. This memo seeks approval to proceed with the next phase of "
            f"{ctx.short}. The estimated cost is within the approved budget."
        ),
        "2. The evaluation committee reviewed the proposal and supports it.",
        "3. The team will report progress to the steering committee each month.",
        "4. Please indicate your approval below.",
    ]
    for para in paras:
        lines += textwrap.wrap(para, 60, subsequent_indent="   ") + [""]
    for k, line in enumerate(lines):
        d.text((140, 320 + k * 48), line, font=mono, fill=(35, 35, 35))
    y = 320 + len(lines) * 48 + 60
    d.text((140, y), "Approved by:", font=mono, fill=(35, 35, 35))
    pts = [(420 + t * 14, y + 20 + 25 * math.sin(t / 2.2 + rng.random())) for t in range(40)]
    d.line(pts, fill=(20, 30, 110), width=5)
    d.text((420, y + 80), approver, font=mono, fill=(35, 35, 35))
    approval = f"A-{rng.randint(10000, 99999)}"
    stamp = Image.new("RGBA", (620, 360), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    red = (190, 20, 30, 210)
    sd.rounded_rectangle((10, 10, 610, 350), 30, outline=red, width=10)
    ctext(sd, (310, 100), "APPROVED", font(84, bold=True), fill=red)
    ctext(sd, (310, 200), ctx.date.upper(), font(44, bold=True), fill=red)
    ctext(sd, (310, 280), f"Approval no. {approval}", font(38, bold=True), fill=red)
    stamp = stamp.rotate(rng.uniform(-14, 14), expand=True, resample=Image.BICUBIC)
    page.paste(stamp, (900, min(h - 500, y - 40)), stamp)
    page = page.rotate(
        rng.uniform(-1.2, 1.2),
        expand=False,
        fillcolor=(40, 40, 40),
        resample=Image.BICUBIC,
    )
    d_final = ImageDraw.Draw(page)
    d_final.rectangle((0, 0, w, 16), fill=ctx.theme)
    _draw_metric_badge(d_final, w, h, ctx.chart_title, ctx.printed_value, ctx.theme)
    cap = f"Scanned approval memo, {ctx.short}"
    return page, cap, "JPEG"


ROOMS = [
    "Meeting Room Merlion",
    "Meeting Room Orchid",
    "Collab Zone A",
    "Collab Zone B",
    "Training Room",
    "Operations Centre",
    "Focus Pods",
    "Quiet Room",
    "Huddle Room 1",
    "Huddle Room 2",
    "Exercise Control Room",
    "Server Room",
]


def img_floor(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    level = rng.randint(2, 18)
    site = rng.choice(ctx.corpus.sites) if ctx.corpus.sites else "Headquarters"
    name = f"Level {level} floor plan, {site}"
    if name in ctx.used:
        level += 1
        name = f"Level {level} floor plan, {site}"
    ctx.used.add(name)
    img, d = new_chart(
        2400,
        1600,
        name,
        f"{ctx.short}. Seat counts are design capacity.",
        ctx.theme,
        "Facilities management",
        ctx.chart_title,
        ctx.printed_value,
    )
    rooms = rng.sample(ROOMS, 8)
    seats = [rng.randint(4, 60) for _ in rooms]
    d.rectangle((120, 220, 2280, 1380), outline=(30, 30, 30), width=10)
    d.rectangle((120, 740, 2280, 860), fill=(238, 238, 238))
    ctext(d, (1200, 800), "Corridor", font(30), fill=(120, 120, 120))
    xs = [120, 660, 1200, 1740, 2280]
    for i, (room, n) in enumerate(zip(rooms, seats)):
        x0, x1 = xs[i % 4], xs[i % 4 + 1]
        y0, y1 = (220, 740) if i < 4 else (860, 1380)
        d.rectangle(
            (x0, y0, x1, y1),
            outline=(30, 30, 30),
            width=6,
            fill=shade(ctx.theme, 0.88 if i % 2 else 0.8),
        )
        door_y = y1 if i < 4 else y0
        d.line(((x0 + x1) / 2 - 60, door_y, (x0 + x1) / 2 + 60, door_y), fill="white", width=10)
        for k, line in enumerate(textwrap.wrap(room, 16)):
            ctext(d, ((x0 + x1) / 2, (y0 + y1) / 2 - 50 + k * 42), line, font(34, bold=True))
        ctext(d, ((x0 + x1) / 2, (y0 + y1) / 2 + 60), f"Seats: {n}", font(32))
    d.polygon([(2180, 250), (2210, 330), (2150, 330)], fill=(30, 30, 30))
    ctext(d, (2180, 355), "N", font(30, bold=True))
    return img, name, "PNG"


PHONE_APPS = [
    ("Customer Portal", ["Order status check", "Loyalty claim", "Account registration"]),
    ("Enterprise SSO", ["Biometric verification", "Profile consent", "Device binding"]),
    ("Field Telemetry", ["Sensor install check", "Gateway pairing", "Site photo"]),
    ("Workspace Access", ["Access request", "Device posture", "Token reset"]),
]


def img_phone(ctx: ChartContext) -> tuple[Image.Image, str, str]:
    rng = ctx.rng
    app, items = ctx.pick(PHONE_APPS)
    w, h = 1180, 2400
    img = Image.new("RGB", (w, h), (30, 30, 30))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 40, w - 40, h - 40), 90, fill=(250, 250, 252))
    d.rectangle((0, 0, w, 16), fill=ctx.theme)
    d.text((110, 90), f"{rng.randint(7, 11)}:{rng.randint(10, 59)}", font=font(38, bold=True))
    d.rectangle((40, 170, w - 40, 330), fill=ctx.theme)
    d.text((100, 220), app, font=font(56, bold=True), fill="white")
    statuses = ["Submitted", "In review", "Approved", "Action needed"]
    for k, item in enumerate(items):
        y = 400 + k * 260
        d.rounded_rectangle(
            (90, y, w - 90, y + 220),
            30,
            fill="white",
            outline=(220, 220, 225),
            width=3,
        )
        d.text((130, y + 40), item, font=font(40, bold=True), fill=(30, 30, 30))
        st = rng.choice(statuses)
        d.rounded_rectangle(
            (130, y + 120, 130 + 30 * len(st), y + 175),
            26,
            fill=shade(ctx.theme, 0.8),
        )
        d.text((150, y + 127), st, font=font(30), fill=(40, 40, 40))
    y = 400 + len(items) * 260 + 40
    d.rounded_rectangle(
        (90, y, w - 90, y + 320),
        30,
        fill=(255, 243, 224),
        outline=(230, 150, 30),
        width=4,
    )
    d.text((130, y + 40), ctx.chart_title[:42], font=font(30), fill=(90, 60, 10))
    d.text((130, y + 110), ctx.printed_value, font=font(64, bold=True), fill=(60, 40, 0))
    d.text((130, y + 215), "Verified telemetry metric.", font=font(30), fill=(90, 60, 10))
    d.rounded_rectangle((w / 2 - 160, h - 110, w / 2 + 160, h - 96), 7, fill=(40, 40, 40))
    cap = f"{app} app screenshot from usability test"
    return img, cap, "PNG"


DRAWERS = {
    "line": img_line,
    "bar": img_bar,
    "donut": img_donut,
    "stacked": img_stacked,
    "heatmap": img_heatmap,
    "kpi": img_kpi,
    "gantt": img_gantt,
    "architecture": img_architecture,
    "org": img_org,
    "whiteboard": img_whiteboard,
    "memo": img_memo,
    "floor": img_floor,
    "phone": img_phone,
}
CHART_KINDS: tuple[str, ...] = tuple(DRAWERS.keys())


def make_chart_figures(
    ctx: ChartContext,
    count: int,
    preferred_kinds: Sequence[str] | None = None,
) -> list[FigurePlate]:
    """Build count FigurePlate instances cycling through preferred_kinds and DRAWERS."""
    prefs = list(dict.fromkeys(preferred_kinds or CHART_KINDS))
    extra = [k for k in CHART_KINDS if k not in prefs]
    ctx.rng.shuffle(extra)
    order = (prefs + extra) * max(2, (count // len(CHART_KINDS)) + 2)
    out: list[FigurePlate] = []
    for kind in order[:count]:
        img, caption, fmt = DRAWERS[kind](ctx)
        out.append(FigurePlate(base=img, caption=caption, fmt=fmt, kind=kind))
    return out


def figure_count_for_target(target_bytes: int) -> int:
    """Return a clean figure count between 2 and 12 for target_bytes."""
    mb = 1024 * 1024
    if target_bytes < 256 * 1024:
        return 1
    if target_bytes < 5 * mb:
        return max(2, min(6, target_bytes // (300 * 1024)))
    if target_bytes <= 100 * mb:
        return max(4, min(12, round(target_bytes / (6 * mb))))
    return min(24, max(12, round(target_bytes / (16 * mb))))


def encode_figure_tight(
    fig: FigurePlate,
    target_bytes: int,
    *,
    seed: int = 42,
    scales: dict[int, float] | None = None,
) -> bytes:
    """Encode fig near target_bytes using Image.LANCZOS scaling and a 12% noise grain blend."""
    fig.fmt = "PNG"

    def _render_once(scale: float, grain: int) -> bytes:
        img = fig.base
        if abs(scale - 1.0) > 0.005:
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            img = img.resize((new_w, new_h), Image.LANCZOS)
        if grain > 0:
            # Build a small deterministic tile and resize with NEAREST/BILINEAR or effect_noise
            noise = Image.merge("RGB", [Image.effect_noise(img.size, 64) for _ in range(3)])
            img = Image.blend(img, noise, grain / 100.0)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        fig.size = img.size
        return buf.getvalue()

    if target_bytes < 90_000:
        fig.data = _render_once(0.45, 0)
        return fig.data

    fid = id(fig)
    if scales is not None and fid in scales and fig.data:
        scale = scales[fid] * math.sqrt(target_bytes / len(fig.data))
    else:
        scale = math.sqrt(target_bytes / 2.0 / (fig.base.width * fig.base.height))

    for _ in range(4):
        scale = min(3.2, max(0.25, scale))
        if scales is not None:
            scales[fid] = scale
        fig.data = _render_once(scale, GRAIN)
        ratio = target_bytes / max(1, len(fig.data))
        if 0.96 < ratio < 1.04:
            break
        scale *= math.sqrt(ratio)
    return fig.data
