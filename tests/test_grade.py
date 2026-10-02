"""Unit tests for BigLoom eval-time leakage grading."""

from __future__ import annotations

from bigloom.grade import grade_responses
from bigloom.models import CanaryTrap, EvalCase, EvalResponse, LeakageVerdict


def _sample_cases() -> list[EvalCase]:
    return [
        EvalCase(
            id="case-1",
            query="What is the final FY2026 reserve budget for Project Aurora?",
            target_file="docs/aurora_fy2026_final.docx",
            modality="text",
            golden_value="SGD 4,827,319",
            acceptable_values=("4,827,319",),
            min_unit_index=6,
            canary_trap=CanaryTrap(
                distractor_file="traps/aurora_fy2025_draft.docx",
                canary_value="SGD 3,190,450",
            ),
        ),
        EvalCase(
            id="case-2",
            query="What is the Q4 peak thermal load in Zone B-409?",
            target_file="decks/thermal_fy2026_final.pptx",
            modality="image",
            golden_value="38.47%",
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file="traps/thermal_fy2025_draft.pptx",
                canary_value="29.15%",
            ),
        ),
    ]


def test_grade_all_five_verdicts() -> None:
    cases = _sample_cases()
    c3 = EvalCase(
        id="case-3",
        query="What is the audit code?",
        target_file="sheets/audit_fy2026.xlsx",
        modality="text",
        golden_value="AUD-9041-Z",
        min_unit_index=5,
    )
    c4 = EvalCase(
        id="case-4",
        query="What is the backup capacity?",
        target_file="pdfs/capacity_fy2026.pdf",
        modality="text",
        golden_value="74,812 kWh",
        min_unit_index=5,
    )
    c5 = EvalCase(
        id="case-5",
        query="What is the latency target?",
        target_file="pdfs/latency_fy2026.pdf",
        modality="text",
        golden_value="14.85 ms",
        min_unit_index=5,
    )
    all_cases = [*cases, c3, c4, c5]

    responses = [
        # 1. CORRECT_WITH_DOWNLOAD
        EvalResponse(
            case_id="case-1",
            answer_text="According to aurora_fy2026_final.docx, the budget is SGD 4,827,319.",
            cited_files=("docs/aurora_fy2026_final.docx",),
            tool_calls=("search_documents", "download_document"),
        ),
        # 2. SNIPPET_ONLY_LEAK (matched golden, no download tool)
        EvalResponse(
            case_id="case-2",
            answer_text="The Q4 peak thermal load is 38.47% in thermal_fy2026_final.pptx.",
            cited_files=("decks/thermal_fy2026_final.pptx",),
            tool_calls=("search_documents",),
        ),
        # 3. CROSS_FILE_LEAK_CITATION (matched golden or answered, but cited wrong corpus file)
        EvalResponse(
            case_id="case-3",
            answer_text="The audit code is AUD-9041-Z.",
            cited_files=("traps/aurora_fy2025_draft.docx",),
            tool_calls=("search_documents", "read_file"),
        ),
        # 4. WRONG_ANSWER (wrong value)
        EvalResponse(
            case_id="case-4",
            answer_text="I could not find the backup capacity.",
            cited_files=(),
            tool_calls=("search_documents",),
        ),
        # case-5 omitted -> also WRONG_ANSWER
    ]

    report = grade_responses(all_cases, responses)
    by_id = {r.case_id: r for r in report.results}

    assert by_id["case-1"].verdict == LeakageVerdict.CORRECT_WITH_DOWNLOAD
    assert by_id["case-2"].verdict == LeakageVerdict.SNIPPET_ONLY_LEAK
    assert by_id["case-3"].verdict == LeakageVerdict.CROSS_FILE_LEAK_CITATION
    assert by_id["case-4"].verdict == LeakageVerdict.WRONG_ANSWER
    assert by_id["case-5"].verdict == LeakageVerdict.WRONG_ANSWER


def test_grade_canary_trap_and_prose_citation() -> None:
    cases = _sample_cases()
    responses = [
        # Returns canary value from distractor file with currency code moved after the number
        EvalResponse(
            case_id="case-1",
            answer_text="The reserve budget for Project Aurora is 3,190,450 SGD.",
            cited_files=(),
            tool_calls=("search_documents",),
        ),
        # Mentions wrong corpus file in prose without explicit cited_files
        EvalResponse(
            case_id="case-2",
            answer_text="Based on thermal_fy2025_draft, the load is 38.47%.",
            cited_files=(),
            tool_calls=("fetch_documents",),
        ),
    ]
    report = grade_responses(cases, responses)
    by_id = {r.case_id: r for r in report.results}
    assert by_id["case-1"].verdict == LeakageVerdict.CROSS_FILE_LEAK_CANARY
    assert by_id["case-2"].verdict == LeakageVerdict.CROSS_FILE_LEAK_CITATION


def test_grade_word_boundary_prevents_false_positive() -> None:
    """Ensure partial numeric overlap does not count as matching golden or canary value."""
    case = EvalCase(
        id="wb-grade-1",
        query="What is the reserve ratio?",
        target_file="docs/ratio_fy2026.docx",
        modality="text",
        golden_value="38.47%",
        min_unit_index=5,
        canary_trap=CanaryTrap(
            distractor_file="traps/ratio_fy2025.docx",
            canary_value="29.15%",
        ),
    )
    # "138.47%" contains "38.47%" as a substring, and "229.15%" contains "29.15%" as a substring.
    resp = EvalResponse(
        case_id="wb-grade-1",
        answer_text="The reserve ratio was 138.47% in Q1 and 229.15% in Q2.",
        cited_files=("docs/ratio_fy2026.docx",),
        tool_calls=("download_document",),
    )
    report = grade_responses([case], [resp])
    res = report.results[0]
    assert res.matched_golden is False
    assert res.matched_canary is False
    assert res.verdict == LeakageVerdict.WRONG_ANSWER
