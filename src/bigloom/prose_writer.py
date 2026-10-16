"""WorldLoom-backed prose generator, risk tables, chart pools, and Excel row definitions."""

from __future__ import annotations

import calendar
import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from worldloom import divisions as wl_divisions
from worldloom import roles as wl_roles
from worldloom.generators import masterdata as wl_masterdata
from worldloom.generators import names as wl_names
from worldloom.narrative import references
from worldloom.narrative.composer import ComposedProvider, measure_noun
from worldloom.render.values import corpus_locale
from worldloom.rng import Rng as WlRng
from worldloom.world import World

MARKING = "OFFICIAL (CLOSED) / SENSITIVE NORMAL - SYNTHETIC TEST DATA"
SHORT_MARK = "SYNTHETIC TEST DATA"

THEME_PALETTE: list[tuple[int, int, int]] = [
    (0, 84, 147),
    (200, 16, 46),
    (0, 128, 96),
    (60, 60, 140),
    (31, 119, 180),
    (148, 103, 189),
    (44, 160, 44),
    (214, 39, 40),
    (230, 120, 0),
    (0, 110, 110),
]


def ensure_narrated_world(world: World) -> World:
    """Ensure world has compiled and narrated ArtifactIRs when intents or scenarios exist."""
    if world.artifact_irs and any(
        s.body for ir in world.artifact_irs for s in ir.sections
    ):
        return world
    try:
        if not world.artifact_intents:
            from worldloom.scenarios import MonthEndClose

            world = world.run(MonthEndClose(period=world.period or "2026-01"))
        if world.artifact_intents:
            return world.narrate(ComposedProvider.for_world(world))
    except (KeyError, ValueError, RuntimeError, TypeError, AttributeError):
        return world
    return world


