"""Unit tests for rich chart drawers, tight byte-budget encoder, and grounded prose writer."""

from __future__ import annotations

import io
import random

import pytest
from PIL import Image

from bigloom.charts import (
    CHART_KINDS,
    ChartContext,
    FigurePlate,
    encode_figure_tight,
    make_chart_figures,
)
from bigloom.prose_writer import (
    MITIGATIONS,
    RISKS,
    ProseCorpus,
    Writer,
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
    for fig in figures:
        encode_figure_tight(fig, target_bytes=220_000, seed=101)
        assert len(fig.data) >= 120_000
        decoded = Image.open(io.BytesIO(fig.data))
        assert decoded.size == fig.size
        # Top header bar pixel must remain close to the theme color, not random static.
        r, g, b = decoded.getpixel((100, 8))
        assert b > r


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
