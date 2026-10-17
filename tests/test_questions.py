"""Phase 6 tests: questions take their wording from WorldLoom evaluation text and pack overrides."""

from __future__ import annotations

import json
from pathlib import Path

from worldloom.generators import episode_text
from worldloom.generators.evaluation import EVAL_TEXT

from bigloom.questions import Measure, period_text, sentence_case, text_question

PACK = Path(__file__).resolve().parents[1] / "packs" / "govtech.json"


def test_period_text_names_the_month() -> None:
    assert period_text("2026-03") == "March 2026"
    assert period_text("FY2026") == "FY2026"


def test_engine_wording_is_used_when_no_pack_overrides_it() -> None:
    q = text_question(dict(EVAL_TEXT), Measure("financial.revenue", "revenue"), "revised revenue forecast", "2026-03", "Acme CFO Memo")
    assert q == "What was the total revised revenue forecast for March 2026 in the Acme CFO Memo?"


def test_pack_evaluation_text_sets_the_wording() -> None:
    overrides = json.loads(PACK.read_text(encoding="utf-8"))["evaluation_text"]
    text = episode_text.merged(EVAL_TEXT, overrides, field="evaluation_text")
    q = text_question(text, Measure("financial.revenue", "revenue"), "revised revenue forecast", "2026-03", "Agency CFO Memo")
    assert q.startswith("What was the agency's total revised revenue forecast for March 2026")
    assert q.endswith("in the Agency CFO Memo?")


def test_measure_without_engine_wording_uses_the_plain_form() -> None:
    q = text_question(dict(EVAL_TEXT), Measure("overhead.shared_services.cost", "shared services cost"), "revised shared services cost forecast", "2026-03", "Acme RCA")
    assert q == "What is the revised shared services cost forecast for March 2026 in the Acme RCA?"


def test_group_wording_gets_an_article() -> None:
    q = text_question(dict(EVAL_TEXT), Measure("financial.gross_profit", "gross profit"), "revised gross profit forecast", "2026-03", "Acme CFO Memo")
    assert q == "What was the group revised gross profit forecast for March 2026 in the Acme CFO Memo?"


def test_sentence_case_keeps_acronyms() -> None:
    assert sentence_case("revised CET1 capital forecast") == "Revised CET1 capital forecast"
