"""Unit tests for rich chart drawers, tight byte-budget encoder, and grounded prose writer."""

from __future__ import annotations

import io
import random

from PIL import Image

from bigloom.charts import (
    CHART_KINDS,
    ChartContext,
    FigurePlate,
    encode_figure_tight,
    figure_count_for_target,
    make_chart_figures,
)
from bigloom.prose_writer import (
    MITIGATIONS,
    RISKS,
    ProseCorpus,
    Writer,
    format_money,
    sheet_definition,
)


def _sample_corpus() -> ProseCorpus:
    return ProseCorpus(
        company="Government Technology Agency (Synthetic)",
        currency="SGD",
        periods=["FY2025", "FY2026"],
        names={
            "BU-01": "Smart Nation Platform Solutions",
            "BU-02": "Cloud and Data Infrastructure",
            "CAT-01": "Identity and Authentication",
            "CAT-02": "Whole-of-Government Cloud",
        },
        revenue={
            ("BU-01", "FY2025"): (14_250.0, 13_800.0),
            ("BU-02", "FY2026"): (22_910.0, 21_500.0),
            ("CAT-01", "FY2025"): (8_420.0, 8_100.0),
            ("CAT-02", "FY2026"): (19_300.0, 18_950.0),
        },
        units=["BU-01", "BU-02"],
        categories=["CAT-01", "CAT-02"],
        people=[
            ("Tan Wei Jie", "Director, Platform Engineering"),
            ("Lim Hui Ling", "Deputy Director, Cloud Operations"),
            ("Arun Kumar", "Principal Architect, Identity"),
        ],
        systems=["Singpass Auth Core", "SHIP-HATS Pipeline", "GCC Landing Zone"],
        sites=["Mapletree Business City", "Sandcrawler Building", "Punggol Digital District"],
    )


def test_all_13_chart_drawers_render_high_res_images() -> None:
    assert len(CHART_KINDS) == 13
    expected_kinds = {
        "line",
        "bar",
        "donut",
        "stacked",
        "heatmap",
        "kpi",
        "gantt",
        "architecture",
        "org",
        "whiteboard",
        "memo",
        "floor",
        "phone",
    }
    assert set(CHART_KINDS) == expected_kinds

    corpus = _sample_corpus()
    ctx = ChartContext(
        rng=random.Random(42),
        corpus=corpus,
        title="Project Aurora FY2026 Final Audit Report",
        date="14 Oct 2026",
        theme=(0, 84, 147),
        chart_title="Project Aurora FY2026 Q4 Peak Thermal Efficiency",
        printed_value="48.73%",
    )
    figures = make_chart_figures(ctx, count=13, preferred_kinds=list(CHART_KINDS))
    assert len(figures) == 13
    assert {fig.kind for fig in figures} == expected_kinds

    for fig in figures:
        assert isinstance(fig, FigurePlate)
        assert fig.base.width >= 1000
        assert fig.base.height >= 1000
        assert fig.fmt in ("PNG", "JPEG")
        assert fig.caption


