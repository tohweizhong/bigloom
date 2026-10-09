"""Unit tests for the six grained plate drawers and batched JPEG encoder (Phase 2)."""

from __future__ import annotations

import io
import random

from PIL import Image

from bigloom.proposal.facts import load_world_entities
from bigloom.proposal.plates import (
    KINDS,
    encode_all,
    encode_job,
    kind_budget,
    kind_gantt,
    kind_render,
    kind_section,
    kind_sensors,
    kind_zone,
    make_figs,
    make_trap_figs,
)
from bigloom.proposal.spec import ProposalSpec


def _sample_spec_and_entities():
    spec = ProposalSpec(
        world_pack="retail-close",
        subject="Greater Southern Waterfront Digital Twin Programme",
        sizes_mb=[10],
        figures=6,
    )
    entities = load_world_entities(spec, seed=2026)
    return spec, entities


def test_all_six_plate_drawers_produce_rgb_images_and_questions() -> None:
    """Every plate drawer returns a 2400x1500 RGB image, caption, question, and value."""
    spec, entities = _sample_spec_and_entities()
    rng = random.Random(2026)
    drawers = [kind_zone, kind_gantt, kind_budget, kind_render, kind_section, kind_sensors]
    assert len(KINDS) == 6

    for idx, drawer in enumerate(drawers, start=1):
        img, caption, question, answer = drawer(rng, idx, spec, entities)
        assert isinstance(img, Image.Image)
        assert img.size == (2400, 1500)
        assert img.mode == "RGB"
        assert caption.strip()
        assert spec.doc_ref in question
        assert answer.strip()


def test_make_figs_and_trap_figs_preserve_site_context_with_different_values() -> None:
    """Trap figures reproduce the exact same caption and question with a different value."""
    spec, entities = _sample_spec_and_entities()
    rng = random.Random(2026)
    figs = make_figs(rng, 6, spec, entities)
    assert len(figs) == 6

    picks = {"start": 0, "middle": 3, "end": 5}
    trap_figs = make_trap_figs(figs, picks, spec, entities, seed=2026)
    assert len(trap_figs) == 3

    for (where, idx), (trap_where, trap_fig) in zip(picks.items(), trap_figs):
        target_fig = figs[idx]
        assert trap_where == where
        assert trap_fig.caption == target_fig.caption
        assert trap_fig.question == target_fig.question
        assert trap_fig.answer != target_fig.answer
        assert len(trap_fig.data) > 10_000


def test_encode_job_and_encode_all_scale_jpeg_near_budget() -> None:
    """encode_job and encode_all produce valid JPEG bytes scaled near the target budget."""
    spec, entities = _sample_spec_and_entities()
    rng = random.Random(99)
    figs = make_figs(rng, 4, spec, entities)

    budget = 180_000
    encode_all(figs, budget=budget, workers=2)

    for fig in figs:
        assert len(fig.data) > 50_000
        assert fig.size[0] > 0 and fig.size[1] > 0
        decoded = Image.open(io.BytesIO(fig.data))
        assert decoded.format == "JPEG"
        assert decoded.size == fig.size

    # Verify single encode_job call directly
    raw_bytes = figs[0].base.tobytes()
    data, out_size = encode_job((raw_bytes, figs[0].base.size, 120_000))
    assert len(data) > 30_000
    assert out_size[0] > 0
