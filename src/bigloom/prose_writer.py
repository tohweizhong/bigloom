"""Grounded multi-paragraph prose generator, risk tables, and Excel row definitions."""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field

MARKING = "OFFICIAL (CLOSED) / SENSITIVE NORMAL - SYNTHETIC TEST DATA"
SHORT_MARK = "SYNTHETIC TEST DATA"
DEFAULT_AGENCY = "Apex Enterprise Group (Synthetic)"

FY_MONTHS = [
    "Apr 2025",
    "May 2025",
    "Jun 2025",
    "Jul 2025",
    "Aug 2025",
    "Sep 2025",
    "Oct 2025",
    "Nov 2025",
    "Dec 2025",
    "Jan 2026",
    "Feb 2026",
    "Mar 2026",
]
QUARTERS = ["Q1 FY25", "Q2 FY25", "Q3 FY25", "Q4 FY25"]
AGENCIES = [
    "Core Platform",
    "Cloud Operations",
    "Customer Channels",
    "Data Analytics",
    "Risk & Compliance",
    "Treasury Services",
    "Supply Chain",
    "Identity Security",
    "Field Operations",
    "Digital Commerce",
    "Enterprise Architecture",
    "Service Management",
]
GIVEN = [
    "Jia Hui",
    "Wei Jie",
    "Nur Aisyah",
    "Arun",
    "Hui Ling",
    "Zhi Hao",
    "Kumaran",
    "Mei Ling",
    "Irfan",
    "Shu Fen",
    "Vikram",
    "Yong Sheng",
    "Farah",
    "Clement",
    "Joanne",
    "Benjamin",
    "Charmaine",
    "Hazwan",
    "Pei Shan",
    "Gopal",
    "Sharon",
    "Terence",
    "Amirah",
    "Desmond",
]
SURNAMES = [
    "Tan",
    "Lim",
    "Lee",
    "Ng",
    "Wong",
    "Goh",
    "Chua",
    "Koh",
    "Teo",
    "Ong",
    "Rahman",
    "Ismail",
    "Kumar",
    "Pillai",
    "Singh",
    "Menon",
    "Yusof",
    "Chandran",
    "Seah",
    "Quek",
    "Low",
    "Foo",
]
VENDOR_A = [
    "Meridian",
    "Straits",
    "Vertex",
    "Kallang",
    "Orchid",
    "Horizon",
    "Vanguard",
    "Summit",
    "Marina",
    "Harbourfront",
    "Vector",
    "Equator",
    "Quay",
    "Tanjong",
    "Catalyst",
    "Nexus",
    "Keppel",
]
VENDOR_B = [
    "Data Systems",
    "Cloud Solutions",
    "Digital Works",
    "InfoTech",
    "Cyber Labs",
    "Analytics",
    "Integration Services",
    "Software",
    "Network Services",
    "Consulting",
    "Managed Services",
    "Design Studio",
]