def _compute_fy_months(start_month: int, period: str) -> list[str]:
    """Compute 12 fiscal month labels from a WorldLoom Locale fiscal_year_start_month."""
    year = 2025
    if period and len(period) >= 4 and period[:4].isdigit():
        year = int(period[:4]) - 1
    months: list[str] = []
    for offset in range(12):
        m = ((start_month - 1 + offset) % 12) + 1
        y = year + ((start_month - 1 + offset) // 12)
        months.append(f"{calendar.month_abbr[m]} {y}")
    return months


def _compute_quarters(period: str) -> list[str]:
    """Compute 4 fiscal quarter labels from a WorldLoom period."""
    yr = 25
    if period and len(period) >= 4 and period[:4].isdigit():
        yr = int(period[:4]) % 100
    return [f"Q{q} FY{yr:02d}" for q in range(1, 5)]


def _extract_world_pools(world: World) -> dict[str, object]:
    """Extract all entity, locale, prose, risk, and chart pools from a WorldLoom World."""
    w = ensure_narrated_world(world)
    loc = corpus_locale(w)
    company = w.company.name
    currency = (w.company.currency or loc.currency or "SGD").strip().upper()
    fy_months = _compute_fy_months(loc.fiscal_year_start_month, w.period or "2026-01")
    quarters = _compute_quarters(w.period or "2026-01")

    given_names: list[str] = []
    surnames: list[str] = []
    people: list[tuple[str, str]] = []
    org_roles: list[str] = []
    for p in w.people:
        if getattr(p, "function", "") != "Merchandising":
            people.append((p.name, p.title))
        if p.title and p.title not in org_roles:
            org_roles.append(p.title)
        parts = p.name.split()
        if parts:
            first = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
            last = parts[-1]
            if first and first not in given_names:
                given_names.append(first)
            if last and last not in surnames:
                surnames.append(last)
    for g in loc.given:
        if g not in given_names:
            given_names.append(g)
    for f in loc.family:
        if f not in surnames:
            surnames.append(f)

    for role_spec in wl_roles._shipped("retail"):
        if role_spec.title not in org_roles:
            org_roles.append(role_spec.title)

    names: dict[str, str] = {}
    units: list[str] = []
    for bu in w.business_units:
        names[bu.id] = bu.name
        units.append(bu.id)
    categories: list[str] = []
    for cat in getattr(w, "categories", ()):
        names[cat.id] = cat.name
        categories.append(cat.id)
    for cc in w.cost_centres:
        names[cc.id] = cc.name
        if not categories:
            categories.append(cc.id)

    part_labels: list[str] = []
    for label in (
        [bu.name for bu in w.business_units]
        + [cc.name for cc in w.cost_centres]
        + [cat.name for cat in getattr(w, "categories", ())]
        + [u.name for pool in wl_divisions.POOLS.values() for u in pool]
        + [c.name for pool in wl_divisions.POOLS.values() for u in pool for c in u.categories]
    ):
        if label and label not in part_labels:
            part_labels.append(label)

    systems: list[str] = []
    for s in w.systems:
        if s.name and s.name not in systems:
            systems.append(s.name)
    for sys_pool in (wl_names.ERP, wl_names.PLATFORM, wl_names.MDM, wl_names.COMMERCE, wl_names.POS):
        for s_name in sys_pool:
            if s_name not in systems:
                systems.append(s_name)

    services: list[str] = []
    for svc in w.services:
        if svc.name and svc.name not in services:
            services.append(svc.name)
    for sys_name in systems:
        slug = re.sub(r"[^a-z0-9]+", "-", sys_name.lower()).strip("-")
        if slug and slug not in services:
            services.append(slug)

    sites: list[str] = [s.name for s in w.sites if s.name]
    for city, country in loc.cities:
        loc_label = f"{city}, {country}"
        if loc_label not in sites:
            sites.append(loc_label)

    vendors: list[str] = []
    md = getattr(w, "_masterdata", None)
    if md is None or not getattr(md, "vendors", None) or not getattr(md, "skus", None):
        seed_val = int(getattr(w, "seed", 42) or 42)
        md = wl_masterdata.generate(
            WlRng(seed_val).derive("masterdata"),
            vendors=20,
            customers=20,
            skus=20,
            locale=loc,
            categories=part_labels[:6],
        )
    for v in md.vendors:
        if v.name and v.name not in vendors:
            vendors.append(v.name)
    for cp in getattr(w, "counterparties", ()):
        cp_name = getattr(cp, "name", "")
        if cp_name and cp_name not in vendors:
            vendors.append(cp_name)

    skus: list[tuple[str, str, str, float]] = [
        (sku.id, sku.name, sku.category, float(sku.unit_price)) for sku in md.skus
    ]
    bt_rng = WlRng(int(getattr(w, "seed", 42) or 42)).derive("brand_tokens")
    quals = bt_rng.derive("qualifiers").shuffled(wl_masterdata._VOCAB["sku_qualifiers"])
    nouns = bt_rng.derive("nouns").shuffled(wl_masterdata._VOCAB["sku_nouns"])
    brand_tokens: list[str] = [
        f"{wl_names.COMPANY_FIRST[i % len(wl_names.COMPANY_FIRST)]} "
        f"{quals[i % len(quals)]} {nouns[i % len(nouns)]}"
        for i in range(max(len(wl_names.COMPANY_FIRST), 32))
    ]

    facts_by_id = {f.id: f for f in w.facts}
    narrated_sentences: list[str] = []
    sections: list[str] = []
    chart_titles: list[str] = []
    for ir in w.artifact_irs:
        ir_title = ir.title.replace("&", "and") if ir.title else ""
        if ir_title and ir_title not in sections:
            sections.append(ir_title)
        for sec in ir.sections:
            sec_heading = sec.heading.replace("&", "and") if sec.heading else ""
            if sec_heading and sec_heading not in sections:
                sections.append(sec_heading)
            if sec.body:
                resolved = references.substitute(sec.body, facts_by_id, locale=loc)
                for chunk in re.split(r"(?<=[.!?])\s+", resolved.strip()):
                    clean = chunk.strip().replace("&", "and")
                    if len(clean) >= 20 and clean not in narrated_sentences:
                        narrated_sentences.append(clean)
            for ch in sec.charts or ():
                ch_title = ch.title.replace("&", "and") if ch.title else ""
                if ch_title and ch_title not in chart_titles:
                    chart_titles.append(ch_title)

    if "Financial overview" not in sections:
        sections.insert(min(4, len(sections)), "Financial overview")

    lore_items: list[str] = []
    for lore_entry in w.lore:
        assertion = getattr(lore_entry, "assertion", "").strip()
        if assertion:
            lore_items.append(assertion)
            if assertion not in narrated_sentences:
                narrated_sentences.append(assertion)

    event_summaries: list[str] = []
    for ev in w.events:
        summary = getattr(ev, "summary", "").strip()
        if summary:
            event_summaries.append(summary)
            if summary not in narrated_sentences:
                narrated_sentences.append(summary)

    risks: list[tuple[str, str]] = []
    mitigations: list[str] = []
    severities = ("High", "Medium", "Low")
    for idx, text in enumerate(lore_items + event_summaries):
        short_clause = text.split(".")[0].strip()[:72]
        if short_clause and all(short_clause != r[0] for r in risks):
            risks.append((short_clause, severities[idx % len(severities)]))
    for f in w.facts:
        if f.text_value and f.kind.startswith(("ops.cause", "ops.incident", "ops.root_cause")):
            clause = str(f.text_value).split(".")[0].strip()[:72]
            if clause and all(clause != r[0] for r in risks):
                risks.append((clause, "High"))
        if f.text_value and f.kind.startswith(("ops.workaround", "ops.remediation")):
            clause = str(f.text_value).split(".")[0].strip()[:72]
            if clause and clause not in mitigations:
                mitigations.append(clause)
    for svc in services[:6]:
        mit = f"Automated control review on {svc}"
        if mit not in mitigations:
            mitigations.append(mit)
    for bu_label in part_labels[:6]:
        r_text = f"Operational variance across {bu_label}"
        if all(r_text != r[0] for r in risks):
            risks.append((r_text, severities[len(risks) % len(severities)]))

    measure_nouns: list[str] = []
    for f in w.facts:
        noun = measure_noun(f.kind).strip()
        if noun and noun not in measure_nouns:
            measure_nouns.append(noun)

    revenue_slots: dict[tuple[str, str], list[float | None]] = {}
    for fact in w.facts:
        kind = getattr(fact, "kind", "")
        if kind not in ("financial.revenue.actual", "financial.revenue.budget"):
            continue
        val = getattr(fact, "value", None)
        amt = val.get("amount") if isinstance(val, dict) else getattr(val, "amount", val)
        period = getattr(fact, "period", None)
        subject_id = getattr(fact, "subject", None)
        if period and subject_id and isinstance(amt, (int, float)):
            slot = revenue_slots.setdefault((str(subject_id), str(period)), [None, None])
            slot[0 if kind.endswith("actual") else 1] = float(amt)
    revenue: dict[tuple[str, str], tuple[float, float]] = {
        k: (v[0], v[1])
        for k, v in revenue_slots.items()
        if v[0] is not None and v[1] is not None
    }
    if not revenue:
        for idx, u_id in enumerate(units[:4] or ["BU-01"], 1):
            names.setdefault(u_id, part_labels[idx - 1] if idx <= len(part_labels) else u_id)
            revenue[(u_id, fy_months[0].split()[-1])] = (12_400.0 * idx, 12_000.0 * idx)
            revenue[(u_id, fy_months[-1].split()[-1])] = (14_150.0 * idx, 13_750.0 * idx)

    periods = sorted({p for _, p in revenue}) or [
        fy_months[0].split()[-1],
        fy_months[-1].split()[-1],
    ]

    return {
        "company": company,
        "currency": currency,
        "periods": periods,
        "names": names,
        "revenue": revenue,
        "units": units,
        "categories": categories,
        "people": people,
        "systems": systems,
        "sites": sites,
        "part_labels": part_labels,
        "vendors": vendors,
        "given_names": given_names,
        "surnames": surnames,
        "services": services,
        "org_roles": org_roles,
        "fy_months": fy_months,
        "quarters": quarters,
        "narrated_sentences": narrated_sentences,
        "sections": sections,
        "risks": risks,
        "mitigations": mitigations,
        "measure_nouns": measure_nouns,
        "chart_titles": chart_titles,
        "lore_items": lore_items,
        "skus": skus,
        "brand_tokens": brand_tokens,
    }


@dataclass
class ProseCorpus:
    """Grounded WorldLoom entities, locale pools, and narrated prose."""

    company: str = ""
    currency: str = ""
    periods: list[str] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)
    revenue: dict[tuple[str, str], tuple[float, float]] = field(default_factory=dict)
    units: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    people: list[tuple[str, str]] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    sites: list[str] = field(default_factory=list)
    part_labels: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)
    given_names: list[str] = field(default_factory=list)
    surnames: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    org_roles: list[str] = field(default_factory=list)
    fy_months: list[str] = field(default_factory=list)
    quarters: list[str] = field(default_factory=list)
    narrated_sentences: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)
    risks: list[tuple[str, str]] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    measure_nouns: list[str] = field(default_factory=list)
    chart_titles: list[str] = field(default_factory=list)
    lore_items: list[str] = field(default_factory=list)
    skus: list[tuple[str, str, str, float]] = field(default_factory=list)
    brand_tokens: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Derive name and service pools from the given people and systems. Add no default content."""
        for p_name, title in self.people:
            parts = p_name.split()
            if parts and parts[0] not in self.given_names:
                self.given_names.append(parts[0])
            if len(parts) >= 2 and parts[-1] not in self.surnames:
                self.surnames.append(parts[-1])
            if title and title not in self.org_roles:
                self.org_roles.append(title)
        for sys_name in self.systems:
            slug = re.sub(r"[^a-z0-9]+", "-", sys_name.lower()).strip("-")
            if slug and slug not in self.services:
                self.services.append(slug)

    @classmethod
    def from_world(cls, world: World) -> ProseCorpus:
        """Construct a ProseCorpus directly from a WorldLoom World instance."""
        pools = _extract_world_pools(world)
        return cls(**pools)  # type: ignore[arg-type]

    def effective_part_labels(self) -> list[str]:
        """Return at least 10 distinct division, unit, category, or site labels from WorldLoom."""
        seen: list[str] = []
        for item in self.part_labels:
            if item and item not in seen:
                seen.append(item)
        for uid in [*self.units, *self.categories]:
            label = self.names.get(uid, uid)
            if label and label not in seen:
                seen.append(label)
        for site in self.sites:
            if site and site not in seen:
                seen.append(site)
        return seen


def format_money(value: float, currency: str = "SGD") -> str:
    """Format a numeric value in thousands with the given currency code."""
    return f"{currency} {value:,.0f}k"


class Writer:
    """Generate deterministic multi-sentence paragraphs grounded in WorldLoom entities and prose."""

    def __init__(self, rng: random.Random, corpus: ProseCorpus) -> None:
        self.rng = rng
        self.corpus = corpus
        self.pool: list[str] = []

    def _build_sentence_pool(self) -> list[str]:
        """Combine WorldLoom ComposedProvider sentences with entity-grounded statements."""
        r = self.rng
        c = self.corpus
        parts = c.effective_part_labels()
        people = c.people or [(f"{c.given_names[0]} {c.surnames[0]}", c.org_roles[0])]
        systems = c.systems
        services = c.services
        sites = c.sites
        vendors = c.vendors
        months = c.fy_months
        measures = c.measure_nouns
        sections = c.sections

        out: list[str] = list(c.narrated_sentences)
        for idx in range(max(24, len(parts) * 2)):
            unit = parts[idx % len(parts)]
            peer = parts[(idx + 1) % len(parts)]
            person, role = people[idx % len(people)]
            sys_name = systems[idx % len(systems)]
            svc_name = services[idx % len(services)]
            site_name = sites[idx % len(sites)]
            vendor_name = vendors[idx % len(vendors)]
            month = months[idx % len(months)]
            measure = measures[idx % len(measures)]
            sec_title = sections[idx % len(sections)]
            amt = f"{r.randint(25, 950)},000"
            pct = r.randint(4, 96)
            n = r.randint(3, 58)
            n2 = r.randint(60, 140)
            avail = f"{r.uniform(99.5, 99.99):.2f}"
            out.extend(
                [
                    (
                        f"In {month}, {unit} reviewed {measure} performance with {person} "
                        f"({role}) across {site_name}."
                    ),
                    (
                        f"{unit} completed {n} of {n2} scheduled milestones on {sys_name} "
                        f"and reconciled {svc_name} telemetry for {sec_title}."
                    ),
                    (
                        f"Contracted support with {vendor_name} for {sys_name} remained within "
                        f"the {c.currency} {amt} allocation during {month}."
                    ),
                    (
                        f"Service availability on {svc_name} reached {avail}% while {peer} "
                        f"closed {pct}% of tracked action items at {site_name}."
                    ),
                ]
            )
        r.shuffle(out)
        return out

    def sentence(self) -> str:
        """Return one grounded sentence from the WorldLoom narrative and entity pool."""
        if not self.pool:
            self.pool = self._build_sentence_pool()
        return self.pool.pop()

    def paragraph(self, n: int = 0) -> str:
        """Return a paragraph with n sentences (or 3 to 5 sentences when n is 0)."""
        count = n or self.rng.randint(3, 5)
        return " ".join(self.sentence() for _ in range(count))


RowMaker = Callable[[random.Random, int], list[object]]


def sheet_definition(
    kind: str,
    corpus: ProseCorpus,
) -> tuple[list[str], RowMaker, int, int, str, str]:
    """Return columns, row generator, ID col, probe col, probe label, and row noun from WorldLoom."""
    cats = [corpus.names.get(c, c) for c in corpus.categories] or corpus.effective_part_labels()[:4]
    parts = corpus.effective_part_labels()
    people = [p[0] for p in corpus.people] or [
        f"{g} {s}" for g, s in zip(corpus.given_names[:4], corpus.surnames[:4])
    ]
    ccy = corpus.currency
    months = corpus.fy_months
    measures = [m.capitalize() for m in corpus.measure_nouns[:8]] or [
        s.heading for s in ()
    ] or parts[:6]

    if kind == "budget":
        cols = [
            "Line ID",
            "Period",
            "Month",
            "Category",
            "Business unit",
            "Cost centre",
            "Account code",
            "Measure",
            f"Budget ({ccy})",
            f"Committed ({ccy})",
            f"Actual ({ccy})",
            f"Variance ({ccy})",
        ]

        def row_budget(r: random.Random, i: int) -> list[object]:
            b = round(r.uniform(5_000, 900_000), 2)
            a = round(b * r.uniform(0.4, 1.15), 2)
            return [
                f"BUL-{i:07d}",
                r.choice(corpus.periods),
                r.choice(months),
                r.choice(cats),
                r.choice(parts),
                f"CC-{r.randint(100, 999)}",
                f"{r.choice([5101, 5203, 5310, 5420, 6105])}",
                r.choice(measures),
                b,
                round(b * r.uniform(0.5, 1.0), 2),
                a,
                round(b - a, 2),
            ]

        return cols, row_budget, 0, 10, f"actual spend ({ccy})", "budget lines"

    if kind == "procurement":
        cols = [
            "PO number",
            "Contract reference",
            "Category",
            "Business unit",
            "Vendor",
            "Site",
            "Award date",
            f"Contract value ({ccy})",
            "Status",
            "Owner",
        ]

        def row_proc(r: random.Random, i: int) -> list[object]:
            return [
                f"4500{i:07d}",
                f"CNT-{r.randint(100000, 999999)}",
                r.choice(cats),
                r.choice(parts),
                r.choice(corpus.vendors),
                r.choice(corpus.sites),
                f"2026-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}",
                round(r.uniform(800, 2_500_000), 2),
                r.choice(["Committed", "Closed", "Reviewed"]),
                r.choice(people),
            ]

        return cols, row_proc, 0, 7, f"contract value ({ccy})", "purchase orders"

    if kind == "pipeline":
        cols = [
            "Run ID",
            "Service",
            "System",
            "Business unit",
            "Started (SGT)",
            "Duration (s)",
            "Status",
            "Triggered by",
            "Commit",
        ]

        def row_pipe(r: random.Random, i: int) -> list[object]:
            first = r.choice(corpus.given_names).split()[0].lower()
            last = r.choice(corpus.surnames).split()[-1].lower()
            return [
                f"run-{i:08d}",
                r.choice(corpus.services),
                r.choice(corpus.systems),
                r.choice(parts),
                f"2026-05-{r.randint(1, 31):02d} {r.randint(0, 23):02d}:{r.randint(0, 59):02d}",
                r.randint(12, 3600),
                r.choice(["verified"] * 6 + ["delayed", "superseded"]),
                f"{first}.{last}",
                f"{r.getrandbits(28):07x}",
            ]

        return cols, row_pipe, 0, 5, "duration in seconds", "pipeline runs"

    cols = [
        "Event ID",
        "Timestamp (SGT)",
        "Business unit",
        "System",
        "Service",
        "Status",
        "Latency (ms)",
        "Site",
    ]

    def row_auth(r: random.Random, i: int) -> list[object]:
        return [
            f"ATX{i:010d}",
            (
                f"2026-{r.randint(1, 12):02d}-{r.randint(1, 28):02d} "
                f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}"
            ),
            r.choice(parts),
            r.choice(corpus.systems),
            r.choice(corpus.services),
            r.choice(["Verified"] * 9 + ["Exception"]),
            r.randint(90, 4000),
            r.choice(corpus.sites),
        ]

    return cols, row_auth, 0, 6, "latency in milliseconds", "transactions"
