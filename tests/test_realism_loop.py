"""Tests for the realism loop promotion rule and receipts."""

from __future__ import annotations

import json
from pathlib import Path

from bigloom import realism_loop as rl

REAL = {"wl_id_per_k": 0.0, "commercial_per_k": 0.0, "retail_per_k": 0.78, "within_file_repeat": 0.04,
        "top_opener_share": 0.074, "unique_sentences": 146.7, "cross_document_reuse": 0.001}
BEST = {"wl_id_per_k": 0.0, "commercial_per_k": 8.0, "retail_per_k": 0.2, "within_file_repeat": 0.044,
        "top_opener_share": 0.12, "unique_sentences": 51.0, "cross_document_reuse": 0.0}


def test_distance_is_absolute_gap_to_real() -> None:
    d = rl.distances(BEST, REAL)
    assert d["top_opener_share"] == round(0.12 - 0.074, 4)
    assert "unique_sentences" not in d  # loop v2 reports the count but does not score it


def test_promote_when_train_improves_and_holdout_gains() -> None:
    cand = {**BEST, "top_opener_share": 0.09, "unique_sentences": 60.0}
    d = rl.decide(BEST, cand, BEST, {**BEST, "top_opener_share": 0.10}, REAL)
    assert d.promote and set(d.improved) == {"top_opener_share"}


def test_a_longer_file_alone_does_not_promote_or_reject() -> None:
    """Loop v2: the raw sentence count is not scored, so length alone moves nothing."""
    d = rl.decide(BEST, {**BEST, "unique_sentences": 500.0}, BEST, {**BEST, "unique_sentences": 5.0}, REAL)
    assert d.improved == () and d.worsened == ()


def test_reject_when_a_dimension_worsens_beyond_its_band() -> None:
    cand = {**BEST, "top_opener_share": 0.09, "within_file_repeat": 0.08}
    d = rl.decide(BEST, cand, BEST, {**BEST, "top_opener_share": 0.09}, REAL)
    assert not d.promote and "within_file_repeat" in d.worsened


def test_reject_when_holdout_does_not_gain() -> None:
    cand = {**BEST, "top_opener_share": 0.09}
    d = rl.decide(BEST, cand, BEST, {**BEST, "top_opener_share": 0.15}, REAL)
    assert not d.promote and any("holdout" in r for r in d.reasons)


def test_reject_changes_inside_the_band() -> None:
    cand = {**BEST, "top_opener_share": 0.115}
    assert not rl.decide(BEST, cand, BEST, cand, REAL).promote


def test_train_and_holdout_seeds_do_not_overlap() -> None:
    assert not set(rl.TRAIN.values()) & set(rl.HOLDOUT.values())


def test_receipt_round_trips(tmp_path: Path) -> None:
    d = rl.decide(BEST, BEST, BEST, BEST, REAL)
    rl.write_receipt(tmp_path / "r.json", {"round": 2, "decision": d})
    data = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert data["round"] == 2 and data["decision"]["promote"] is False


def test_judge_guard_blocks_only_when_every_judge_agrees() -> None:
    cand = {**BEST, "top_opener_share": 0.09}
    one_flip = rl.decide(BEST, cand, BEST, cand, REAL, best_judge_correct=[20, 0, 0], cand_judge_correct=[20, 20, 0])
    assert one_flip.promote
    all_agree = rl.decide(BEST, cand, BEST, cand, REAL, best_judge_correct=[10, 2, 3], cand_judge_correct=[20, 18, 19])
    assert not all_agree.promote and any("every judge" in r for r in all_agree.reasons)


def test_v2_reference_is_the_median_of_the_real_files() -> None:
    import json
    import statistics

    from bigloom.realism_loop import REFERENCE_V2, real_reference

    ref = real_reference()
    files = json.loads(REFERENCE_V2.read_text(encoding="utf-8"))["files"]
    assert len(files) == 11
    assert ref["unique_sentences"] == statistics.median(f["unique_sentences"] for f in files)
    assert ref["unique_sentences"] < 146.7  # the v1 mean, skewed by one long DOCX
    assert set(ref) >= {"commercial_per_k", "top_opener_share", "unique_sentences", "cross_document_reuse"}