SENTENCES = [
    "{unit} completed {n} of {n2} planned milestones in {month}.",
    "The team moved {n} workloads from on-premise hosting to the commercial cloud this quarter.",
    "{person}, {role}, chairs the fortnightly working group.",
    "Business units raised {n} service requests through the {system} in {month}.",
    "The median time to resolve a priority 2 incident fell to {hours} hours.",
    "The programme follows the enterprise policy on cloud security and data classification.",
    "{agency} joined the pilot in {month} and onboarded {n} staff in the first two weeks.",
    "We expect the remaining work to complete by {date}, if vendor resources stay available.",
    "The second phase uses a formal quotation on the procurement portal, because the estimated value is below {currency} {amt}.",
    "The steering committee approved a contingency of {pct}% of the phase budget.",
    "User research sessions took place at {site} with {n} participants.",
    "Three risks stay open. The highest is the dependency on legacy interfaces in the {system}.",
    "Service availability for the quarter was {avail}% against a target of 99.90%.",
    "All production changes now go through the automated CI/CD pipeline with security scans.",
    "The data classification for this dataset is Confidential (Cloud-Eligible).",
    "Staff reported that the new flow saves about {mins} minutes for each transaction.",
    "{unit} will give the next update to the Management Committee in {month}.",
    "The vendor delivered release {ver} on {date}. It fixed {n} defects.",
    "Training uptake reached {pct}% of the target group by the end of {month}.",
    "The team retired {n} legacy servers and released {n2} vCPU of capacity.",
    "Cost avoidance for the year is approximately {currency} {amt}.",
    "An internal audit by {person} found no high-severity issues in the change process.",
    "The helpdesk now answers {pct}% of chats within two minutes.",
    "The architecture review board endorsed the design on {date}.",
    "Monitoring alerts go to the on-call roster through the central observability stack.",
    "The team reviews access rights for privileged accounts every {days} days.",
    "Feedback from {agency} teams was positive, with a satisfaction score of {score} out of 5.",
    "The next phase extends the service to {n} more business units.",
    "Data from the pilot stays in the primary region of the commercial cloud provider.",
    "A tabletop exercise on {date} tested the recovery plan for the {system}.",
    "The design team reduced the form from {n2} fields to {n} fields.",
    "The vulnerability backlog fell by {pct}% after the patch sprint in {month}.",
    "{person} owns the benefits tracking for this workstream.",
    "Two divisions asked for a later migration window. The programme office agreed.",
    "The team measures adoption as the number of monthly active users.",
    "Licence costs change from a perpetual model to a subscription model from {month}.",
    "The pilot used synthetic data only. No production records left the corporate network.",
    "Load tests reached {n} requests each second with no errors.",
    "Accessibility tests followed the enterprise digital service standards checklist.",
    "The recovery point objective for the service is {mins} minutes.",
]

RISKS: list[tuple[str, str]] = [
    ("Vendor resources are not sufficient", "Medium"),
    ("Legacy interfaces delay integration", "High"),
    ("Divisions are not ready to migrate", "Medium"),
    ("Budget overrun in phase 2", "Low"),
    ("Security findings delay go-live", "High"),
    ("Low adoption by operational teams", "Medium"),
    ("Key staff leave the team", "Low"),
]

MITIGATIONS: list[str] = [
    "Weekly vendor review",
    "Early interface tests",
    "Division readiness checklist",
    "Monthly cost review",
    "Early penetration test slot booked",
    "Change champions in each division",
    "Handover notes and pairing",
]

DEFAULT_SECTIONS: list[str] = [
    "Executive summary",
    "Programme background",
    "Current operational performance",
    "Architecture and platform controls",
    "Financial overview",
    "Risks and mitigations",
    "Implementation roadmap",
]

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


@dataclass
class ProseCorpus:
    """Grounded WorldLoom entities used by the prose and chart writers."""

    company: str = DEFAULT_AGENCY
    currency: str = "SGD"
    periods: list[str] = field(default_factory=lambda: ["FY2025", "FY2026"])
    names: dict[str, str] = field(default_factory=dict)
    revenue: dict[tuple[str, str], tuple[float, float]] = field(default_factory=dict)
    units: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    people: list[tuple[str, str]] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    sites: list[str] = field(default_factory=list)
    part_labels: list[str] = field(default_factory=list)
    vendors: list[str] = field(default_factory=list)

    def effective_part_labels(self) -> list[str]:
        """Return at least 10 distinct division, unit, or site labels for charts and tables."""
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
        for fallback in AGENCIES:
            if len(seen) >= 10:
                break
            if fallback not in seen:
                seen.append(fallback)
        return seen


def format_money(value: float, currency: str = "SGD") -> str:
    """Format a numeric value in thousands with the given currency code."""
    return f"{currency} {value:,.0f}k"


