"""Generate Markdown scorecards by file size tier, format, and modality."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from .models import CaseGrade, EvalCase, GradeReport, LeakageVerdict, ManifestEntry

LEAKAGE_VERDICTS = {
    LeakageVerdict.SNIPPET_ONLY_LEAK,
    LeakageVerdict.CROSS_FILE_LEAK_CANARY,
    LeakageVerdict.CROSS_FILE_LEAK_CITATION,
}
_FILENAME_SIZE_RE = re.compile(r"-(\d+(?:_\d+)?)mb", re.IGNORECASE)


def _infer_size_label(target_file: str, size_by_file: dict[str, int]) -> str:
    """Return a readable MB tier label from manifest bytes or target filename."""
    match = _FILENAME_SIZE_RE.search(target_file)
    if match:
        raw_num = match.group(1).replace("_", ".")
        return f"{raw_num} MB"
    byte_count = size_by_file.get(target_file)
    if byte_count is not None:
        mb = round(byte_count / (1024 * 1024), 2)
        return f"{mb:g} MB"
    return "Unknown"


def _format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0 (0.0%)"
    pct = (numerator / denominator) * 100.0
    return f"{numerator} ({pct:.1f}%)"


def _group_sort_key(label: str) -> tuple[int, float, str]:
    """Sort numeric MB labels in ascending numeric order before string labels."""
    if label.endswith(" MB"):
        try:
            return (0, float(label.removesuffix(" MB").strip()), label)
        except ValueError:
            pass
    return (1, 0.0, label)


def _render_group_table(
    header_col: str,
    groups: dict[str, list[CaseGrade]],
) -> list[str]:
    """Render a Markdown table summarizing pass, leakage, and wrong-answer counts per group."""
    lines = [
        f"| {header_col} | Total Cases | Pass (`CORRECT_WITH_DOWNLOAD`) | Target Leakage | Wrong Answer |",
        "| :--- | ---: | ---: | ---: | ---: |",
    ]
    for key in sorted(groups.keys(), key=_group_sort_key):
        items = groups[key]
        total = len(items)
        passed = sum(1 for g in items if g.verdict == LeakageVerdict.CORRECT_WITH_DOWNLOAD)
        leaked = sum(1 for g in items if g.verdict in LEAKAGE_VERDICTS)
        wrong = sum(1 for g in items if g.verdict == LeakageVerdict.WRONG_ANSWER)
        lines.append(
            f"| {key} | {total} | {_format_rate(passed, total)} | "
            f"{_format_rate(leaked, total)} | {_format_rate(wrong, total)} |"
        )
    return lines


def render_scorecard_markdown(
    cases: Sequence[EvalCase],
    grade_report: GradeReport,
    *,
    manifest_entries: Sequence[ManifestEntry] | None = None,
    out_path: Path | None = None,
) -> str:
    """Build a five-section Markdown scorecard from evaluation cases and grading results."""
    case_by_id = {c.id: c for c in cases}
    size_by_file: dict[str, int] = {}
    fmt_by_file: dict[str, str] = {}
    if manifest_entries is not None:
        for entry in manifest_entries:
            size_by_file[entry.target_file] = entry.target_size_bytes
            fmt_by_file[entry.target_file] = entry.format

    total = len(grade_report.results)
    lines: list[str] = [
        "# BigLoom Evaluation Scorecard",
        "",
        "## Overall Verdict Summary",
        "",
        "| Verdict | Count | Share |",
        "| :--- | ---: | ---: |",
    ]
    for verdict in LeakageVerdict:
        count = sum(1 for g in grade_report.results if g.verdict == verdict)
        pct = (count / total * 100.0) if total else 0.0
        lines.append(f"| `{verdict.value}` | {count} | {pct:.1f}% |")

    by_size: dict[str, list[CaseGrade]] = defaultdict(list)
    by_format: dict[str, list[CaseGrade]] = defaultdict(list)
    by_modality: dict[str, list[CaseGrade]] = defaultdict(list)

    for grade in grade_report.results:
        case = case_by_id.get(grade.case_id)
        if case is None:
            continue
        size_label = _infer_size_label(case.target_file, size_by_file)
        fmt_label = fmt_by_file.get(
            case.target_file,
            Path(case.target_file).suffix.lower().removeprefix(".") or "unknown",
        )
        by_size[size_label].append(grade)
        by_format[fmt_label].append(grade)
        by_modality[case.modality].append(grade)

    lines.extend(["", "## Breakdown by File Size Tier", ""])
    lines.extend(_render_group_table("Size Tier", by_size))

    lines.extend(["", "## Breakdown by Document Format", ""])
    lines.extend(_render_group_table("Format", by_format))

    lines.extend(["", "## Breakdown by Modality", ""])
    lines.extend(_render_group_table("Modality", by_modality))

    lines.extend(
        [
            "",
            "## Leakage and Failure Details",
            "",
            "| Case ID | Target File | Modality | Verdict | Detail |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
    )
    for grade in grade_report.results:
        if grade.verdict == LeakageVerdict.CORRECT_WITH_DOWNLOAD:
            continue
        case = case_by_id.get(grade.case_id)
        target_file = case.target_file if case else "unknown"
        modality = case.modality if case else "unknown"
        safe_detail = grade.detail.replace("|", "\\|")
        lines.append(
            f"| `{grade.case_id}` | `{target_file}` | `{modality}` | "
            f"`{grade.verdict.value}` | {safe_detail} |"
        )

    markdown = "\n".join(lines) + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
    return markdown
