"""Eval-time leakage detection and response grading."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Sequence

from .models import CaseGrade, EvalCase, EvalResponse, GradeReport, LeakageVerdict

DOWNLOAD_TOOLS = {
    "download_document",
    "fetch_documents",
    "read_file",
    "get_document_content",
}


def _value_matches(text: str, needle: str) -> bool:
    """Return True when needle appears on word boundaries inside text."""
    low_needle = needle.strip().lower()
    if not low_needle:
        return False
    pattern = re.compile(
        r"(?<![0-9a-z])" + re.escape(low_needle) + r"(?![0-9a-z])(?!\.\d)"
    )
    return bool(pattern.search(text.lower()))


def _basename_stem(path_str: str) -> str:
    name = Path(path_str).name
    return Path(name).stem.lower()


def _cites_wrong_file(
    answer_text: str,
    cited_files: Sequence[str],
    target_file: str,
    corpus_files: Sequence[str],
) -> str | None:
    """Return the wrong corpus file name if the response cites a non-target file."""
    target_name = Path(target_file).name.lower()
    target_stem = _basename_stem(target_file)
    low_answer = answer_text.lower()

    # Check explicit grounding metadata citations first.
    for cited in cited_files:
        cited_low = Path(cited).name.lower()
        cited_stem = _basename_stem(cited)
        if cited_low == target_name or cited_stem == target_stem:
            return None
    for cited in cited_files:
        cited_low = Path(cited).name.lower()
        cited_stem = _basename_stem(cited)
        for candidate in corpus_files:
            if candidate == target_file:
                continue
            if cited_low == Path(candidate).name.lower() or cited_stem == _basename_stem(candidate):
                return candidate

    # Check file mentions inside the response prose.
    if target_name in low_answer or target_stem in low_answer:
        return None
    for candidate in corpus_files:
        if candidate == target_file:
            continue
        cand_name = Path(candidate).name.lower()
        cand_stem = _basename_stem(candidate)
        if cand_name in low_answer or (len(cand_stem) >= 8 and cand_stem in low_answer):
            return candidate
    return None


def grade_responses(
    cases: Sequence[EvalCase],
    responses: Sequence[EvalResponse],
    *,
    corpus_files: Sequence[str] | None = None,
) -> GradeReport:
    """Grade each response and classify target leakage verdicts."""
    all_files = list(corpus_files) if corpus_files is not None else sorted({c.target_file for c in cases})
    for case in cases:
        if case.canary_trap and case.canary_trap.distractor_file not in all_files:
            all_files.append(case.canary_trap.distractor_file)

    resp_by_id = {r.case_id: r for r in responses}
    grades: list[CaseGrade] = []

    for case in cases:
        resp = resp_by_id.get(case.id)
        if resp is None:
            grades.append(
                CaseGrade(
                    case_id=case.id,
                    verdict=LeakageVerdict.WRONG_ANSWER,
                    matched_golden=False,
                    matched_canary=False,
                    cited_wrong_file=False,
                    used_download_tool=False,
                    detail="No response recorded for this case.",
                )
            )
            continue

        matched_golden = any(_value_matches(resp.answer_text, val) for val in case.all_golden_values)
        matched_canary = bool(
            case.canary_trap and _value_matches(resp.answer_text, case.canary_trap.canary_value)
        )
        wrong_file = _cites_wrong_file(resp.answer_text, resp.cited_files, case.target_file, all_files)
        cited_wrong = wrong_file is not None
        used_download = any(
             any(dl in tool.lower() for dl in DOWNLOAD_TOOLS)
            for tool in resp.tool_calls
        )

        if matched_canary and not matched_golden:
            verdict = LeakageVerdict.CROSS_FILE_LEAK_CANARY
            detail = (
                f"Response returned canary value '{case.canary_trap.canary_value}' "
                f"from distractor file '{case.canary_trap.distractor_file}'."
            )
        elif cited_wrong:
            verdict = LeakageVerdict.CROSS_FILE_LEAK_CITATION
            detail = f"Response cited wrong file '{wrong_file}' instead of '{case.target_file}'."
        elif matched_golden and used_download:
            verdict = LeakageVerdict.CORRECT_WITH_DOWNLOAD
            detail = "Response matched golden value, cited target file, and called a download tool."
        elif matched_golden and not used_download:
            verdict = LeakageVerdict.SNIPPET_ONLY_LEAK
            detail = "Response matched golden value from search snippets without a file download call."
        else:
            verdict = LeakageVerdict.WRONG_ANSWER
            detail = "Response did not match golden value or any canary trap."

        grades.append(
            CaseGrade(
                case_id=case.id,
                verdict=verdict,
                matched_golden=matched_golden,
                matched_canary=matched_canary,
                cited_wrong_file=cited_wrong,
                used_download_tool=used_download,
                detail=detail,
            )
        )

    counts = dict(Counter(g.verdict.value for g in grades))
    return GradeReport(
        total_cases=len(cases),
        counts=counts,
        results=tuple(grades),
    )