class Writer:
    """Generate deterministic multi-sentence paragraphs grounded in ProseCorpus entities."""

    def __init__(self, rng: random.Random, corpus: ProseCorpus) -> None:
        self.rng = rng
        self.corpus = corpus
        self.pool: list[str] = []

    def _slots(self) -> dict[str, object]:
        r = self.rng
        c = self.corpus
        person, role = r.choice(c.people) if c.people else ("Tan Wei Jie", "Director")
        month = r.choice(FY_MONTHS)
        unit_id = r.choice(c.units) if c.units else ""
        unit_name = c.names.get(unit_id, unit_id or "Platform Engineering Division")
        parts = c.effective_part_labels()
        return {
            "unit": unit_name,
            "n": r.randint(3, 60),
            "n2": r.randint(61, 140),
            "month": month,
            "person": person,
            "role": role,
            "system": r.choice(c.systems) if c.systems else "Core Enterprise Platform",
            "hours": r.randint(2, 20),
            "agency": r.choice(parts),
            "date": f"{r.randint(1, 28)} {r.choice(FY_MONTHS)}",
            "amt": f"{r.randint(20, 900)},000",
            "currency": c.currency,
            "pct": r.randint(5, 95),
            "site": r.choice(c.sites) if c.sites else "Headquarters",
            "avail": f"{r.uniform(99.5, 99.99):.2f}",
            "mins": r.randint(3, 45),
            "ver": f"{r.randint(1, 5)}.{r.randint(0, 12)}",
            "days": r.choice([30, 60, 90]),
            "score": f"{r.uniform(3.6, 4.8):.1f}",
        }

    def sentence(self) -> str:
        """Return one grounded sentence from the shuffled template pool."""
        if not self.pool:
            self.pool = list(SENTENCES)
            self.rng.shuffle(self.pool)
        return self.pool.pop().format(**self._slots())

    def paragraph(self, n: int = 0) -> str:
        """Return a paragraph with n sentences (or 3 to 5 sentences when n is 0)."""
        count = n or self.rng.randint(3, 5)
        return " ".join(self.sentence() for _ in range(count))


def _vendor_name(rng: random.Random, corpus: ProseCorpus) -> str:
    if corpus.vendors:
        return rng.choice(corpus.vendors)
    return f"{rng.choice(VENDOR_A)} {rng.choice(VENDOR_B)} Ltd"


def _repo_names(corpus: ProseCorpus) -> list[str]:
    repos: list[str] = []
    for sys_name in corpus.systems:
        slug = re.sub(r"[^a-z0-9]+", "-", sys_name.lower()).strip("-")
        if slug:
            repos.append(slug)
    defaults = [
        "core-portal-web",
        "identity-auth-core",
        "partner-gateway",
        "cloud-landing-zone",
        "platform-helm-charts",
        "assistant-backend",
        "telemetry-ingest",
        "notify-gateway",
    ]
    for d in defaults:
        if d not in repos:
            repos.append(d)
    return repos


RowMaker = Callable[[random.Random, int], list[object]]


