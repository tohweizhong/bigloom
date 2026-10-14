"""Grounded multi-paragraph prose generator, risk tables, and Excel row definitions."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

MARKING = "OFFICIAL (CLOSED) / SENSITIVE NORMAL - SYNTHETIC TEST DATA"
SHORT_MARK = "SYNTHETIC TEST DATA"
DEFAULT_AGENCY = "Government Technology Agency (Synthetic)"

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
    "MOE",
    "MOH",
    "MOM",
    "MSF",
    "HDB",
    "CPF Board",
    "IRAS",
    "LTA",
    "NEA",
    "ICA",
    "SLA",
    "URA",
    "MND",
    "MCCY",
    "PUB",
    "SkillsFuture SG",
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
    "Merlion",
    "Straits",
    "Temasek",
    "Kallang",
    "Orchid",
    "Jurong",
    "Changi",
    "Bukit",
    "Marina",
    "Harbourfront",
    "Lion City",
    "Equator",
    "Raffles Quay",
    "Tanjong",
    "Serangoon",
    "Punggol",
    "Keppel Bay",
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
    "Agencies raised {n} service requests through the {system} in {month}.",
    "The median time to resolve a priority 2 incident fell to {hours} hours.",
    "The programme follows the IM8 policy on cloud security and data classification.",
    "{agency} joined the pilot in {month} and onboarded {n} officers in the first two weeks.",
    "We expect the remaining work to complete by {date}, if vendor resources stay available.",
    "The second phase uses a Quotation on GeBIZ, because the estimated value is below {currency} {amt}.",
    "The steering committee approved a contingency of {pct}% of the phase budget.",
    "User research sessions took place at {site} with {n} participants.",
    "Three risks stay open. The highest is the dependency on legacy interfaces in the {system}.",
    "Service availability for the quarter was {avail}% against a target of 99.90%.",
    "All production changes now go through the SHIP-HATS pipeline with automated security scans.",
    "The data classification for this dataset is Confidential (Cloud-Eligible).",
    "Officers said that the new flow saves about {mins} minutes for each application.",
    "{unit} will give the next update to the Management Committee in {month}.",
    "The vendor delivered release {ver} on {date}. It fixed {n} defects.",
    "Training uptake reached {pct}% of the target group by the end of {month}.",
    "The team retired {n} legacy servers and released {n2} vCPU of capacity.",
    "Cost avoidance for the year is approximately {currency} {amt}.",
    "An internal audit by {person} found no high-severity issues in the change process.",
    "The helpdesk now answers {pct}% of chats within two minutes.",
    "The architecture review board endorsed the design on {date}.",
    "Monitoring alerts go to the on-call roster through the SGTS observability stack.",
    "The team reviews access rights for privileged accounts every {days} days.",
    "Feedback from {agency} officers was positive, with a satisfaction score of {score} out of 5.",
    "The next phase extends the service to {n} more agencies.",
    "Data from the pilot stays in the Singapore region of the commercial cloud provider.",
    "A tabletop exercise on {date} tested the recovery plan for the {system}.",
    "The design team reduced the form from {n2} fields to {n} fields.",
    "The vulnerability backlog fell by {pct}% after the patch sprint in {month}.",
    "{person} owns the benefits tracking for this workstream.",
    "Two agencies asked for a later migration window. The programme office agreed.",
    "The team measures adoption as the number of monthly active officers.",
    "Licence costs change from a perpetual model to a subscription model from {month}.",
    "The pilot used synthetic data only. No production records left the agency network.",
    "Load tests reached {n} requests each second with no errors.",
    "Accessibility tests followed the Digital Service Standards checklist.",
    "The recovery point objective for the service is {mins} minutes.",
]

RISKS: list[tuple[str, str]] = [
    ("Vendor resources are not sufficient", "Medium"),
    ("Legacy interfaces delay integration", "High"),
    ("Agencies are not ready to migrate", "Medium"),
    ("Budget overrun in phase 2", "Low"),
    ("Security findings delay go-live", "High"),
    ("Low adoption by officers", "Medium"),
    ("Key staff leave the team", "Low"),
]

MITIGATIONS: list[str] = [
    "Weekly vendor review",
    "Early interface tests",
    "Agency readiness checklist",
    "Monthly cost review",
    "Early VAPT slot booked",
    "Change champions in each agency",
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
        return {
            "unit": unit_name,
            "n": r.randint(3, 60),
            "n2": r.randint(61, 140),
            "month": month,
            "person": person,
            "role": role,
            "system": r.choice(c.systems) if c.systems else "Citizen Services Portal",
            "hours": r.randint(2, 20),
            "agency": r.choice(AGENCIES),
            "date": f"{r.randint(1, 28)} {r.choice(FY_MONTHS)}",
            "amt": f"{r.randint(20, 900)},000",
            "currency": c.currency,
            "pct": r.randint(5, 95),
            "site": r.choice(c.sites) if c.sites else "Mapletree Business City",
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


def _vendor_name(rng: random.Random) -> str:
    return f"{rng.choice(VENDOR_A)} {rng.choice(VENDOR_B)} Pte Ltd"


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
    people = [p[0] for p in corpus.people] or ["Tan Wei Jie", "Lim Hui Ling"]
    ccy = corpus.currency

    if kind == "budget":
        cols = [
            "Line ID",
            "FY",
            "Month",
            "Cluster",
            "Agency",
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
                r.choice(AGENCIES),
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
            "GeBIZ reference",
            "Procurement mode",
            "Category",
            "Vendor",
            "Vendor UEN",
            "Award date",
            f"Contract value ({ccy})",
            "Status",
            "Buyer",
        ]
        modes = [
            ("Small value purchase", "SVP"),
            ("Quotation", "ETQ"),
            ("Open tender", "ETT"),
            ("Framework agreement", "FWA"),
        ]

        def row_proc(r: random.Random, i: int) -> list[object]:
            mode, code = r.choice(modes)
            return [
                f"4500{i:07d}",
                f"GVT000{code}26{r.randint(0, 999999):06d}",
                mode,
                r.choice(cats),
                _vendor_name(r),
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
        repos = [
            "lifesg-web",
            "singpass-auth-core",
            "techpass-portal",
            "gcc-landing-zone",
            "sgts-helm-charts",
            "pair-backend",
            "sensor-ingest",
            "notify-gateway",
        ]

        def row_pipe(r: random.Random, i: int) -> list[object]:
            return [
                f"run-{i:08d}",
                r.choice(repos),
                r.choice(["main", "release/2.4", "develop", f"feature/JIRA-{r.randint(100, 9999)}"]),
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
        "Relying party",
        "Channel",
        "Auth method",
        "Result",
        "Latency (ms)",
        "Device OS",
    ]

    def row_auth(r: random.Random, i: int) -> list[object]:
        return [
            f"SPX{i:010d}",
            (
                f"2026-{r.randint(4, 6):02d}-{r.randint(1, 28):02d} "
                f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}"
            ),
            r.choice(AGENCIES),
            r.choice(["App", "Web", "API"]),
            r.choice(
                [
                    "Singpass app QR",
                    "Face verification",
                    "Password + SMS OTP",
                    "Passkey",
                ]
            ),
            r.choice(["Success"] * 9 + ["Failed"]),
            r.randint(90, 4000),
            r.choice(["iOS 19", "Android 16", "Windows 11", "macOS 16"]),
        ]

    return cols, row_auth, 0, 6, "latency in milliseconds", "transactions"
