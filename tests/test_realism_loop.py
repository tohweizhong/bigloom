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
    assert d["retail_per_k"] == 0.0
    assert "unique_sentences" not in d  # loop v2 reports the count but does not score it


def test_clean_side_below_real_has_zero_distance_and_never_worsens() -> None:
    """Metrics on or below the real reference have distance 0.0 and never count as worsened."""
    champ = {**REAL, "top_opener_share": 0.055}
    cand = {**REAL, "top_opener_share": 0.044}
    assert rl.distances(champ, REAL)["top_opener_share"] == 0.0
    assert rl.distances(cand, REAL)["top_opener_share"] == 0.0
    d = rl.decide(
        champ, cand, champ, cand, REAL,
        best_judge_correct=[20, 20, 20], cand_judge_correct=[10, 10, 10],
        best_holdout_judge_correct=[20, 20, 20], cand_holdout_judge_correct=[10, 10, 10],
    )
    assert d.promote and d.worsened == ()


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


def test_judge_error_alone_can_promote() -> None:
    """Grader v3: judges that cannot tell real from synthetic count as a train and holdout gain."""
    best, cand = [20, 20, 20], [10, 10, 10]  # error 0.0 -> 0.5, the real target
    d = rl.decide(BEST, BEST, BEST, BEST, REAL, best_judge_correct=best, cand_judge_correct=cand,
                  best_holdout_judge_correct=best, cand_holdout_judge_correct=cand)
    assert d.promote and d.improved == ("judge_error",), d
    assert d.holdout_gain == round(0.5 / rl.JUDGE_BAND, 3)


def test_judge_error_moving_away_from_half_is_worsened() -> None:
    """Grader v3: a candidate that the judges spot more easily is blocked, even with a metric gain."""
    cand = {**BEST, "top_opener_share": 0.09}
    d = rl.decide(BEST, cand, BEST, cand, REAL, best_judge_correct=[10, 12, 9], cand_judge_correct=[17, 18, 16])
    assert not d.promote and "judge_error" in d.worsened, d


def test_judge_error_is_skipped_without_counts() -> None:
    cand = {**BEST, "top_opener_share": 0.09}
    d = rl.decide(BEST, cand, BEST, {**BEST, "top_opener_share": 0.10}, REAL)
    assert d.promote and "judge_error" not in d.improved + d.worsened


def test_decide_rejects_when_gate_fails() -> None:
    cand = {**BEST, "top_opener_share": 0.09}
    d = rl.decide(BEST, cand, BEST, {**BEST, "top_opener_share": 0.10}, REAL, gate_passed=False)
    assert not d.promote and "build or fact gate failed" in d.reasons



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


def test_mask_names_and_passages_strip_symmetric_names_and_extraction_residue() -> None:
    from bigloom.realism_pairs import mask_names, passages

    synth = (
        "In the inventory valuation service and the product hierarchy sync service, "
        "Product & Engineering and Government Digital Transformation reconciled the "
        "Agency Reference Data Register and the reference data register."
    )
    masked_synth = mask_names(synth)
    assert "[PRODUCT-" in masked_synth and "[ORG-" in masked_synth
    assert "inventory valuation service" not in masked_synth
    assert "product hierarchy sync service" not in masked_synth
    assert "Product & Engineering" not in masked_synth

    real_raw = (
        "13 | P a g e \ue912 Provide notice at least [ insert: param, pr-4_prm_1 ] days "
        "in advance on CDCGoWhere and the Singapore Government Design System (SGDS) "
        "for Whole-of-Government portals. Call the 24/7 ScamShield Helpline at 1799 to verify. "
        + " ".join(["Public agencies maintain clear operational standards across digital services."] * 15)
    )
    extracted = mask_names(passages(real_raw)[0])
    assert "P a g e" not in extracted
    assert "\ue912" not in extracted
    assert "insert: param" not in extracted
    assert "pr-4_prm_1" not in extracted
    assert "Helpline at 1799" not in extracted
    assert "CDCGoWhere" not in extracted
    assert "SGDS" not in extracted
    assert "Whole-of-Government" not in extracted
