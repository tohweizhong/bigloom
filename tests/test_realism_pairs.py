"""Tests for the blind pair builder and name masking."""

from __future__ import annotations

from bigloom import realism_pairs as rp


def test_products_and_orgs_are_masked_consistently() -> None:
    text = "Log in with Singpass, then open Corppass. Singpass users of GovTech and the Government Technology Agency (Synthetic)."
    out = rp.mask_names(text)
    assert "Singpass" not in out and "Corppass" not in out and "GovTech" not in out
    import re

    tokens = re.findall(r"\[PRODUCT-\d\]", out)
    assert len(tokens) == 3 and len(set(tokens)) == 2  # the same name keeps one token
    assert "[ORG-1]" in out and "Synthetic" not in out


def test_extra_orgs_mask_world_names() -> None:
    out = rp.mask_names("The Product & Engineering cluster missed plan.", extra_orgs=["Product & Engineering"])
    assert out == "The [ORG-1] cluster missed plan."


def test_score_counts_correct_verdicts() -> None:
    key = {"P01": {"real": "A"}, "P02": {"real": "B"}}
    assert rp.score(key, [{"pair": "P01", "real": "A"}, {"pair": "P02", "real": "A"}]) == 1


def test_passages_drop_clues_and_short_lines() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (line * 20) + "\nPage 3 of 9\nhttps://example.gov.sg/x\n"
    out = rp.passages(text)
    assert out and all("Page 3" not in p and "https" not in p for p in out)


def test_passages_keep_short_tail_of_wrapped_sentence() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (line * 4) + "\nThe owner of the mapping table in the register is\nrecorded as unassigned.\n\n" + (line * 6)
    out = rp.passages(text)
    joined = " ".join(out)
    assert "the register is recorded as unassigned. This sentence" in joined
    assert "the register is This sentence" not in joined


def test_passages_still_drop_short_line_after_full_sentence() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (line * 12) + "\nSection 4\n" + (line * 4)
    assert "Section 4" not in " ".join(rp.passages(text))