def sheet_definition(
    kind: str,
    corpus: ProseCorpus,
) -> tuple[list[str], RowMaker, int, int, str, str]:
    """Return columns, row generator, ID col, probe col, probe label, and row noun."""
    cats = [corpus.names.get(c, c) for c in corpus.categories] or [
        "Cloud Infrastructure",
        "Identity Services",
        "Cyber Operations",
    ]
    parts = corpus.effective_part_labels()
    people = [p[0] for p in corpus.people] or ["Tan Wei Jie", "Lim Hui Ling"]
    ccy = corpus.currency

    if kind == "budget":
        cols = [
            "Line ID",
            "FY",
            "Month",
            "Cluster",
            "Business unit",
            "Cost centre",
            "GL account",
            "Description",
            f"Budget ({ccy})",
            f"Committed ({ccy})",
            f"Actual ({ccy})",
            f"Variance ({ccy})",
        ]
        descs = [
            "Cloud hosting",
            "Software licences",
            "Professional services",
            "Manpower",
            "Hardware refresh",
            "Training",
            "Security testing",
            "Network charges",
        ]

        def row_budget(r: random.Random, i: int) -> list[object]:
            b = round(r.uniform(5_000, 900_000), 2)
            a = round(b * r.uniform(0.4, 1.15), 2)
            return [
                f"BUL-{i:07d}",
                "FY26",
                r.choice(FY_MONTHS[:3]).replace("2025", "2026"),
                r.choice(cats),
                r.choice(parts),
                f"CC-{r.randint(100, 999)}",
                f"{r.choice([5101, 5203, 5310, 5420, 6105])}",
                r.choice(descs),
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
            "Procurement mode",
            "Category",
            "Vendor",
            "Vendor registration",
            "Award date",
            f"Contract value ({ccy})",
            "Status",
            "Buyer",
        ]
        modes = [
            ("Small value purchase", "SVP"),
            ("Quotation", "RFQ"),
            ("Open tender", "RFP"),
            ("Framework agreement", "FWA"),
        ]

        def row_proc(r: random.Random, i: int) -> list[object]:
            mode, code = r.choice(modes)
            return [
                f"4500{i:07d}",
                f"CNT000{code}26{r.randint(0, 999999):06d}",
                mode,
                r.choice(cats),
                _vendor_name(r, corpus),
                f"20{r.randint(10, 24)}{r.randint(10000, 99999)}{r.choice('KMNRWZ')}",
                f"2026-{r.randint(4, 6):02d}-{r.randint(1, 28):02d}",
                round(r.uniform(800, 2_500_000), 2),
                r.choice(["Awarded", "Closed", "Pending"]),
                r.choice(people),
            ]

        return cols, row_proc, 0, 7, f"contract value ({ccy})", "purchase orders"

    if kind == "pipeline":
        cols = [
            "Run ID",
            "Repository",
            "Branch",
            "Stage",
            "Started (SGT)",
            "Duration (s)",
            "Result",
            "Triggered by",
            "Commit",
        ]
        repos = _repo_names(corpus)

        def row_pipe(r: random.Random, i: int) -> list[object]:
            return [
                f"run-{i:08d}",
                r.choice(repos),
                r.choice(["main", "release/2.4", "develop", f"feature/TASK-{r.randint(100, 9999)}"]),
                r.choice(
                    [
                        "build",
                        "unit-test",
                        "sast",
                        "dast",
                        "container-scan",
                        "deploy-uat",
                        "deploy-prod",
                    ]
                ),
                f"2026-05-{r.randint(1, 31):02d} {r.randint(0, 23):02d}:{r.randint(0, 59):02d}",
                r.randint(12, 3600),
                r.choice(["passed"] * 6 + ["failed", "cancelled"]),
                f"{r.choice(GIVEN).split()[0].lower()}.{r.choice(SURNAMES).lower()}",
                f"{r.getrandbits(28):07x}",
            ]

        return cols, row_pipe, 0, 5, "duration in seconds", "pipeline runs"

    cols = [
        "Transaction ID",
        "Timestamp (SGT)",
        "Relying unit",
        "Channel",
        "Auth method",
        "Result",
        "Latency (ms)",
        "Device OS",
    ]

    def row_auth(r: random.Random, i: int) -> list[object]:
        return [
            f"ATX{i:010d}",
            (
                f"2026-{r.randint(4, 6):02d}-{r.randint(1, 28):02d} "
                f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}"
            ),
            r.choice(parts),
            r.choice(["App", "Web", "API"]),
            r.choice(
                [
                    "Enterprise SSO QR",
                    "Biometric verification",
                    "Password + OTP",
                    "Hardware passkey",
                ]
            ),
            r.choice(["Success"] * 9 + ["Failed"]),
            r.randint(90, 4000),
            r.choice(["iOS 19", "Android 16", "Windows 11", "macOS 16"]),
        ]

    return cols, row_auth, 0, 6, "latency in milliseconds", "transactions"