def test_encode_figure_tight_hits_byte_budget_without_static() -> None:
    corpus = _sample_corpus()
    ctx = ChartContext(
        rng=random.Random(99),
        corpus=corpus,
        title="Project Borealis FY2026 Final Audit Report",
        date="14 Oct 2026",
        theme=(31, 119, 180),
        chart_title="Project Borealis FY2026 Q4 Peak Thermal Efficiency",
        printed_value="63.19%",
    )
    figures = make_chart_figures(ctx, count=2, preferred_kinds=["line", "memo"])
    scales: dict[int, float] = {}
    for fig in figures:
        encode_figure_tight(fig, target_bytes=220_000, seed=101, scales=scales)
        assert len(fig.data) >= 120_000
        decoded = Image.open(io.BytesIO(fig.data))
        assert decoded.size == fig.size
        # Top header bar pixel at y=1 must remain close to the theme color, not random static.
        r, _g, b = decoded.getpixel((decoded.width // 2, 1))
        assert b > r

    # Small budget path (< 90 KB) encodes cleanly without grain
    small_data = encode_figure_tight(figures[0], target_bytes=24_000, seed=101, scales=scales)
    assert len(small_data) > 1_000
    assert figure_count_for_target(24_000) == 1
    assert figure_count_for_target(2 * 1024 * 1024) >= 2
    assert figure_count_for_target(20 * 1024 * 1024) >= 4
    assert figure_count_for_target(200 * 1024 * 1024) >= 12
    assert format_money(14_250.0, "SGD") == "SGD 14,250k"


def test_writer_and_sheet_definitions_ground_in_corpus() -> None:
    corpus = _sample_corpus()
    rng = random.Random(7)
    writer = Writer(rng, corpus)

    para = writer.paragraph(n=4)
    assert len(para.split()) >= 40
    assert len(RISKS) >= 4
    assert len(MITIGATIONS) >= 4

    for kind in ("budget", "procurement", "pipeline", "auth"):
        cols, make_row, id_col, probe_col, probe_name, noun = sheet_definition(kind, corpus)
        assert len(cols) >= 8
        sample_row = make_row(rng, 1)
        assert len(sample_row) == len(cols)
        assert 0 <= id_col < len(cols)
        assert 0 <= probe_col < len(cols)
        assert probe_name
        assert noun


def test_domain_neutral_prose_and_charts_exclude_public_sector_terms() -> None:
    """Verify private-sector ProseCorpus generates zero hardcoded government acronyms."""
    corpus = ProseCorpus(
        company="Junipera Banking Group",
        currency="USD",
        periods=["FY2025", "FY2026"],
        names={
            "BU-01": "Retail Banking",
            "BU-02": "Business Banking",
            "BU-03": "Wealth Management",
            "BU-04": "Institutional Banking",
            "CAT-01": "Core Deposits",
            "CAT-02": "Commercial Lending",
        },
        revenue={
            ("BU-01", "FY2025"): (14_250.0, 13_800.0),
            ("BU-02", "FY2026"): (22_910.0, 21_500.0),
        },
        units=["BU-01", "BU-02", "BU-03", "BU-04"],
        categories=["CAT-01", "CAT-02"],
        people=[
            ("Elena Rostova", "Managing Director, Retail Banking"),
            ("Marcus Vance", "Head of Core Deposits"),
        ],
        systems=["Core Ledger Platform", "Treasury Risk Engine", "Mobile Banking Gateway"],
        sites=["One Marina Financial Tower", "Harbourfront Operations Centre"],
    )
    rng = random.Random(123)
    writer = Writer(rng, corpus)
    prose_block = writer.paragraph(n=40)

    forbidden_gov_terms = (
        "GeBIZ",
        "IM8",
        "SHIP-HATS",
        "SGTS",
        "Singpass",
        "LifeSG",
        "TechPass",
        "Myinfo",
        "NRIC",
        "CPF Board",
        "IRAS",
        "SkillsFuture",
    )
    for term in forbidden_gov_terms:
        assert term not in prose_block, f"Found hardcoded public-sector term '{term}' in prose"

    for kind in ("budget", "procurement", "pipeline", "auth"):
        cols, make_row, *_ = sheet_definition(kind, corpus)
        joined_rows = " ".join(
            str(cell) for i in range(1, 25) for cell in [*cols, *make_row(rng, i)]
        )
        for term in forbidden_gov_terms:
            assert term not in joined_rows, f"Found '{term}' in {kind} sheet"

    ctx = ChartContext(
        rng=rng,
        corpus=corpus,
        title="Junipera Banking Group FY2026 Audit Report",
        date="15 Oct 2026",
        theme=(0, 84, 147),
        chart_title="Junipera Banking Group Q4 Efficiency",
        printed_value="44.12%",
    )
    figs = make_chart_figures(ctx, count=13, preferred_kinds=list(CHART_KINDS))
    for fig in figs:
        for term in forbidden_gov_terms:
            assert term not in fig.caption, f"Found '{term}' in chart caption '{fig.caption}'"


def test_prose_and_charts_derive_all_pools_from_worldloom() -> None:
    """Verify ProseCorpus, Writer, and ChartContext derive all pools from WorldLoom with zero hardcoded lists."""
    from worldloom import sdk
    from worldloom.render.values import corpus_locale

    import bigloom.charts as charts_mod
    import bigloom.prose_writer as pw_mod

    for forbidden_const in ("GIVEN", "SURNAMES", "AGENCIES", "VENDOR_A", "VENDOR_B", "SENTENCES"):
        assert not hasattr(pw_mod, forbidden_const), (
            f"prose_writer must not hardcode {forbidden_const}"
        )
    for forbidden_chart_const in (
        "LINE_METRICS",
        "BAR_METRICS",
        "DONUT_SETS",
        "STACK_SETS",
        "HEAT_SETS",
        "KPI_APPS",
        "KPI_TILES",
        "GANTT_TASKS",
        "SERVICES",
        "ORG_ROLES",
        "STICKY_TEXT",
        "ROOMS",
        "PHONE_APPS",
    ):
        assert not hasattr(charts_mod, forbidden_chart_const), (
            f"charts must not hardcode {forbidden_chart_const}"
        )

    world = (
        sdk.company("banking", seed=42)
        .located("united_kingdom")
        .master_data(vendors=12, customers=12, skus=12)
        .build()
        .episodes("2026-01", periods=2)
        .world
    )
    loc = corpus_locale(world)
    corpus = ProseCorpus.from_world(world)

    assert corpus.company == world.company.name
    assert corpus.currency == "GBP"
    assert set(loc.given[:5]).issubset(set(corpus.given_names))
    assert set(loc.family[:5]).issubset(set(corpus.surnames))
    assert any(bu.name in corpus.effective_part_labels() for bu in world.business_units)
    assert any(v.name in corpus.vendors for v in world._masterdata.vendors)
    assert any(svc.name in corpus.services for svc in world.services)
    assert len(corpus.narrated_sentences) >= 5
    assert len(corpus.risks) >= 3
    assert len(corpus.mitigations) >= 3

    rng = random.Random(42)
    writer = Writer(rng, corpus)
    paragraph = writer.paragraph(n=6)
    assert len(paragraph.split()) >= 35

    ctx = ChartContext(
        rng=rng,
        corpus=corpus,
        title=f"{corpus.company} Return Pack",
        date="15 Oct 2026",
        theme=(0, 84, 147),
        chart_title="CET1 Ratio",
        printed_value="12.40%",
    )
    figs = make_chart_figures(ctx, count=13, preferred_kinds=list(CHART_KINDS))
    assert len(figs) == 13
