"""Unit tests for the BigLoom Markdown scorecard generator and CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bigloom.cli import app
from bigloom.grade import grade_responses
from bigloom.models import CanaryTrap, EvalCase, EvalResponse, ManifestEntry
from bigloom.report import render_scorecard_markdown

runner = CliRunner()


def _sample_manifest_and_cases() -> tuple[list[ManifestEntry], list[EvalCase]]:
    entries = [
        ManifestEntry(
            file_id="bl-001-docx-18mb",
            format="docx",
            target_file="large/bl-001-docx-18mb_fy2026_final.docx",
            target_size_bytes=18 * 1024 * 1024,
            target_sha256="a" * 64,
            distractor_file="traps/bl-001-docx-18mb_fy2025_draft.docx",
            distractor_size_bytes=80_000,
            distractor_sha256="b" * 64,
            topic="Project Aurora",
            period="FY2026",
            distractor_period="FY2025",
            text_metric_label="Capital Reserve",
            text_golden_value="SGD 4,827,319",
            text_canary_value="SGD 3,190,450",
            text_unit_index=6,
            image_chart_title="Peak Thermal Load",
            image_golden_value="38.47%",
            image_canary_value="29.15%",
        ),
        ManifestEntry(
            file_id="bl-002-pdf-50mb",
            format="pdf",
            target_file="large/bl-002-pdf-50mb_fy2026_final.pdf",
            target_size_bytes=50 * 1024 * 1024,
            target_sha256="c" * 64,
            distractor_file="traps/bl-002-pdf-50mb_fy2025_draft.pdf",
            distractor_size_bytes=75_000,
            distractor_sha256="d" * 64,
            topic="Project Borealis",
            period="FY2026",
            distractor_period="FY2025",
            text_metric_label="Subsea Budget",
            text_golden_value="SGD 7,912,440",
            text_canary_value="SGD 1,405,900",
            text_unit_index=6,
            image_chart_title="Cooling Efficiency",
            image_golden_value="64.18%",
            image_canary_value="41.09%",
        ),
    ]
    cases = [
        EvalCase(
            id="bl-001-docx-18mb-text",
            query="What is the Capital Reserve for Project Aurora?",
            target_file=entries[0].target_file,
            modality="text",
            golden_value=entries[0].text_golden_value,
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entries[0].distractor_file,
                canary_value=entries[0].text_canary_value,
            ),
        ),
        EvalCase(
            id="bl-001-docx-18mb-image",
            query="What is the Peak Thermal Load for Project Aurora?",
            target_file=entries[0].target_file,
            modality="image",
            golden_value=entries[0].image_golden_value,
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entries[0].distractor_file,
                canary_value=entries[0].image_canary_value,
            ),
        ),
        EvalCase(
            id="bl-002-pdf-50mb-text",
            query="What is the Subsea Budget for Project Borealis?",
            target_file=entries[1].target_file,
            modality="text",
            golden_value=entries[1].text_golden_value,
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entries[1].distractor_file,
                canary_value=entries[1].text_canary_value,
            ),
        ),
        EvalCase(
            id="bl-002-pdf-50mb-image",
            query="What is the Cooling Efficiency for Project Borealis?",
            target_file=entries[1].target_file,
            modality="image",
            golden_value=entries[1].image_golden_value,
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entries[1].distractor_file,
                canary_value=entries[1].image_canary_value,
            ),
        ),
    ]
    return entries, cases


def test_render_scorecard_markdown_sections(tmp_path: Path) -> None:
    entries, cases = _sample_manifest_and_cases()
    responses = [
        EvalResponse(
            case_id="bl-001-docx-18mb-text",
            answer_text="The Capital Reserve is SGD 4,827,319.",
            cited_files=(entries[0].target_file,),
            tool_calls=("search", "download_document"),
        ),
        EvalResponse(
            case_id="bl-001-docx-18mb-image",
            answer_text="The Peak Thermal Load is 38.47%.",
            cited_files=(entries[0].target_file,),
            tool_calls=("search",),
        ),
        EvalResponse(
            case_id="bl-002-pdf-50mb-text",
            answer_text="The Subsea Budget is SGD 1,405,900.",
            cited_files=(),
            tool_calls=("search",),
        ),
        EvalResponse(
            case_id="bl-002-pdf-50mb-image",
            answer_text="No chart metric found.",
            cited_files=(),
            tool_calls=("search",),
        ),
    ]
    grade_report = grade_responses(cases, responses)
    out_md = tmp_path / "scorecard.md"
    md = render_scorecard_markdown(
        cases=cases,
        grade_report=grade_report,
        manifest_entries=entries,
        out_path=out_md,
    )
    assert out_md.is_file()
    assert "## Overall Verdict Summary" in md
    assert "## Breakdown by File Size Tier" in md
    assert "## Breakdown by Document Format" in md
    assert "## Breakdown by Modality" in md
    assert "## Leakage and Failure Details" in md
    assert "18 MB" in md
    assert "50 MB" in md
    assert "SNIPPET_ONLY_LEAK" in md
    assert "CROSS_FILE_LEAK_CANARY" in md

    # Also verify filename-based size fallback when manifest_entries is None
    md_no_manifest = render_scorecard_markdown(cases=cases, grade_report=grade_report)
    assert "18 MB" in md_no_manifest
    assert "50 MB" in md_no_manifest


def test_cli_import_run_and_report_end_to_end(tmp_path: Path) -> None:
    entries, cases = _sample_manifest_and_cases()
    cases_path = tmp_path / "cases.json"
    manifest_path = tmp_path / "manifest.jsonl"
    raw_log_path = tmp_path / "raw_log.jsonl"
    responses_path = tmp_path / "responses.json"
    grade_path = tmp_path / "grade_report.json"
    scorecard_path = tmp_path / "scorecard.md"

    cases_path.write_text(
        json.dumps([c.model_dump() for c in cases], indent=2),
        encoding="utf-8",
    )
    manifest_path.write_text(
        "\n".join(e.model_dump_json() for e in entries) + "\n",
        encoding="utf-8",
    )
    raw_log_path.write_text(
        json.dumps(
            {
                "query": cases[0].query,
                "answer": "Reserve is SGD 4,827,319.",
                "citations": [cases[0].target_file],
                "tools": ["search", "read_file"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    res_import = runner.invoke(
        app,
        [
            "import-run",
            "--input",
            str(raw_log_path),
            "--cases",
            str(cases_path),
            "--out",
            str(responses_path),
        ],
    )
    assert res_import.exit_code == 0, res_import.output
    assert responses_path.is_file()

    res_grade = runner.invoke(
        app,
        [
            "grade",
            "--cases",
            str(cases_path),
            "--responses",
            str(responses_path),
        ],
    )
    assert res_grade.exit_code == 0, res_grade.output
    grade_path.write_text(res_grade.output, encoding="utf-8")

    res_report = runner.invoke(
        app,
        [
            "report",
            "--cases",
            str(cases_path),
            "--grade-report",
            str(grade_path),
            "--manifest",
            str(manifest_path),
            "--out",
            str(scorecard_path),
        ],
    )
    assert res_report.exit_code == 0, res_report.output
    assert scorecard_path.is_file()
    assert "## Overall Verdict Summary" in scorecard_path.read_text(encoding="utf-8")
