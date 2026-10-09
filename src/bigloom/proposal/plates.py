"""Grained figure plate drawers and batched JPEG weight encoder for bigloom proposal."""

from __future__ import annotations

import concurrent.futures as cf
import io
import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .facts import WorldEntities
from .spec import ProposalSpec

W, H = 2400, 1500
GRAIN = 12
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
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
    """Measure rendered width and height of text."""
    box = d.textbbox((0, 0), text, font=f)
    return int(box[2] - box[0]), int(box[3] - box[1])


def ctext(
    d: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    f: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = (20, 20, 20),
) -> None:
    """Draw centered text at xy."""
    w, h = text_size(d, text, f)
    d.text((xy[0] - w / 2, xy[1] - h / 2), text, font=f, fill=fill)


def header(
    title: str,
    subtitle: str,
    spec: ProposalSpec,
    entities: WorldEntities,
    theme: tuple[int, int, int] = (0, 84, 147),
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a 2400x1500 RGB plate canvas with header, agency attribution, and marking."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 18), fill=theme)
    d.text((70, 40), title, font=font(46, bold=True), fill=(25, 25, 25))
    d.text((70, 104), subtitle, font=font(28), fill=(100, 100, 100))
    d.text(
        (70, H - 54),
        f"Source: {entities.agency_name}, {spec.office}",
        font=font(22),
        fill=(120, 120, 120),
    )
    mw, _ = text_size(d, entities.short_mark, font(22, bold=True))
    d.text(
        (W - 70 - mw, H - 54),
        entities.short_mark,
        font=font(22, bold=True),
        fill=(170, 0, 0),
    )
    return img, d


def kind_zone(
    rng: random.Random,
    idx: int,
    spec: ProposalSpec,
    entities: WorldEntities,
    value: str | None = None,
) -> tuple[Image.Image, str, str, str]:
    """Draw a master plan zoning plate with a site area fact."""
    zone = rng.choice(entities.zones)
    value = value or f"{rng.randint(18, 140)} ha"
    img, d = header(
        f"Plate {idx}: Master plan zoning, {zone} precinct",
        "Indicative land parcels for the digital twin pilot",
        spec,
        entities,
    )
    d.rectangle((70, 1080, W - 70, H - 90), fill=(170, 205, 235))
    pts = [(70, 1080)] + [
        (70 + i * 230, 1060 + rng.randint(-40, 30)) for i in range(1, 10)
    ]
    pts += [(W - 70, 1080)]
    d.line(pts, fill=(60, 90, 120), width=8)
    x = 120
    colors = [
        (214, 232, 200),
        (250, 225, 190),
        (230, 210, 240),
        (255, 240, 170),
        (205, 225, 245),
    ]
    for i in range(5):
        w = rng.randint(300, 420)
        d.rectangle((x, 220, x + w, 1000), fill=colors[i], outline=(80, 80, 80), width=4)
        label = zone if i == 2 else f"Parcel {chr(65 + i)}{rng.randint(1, 9)}"
        ctext(d, (x + w / 2, 560), label, font(30, bold=True))
        if i == 2:
            ctext(
                d,
                (x + w / 2, 640),
                f"Site area: {value}",
                font(40, bold=True),
                (150, 0, 0),
            )
        else:
            ctext(d, (x + w / 2, 640), f"{rng.randint(5, 60)} ha", font(28))
        x += w + 40
    q = (
        f"In {spec.doc_ref}, the master plan zoning plate for the {zone} precinct "
        f"shows a site area for {zone}. What is that site area?"
    )
    return img, f"Master plan zoning, {zone} precinct", q, value


def kind_gantt(
    rng: random.Random,
    idx: int,
    spec: ProposalSpec,
    entities: WorldEntities,
    value: str | None = None,
) -> tuple[Image.Image, str, str, str]:
    """Draw a programme phasing Gantt chart with a phase end year fact."""
    phase = rng.choice(entities.phases)
    value = value or str(rng.randint(2031, 2042))
    img, d = header(
        f"Plate {idx}: Programme phasing, 2026 to 2045",
        "Indicative delivery windows for each phase",
        spec,
        entities,
    )
    x0, x1 = 900, W - 100
    years = list(range(2026, 2046))
    for i, y in enumerate(years):
        x = x0 + (x1 - x0) * i / len(years)
        d.line((x, 200, x, 1300), fill=(225, 225, 225), width=2)
        if y % 2 == 0:
            ctext(d, (x + 20, 180), str(y), font(22))
    for r, ph in enumerate(entities.phases):
        y = 260 + r * 170
        d.text((70, y + 20), ph, font=font(26, bold=(ph == phase)), fill=(30, 30, 30))
        start = 2026 + r * 2 + rng.randint(0, 1)
        end = int(value) if ph == phase else min(2045, start + rng.randint(3, 8))
        start = min(start, end - 1)
        xs = x0 + (x1 - x0) * (start - 2026) / len(years)
        xe = x0 + (x1 - x0) * (end + 1 - 2026) / len(years)
        d.rectangle(
            (xs, y, xe, y + 80),
            fill=(0, 110, 160) if ph == phase else (140, 170, 200),
        )
        d.text(
            (xe + 12, y + 22),
            f"ends {end}",
            font=font(24, bold=(ph == phase)),
            fill=(40, 40, 40),
        )
    q = (
        f"In {spec.doc_ref}, the programme phasing chart shows an end year for "
        f"'{phase}'. What is that end year?"
    )
    return img, "Programme phasing, 2026 to 2045", q, value


def kind_budget(
    rng: random.Random,
    idx: int,
    spec: ProposalSpec,
    entities: WorldEntities,
    value: str | None = None,
) -> tuple[Image.Image, str, str, str]:
    """Draw a work package capital cost bar chart with a package cost fact."""
    pkg = rng.choice(entities.packages)
    ccy = entities.currency
    value = value or f"{ccy} {rng.randint(12, 95)}.{rng.randint(1, 9)}m"
    img, d = header(
        f"Plate {idx}: Capital cost by work package",
        f"Indicative capital cost, {ccy} million",
        spec,
        entities,
    )
    base, top = 1300, 260
    bw = (W - 300) / len(entities.packages)
    for i, p in enumerate(entities.packages):
        if p == pkg:
            v = float(value.split()[1][:-1])
        else:
            v = rng.randint(10, 95) + rng.randint(1, 9) / 10
        h = (base - top) * v / 100
        x = 150 + i * bw
        d.rectangle(
            (x + 20, base - h, x + bw - 20, base),
            fill=(0, 110, 160) if p == pkg else (150, 180, 205),
        )
        ctext(
            d,
            (x + bw / 2, base - h - 30),
            f"{ccy} {v:.1f}m",
            font(24, bold=(p == pkg)),
        )
        for j, line in enumerate(p.split(" ", 1)):
            ctext(d, (x + bw / 2, base + 40 + j * 32), line, font(22))
    d.line((140, base, W - 140, base), fill=(60, 60, 60), width=4)
    q = (
        f"In {spec.doc_ref}, the capital cost chart shows a value for the "
        f"'{pkg}' work package. What is that value?"
    )
    return img, "Capital cost by work package", q, value


def kind_render(
    rng: random.Random,
    idx: int,
    spec: ProposalSpec,
    entities: WorldEntities,
    value: str | None = None,
) -> tuple[Image.Image, str, str, str]:
    """Draw an aerial massing study render plate with a height control fact."""
    zone = rng.choice(entities.zones)
    value = value or f"{rng.randint(60, 180)} m"
    img, d = header(
        f"Plate {idx}: Aerial view, {zone} (indicative render)",
        "Massing study for the digital twin reference model",
        spec,
        entities,
    )
    for y in range(160, 900):
        c = int(170 + 70 * (y - 160) / 740)
        d.line((0, y, W, y), fill=(c - 40, c - 10, 255))
    d.rectangle((0, 900, W, H - 90), fill=(60, 120, 170))
    x = 80
    tallest: tuple[float, int] | None = None
    while x < W - 200:
        w = rng.randint(90, 200)
        h = rng.randint(200, 620)
        shade = rng.randint(170, 230)
        d.rectangle(
            (x, 900 - h, x + w, 900),
            fill=(shade, shade, shade),
            outline=(90, 90, 90),
            width=3,
        )
        if tallest is None or h > tallest[1]:
            tallest = (x + w / 2, h)
        x += w + rng.randint(10, 60)
    assert tallest is not None
    tx, th = tallest
    d.line((tx, 900 - th - 10, tx, 900 - th - 120), fill=(150, 0, 0), width=5)
    ctext(
        d,
        (tx, 900 - th - 150),
        f"Height control: {value}",
        font(38, bold=True),
        (150, 0, 0),
    )
    q = (
        f"In {spec.doc_ref}, the aerial render of {zone} marks a height control "
        "on the tallest block. What is that height control?"
    )
    return img, f"Aerial view, {zone} (indicative render)", q, value


def kind_section(
    rng: random.Random,
    idx: int,
    spec: ProposalSpec,
    entities: WorldEntities,
    value: str | None = None,
) -> tuple[Image.Image, str, str, str]:
    """Draw a coastal protection cross-section plate with a seawall crest level fact."""
    zone = rng.choice(entities.zones)
    value = value or f"+{rng.randint(4, 6)}.{rng.randint(0, 9)} m CD"
    img, d = header(
        f"Plate {idx}: Coastal protection cross-section at {zone}",
        "Typical seawall profile with sensor positions",
        spec,
        entities,
    )
    d.rectangle((70, 1000, W - 70, H - 90), fill=(170, 205, 235))
    wall = [
        (900, 1300),
        (1150, 500),
        (1350, 500),
        (1700, 1000),
        (W - 70, 1000),
        (W - 70, 1300),
    ]
    d.polygon(wall, fill=(190, 180, 160), outline=(80, 70, 60))
    d.line((1150, 470, 1350, 470), fill=(150, 0, 0), width=5)
    ctext(d, (1250, 420), f"Crest level {value}", font(40, bold=True), (150, 0, 0))
    for s in range(4):
        x = 1180 + s * 120
        d.ellipse((x, 560 + s * 100, x + 40, 600 + s * 100), fill=(255, 160, 0))
    d.text(
        (120, 800),
        f"Mean sea level +{rng.randint(1, 2)}.{rng.randint(0, 9)} m CD",
        font=font(28),
        fill=(30, 60, 90),
    )
    q = (
        f"In {spec.doc_ref}, the coastal protection cross-section at {zone} shows "
        "a crest level for the seawall. What is that crest level?"
    )
    return img, f"Coastal protection cross-section at {zone}", q, value


def kind_sensors(
    rng: random.Random,
    idx: int,
    spec: ProposalSpec,
    entities: WorldEntities,
    value: str | None = None,
) -> tuple[Image.Image, str, str, str]:
    """Draw an edge sensor deployment plan plate with a sensor device count fact."""
    zone = rng.choice(entities.zones)
    kinds = [
        "Air quality sensors",
        "Flood level gauges",
        "Footfall counters",
        "Noise monitors",
        "Smart lamp posts",
    ]
    key = rng.choice(kinds)
    value = value or f"{rng.randint(120, 1900):,}"
    img, d = header(
        f"Plate {idx}: Edge sensor plan, {zone}",
        "Planned device counts by type (indicative)",
        spec,
        entities,
    )
    dot_colors = [(0, 120, 180), (255, 140, 0), (60, 160, 60), (150, 80, 160)]
    for _ in range(260):
        x, y = rng.randint(100, 1500), rng.randint(220, 1300)
        d.ellipse((x, y, x + 18, y + 18), fill=rng.choice(dot_colors))
    d.rectangle((1620, 240, W - 100, 1100), outline=(80, 80, 80), width=3)
    d.text((1660, 270), "Legend", font=font(32, bold=True), fill=(20, 20, 20))
    for i, k in enumerate(kinds):
        v = value if k == key else f"{rng.randint(120, 1900):,}"
        d.text(
            (1660, 360 + i * 140),
            f"{k}: {v}",
            font=font(28, bold=(k == key)),
            fill=(20, 20, 20),
        )
    q = (
        f"In {spec.doc_ref}, the edge sensor plan for {zone} gives a count of "
        f"'{key}'. What is that count?"
    )
    return img, f"Edge sensor plan, {zone}", q, value


KINDS = (kind_zone, kind_gantt, kind_budget, kind_render, kind_section, kind_sensors)


def encode_job(args: tuple[bytes, tuple[int, int], int]) -> tuple[bytes, tuple[int, int]]:
    """Encode one plate image near its target byte budget with pixel grain as JPEG."""
    raw, size, budget = args
    base = Image.frombytes("RGB", size, raw)
    scale = math.sqrt(budget / 1.6 / (base.width * base.height))
    data, out_size = b"", size
    for _ in range(4):
        scale = min(3.0, max(0.3, scale))
        img = base.resize(
            (max(64, int(base.width * scale)), max(64, int(base.height * scale))),
            Image.Resampling.LANCZOS,
        )
        noise = Image.merge("RGB", [Image.effect_noise(img.size, 64) for _ in range(3)])
        img = Image.blend(img, noise, GRAIN / 100)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        data, out_size = buf.getvalue(), img.size
        ratio = budget / max(1, len(data))
        if 0.93 < ratio < 1.07:
            break
        scale *= math.sqrt(ratio)
    return data, out_size


@dataclass
class Fig:
    """One rendered proposal figure plate and its encoded JPEG bytes."""

    caption: str
    question: str
    answer: str
    base: Image.Image
    state: tuple[object, ...] = ()
    data: bytes = b""
    size: tuple[int, int] = (0, 0)


def make_figs(
    rng: random.Random,
    count: int,
    spec: ProposalSpec,
    entities: WorldEntities,
) -> list[Fig]:
    """Draw `count` base figure plates cycling across the six plate drawers."""
    out: list[Fig] = []
    for i in range(count):
        state = rng.getstate()
        drawer = KINDS[i % len(KINDS)]
        img, cap, q, a = drawer(rng, i + 1, spec, entities)
        out.append(Fig(caption=cap, question=q, answer=a, base=img, state=state))
    return out


def make_trap_figs(
    figs: list[Fig],
    picks: dict[str, int],
    spec: ProposalSpec,
    entities: WorldEntities,
    *,
    seed: int = 2026,
    budget: int = 120_000,
) -> list[tuple[str, Fig]]:
    """Re-draw selected plates from their saved RNG state with draft canary values."""
    trap_rng = random.Random(seed + 99)
    trap_figs: list[tuple[str, Fig]] = []
    for where, idx in picks.items():
        drawer = KINDS[idx % len(KINDS)]
        alt = figs[idx].answer
        while alt == figs[idx].answer:
            _, _, _, alt = drawer(trap_rng, 0, spec, entities)
        r = random.Random()
        r.setstate(figs[idx].state)
        img, cap, q, a = drawer(r, idx + 1, spec, entities, alt)
        f = Fig(caption=cap, question=q, answer=a, base=img)
        f.data, f.size = encode_job((f.base.tobytes(), f.base.size, budget))
        trap_figs.append((where, f))
    return trap_figs


def encode_all(figs: list[Fig], budget: int, workers: int) -> None:
    """Encode all figure plates in bounded batches so peak memory stays low."""
    batch = max(workers * 4, 16)
    with cf.ThreadPoolExecutor(max(1, workers)) as pool:
        for s in range(0, len(figs), batch):
            part = figs[s : s + batch]
            jobs = [(f.base.tobytes(), f.base.size, budget) for f in part]
            for f, (data, size) in zip(part, pool.map(encode_job, jobs)):
                f.data, f.size = data, size
            del jobs
