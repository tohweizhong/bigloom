"""End-to-end tests for BigLoom build, queries, qualify, grade, and CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bigloom.build import build_corpus
from bigloom.cli import app
from bigloom.models import EvalCase, EvalResponse, LeakageVerdict
from bigloom.qualify import load_corpus_snapshots, qualify_corpus
from bigloom.queries import generate_queries

runner = CliRunner()


def test_build_and_queries_pass_qualification_gate(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    entries = build_corpus(
        out_dir=out_dir,
        sizes_mb=(0.12,),
        seed=42,
        formats=("docx", "xlsx", "pptx", "pdf"),
    )
    assert len(entries) == 4
    manifest_path = out_dir / "manifest.jsonl"
    assert manifest_path.is_file()

    # Check byte targets and distractor trap caps
    min_bytes = int(0.12 * 1024 * 1024)
    for entry in entries:
        target_path = out_dir / entry.target_file
        dist_path = out_dir / entry.distractor_file
        assert target_path.is_file()
        assert dist_path.is_file()
        assert entry.target_size_bytes == target_path.stat().st_size
        assert entry.target_size_bytes >= min_bytes
        assert entry.distractor_size_bytes == dist_path.stat().st_size
        assert entry.distractor_size_bytes < 1024 * 1024
        assert entry.text_unit_index >= 5

    # Generate cases.json and verify two questions per large file
    cases_path = out_dir / "cases.json"
    cases = generate_queries(manifest_path=manifest_path, out_path=cases_path)
    assert len(cases) == 8
    assert cases_path.is_file()

    modalities = [c.modality for c in cases]
    assert modalities.count("text") == 4
    assert modalities.count("image") == 4

    # Run qualification gate with BM25 and TF-IDF retrieval check enabled
    snapshots = load_corpus_snapshots(out_dir)
    report = qualify_corpus(snapshots, cases, check_retrieval=True)
    assert report.passed is True, f"Violations: {report.violations}"


def test_seed_determinism_and_corpus_dir_input(tmp_path: Path) -> None:
    seed_corpus = tmp_path / "seed_corpus"
    seed_corpus.mkdir()
    (seed_corpus / "note1.md").write_text(
        "# Sovereign Cloud Cooling\n Reserve capacity planning for Marina Bay Data Center.\n",
        encoding="utf-8",
    )

    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    entries_a = build_corpus(
        out_dir=out_a,
        sizes_mb=(0.08,),
        seed=99,
        formats=("docx", "pdf"),
        corpus_dir=seed_corpus,
    )
    entries_b = build_corpus(
        out_dir=out_b,
        sizes_mb=(0.08,),
        seed=99,
        formats=("docx", "pdf"),
        corpus_dir=seed_corpus,
    )
    assert [e.text_golden_value for e in entries_a] == [e.text_golden_value for e in entries_b]
    assert [e.image_golden_value for e in entries_a] == [e.image_golden_value for e in entries_b]
    assert [e.text_canary_value for e in entries_a] == [e.text_canary_value for e in entries_b]


def test_cli_four_step_pipeline(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_out"
    manifest_path = out_dir / "manifest.jsonl"
    cases_path = out_dir / "cases.json"
    responses_path = tmp_path / "responses.json"

    # Step 1: bigloom build
    res_build = runner.invoke(
        app,
        [
            "build",
            "--out-dir",
            str(out_dir),
            "--sizes-mb",
            "0.1",
            "--formats",
            "docx,pdf",
            "--seed",
            "7",
        ],
    )
    assert res_build.exit_code == 0, res_build.output
    assert manifest_path.is_file()

    # Step 2: bigloom queries
    res_queries = runner.invoke(
        app,
        [
            "queries",
            "--manifest",
            str(manifest_path),
            "--out",
            str(cases_path),
        ],
    )
    assert res_queries.exit_code == 0, res_queries.output
    assert cases_path.is_file()

    # Step 3: bigloom qualify
    res_qualify = runner.invoke(
        app,
        [
            "qualify",
            "--corpus-dir",
            str(out_dir),
            "--cases",
            str(cases_path),
        ],
    )
    assert res_qualify.exit_code == 0, res_qualify.output
    qual_data = json.loads(res_qualify.output)
    assert qual_data["passed"] is True

    # Step 4: bigloom grade
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw_cases]
    mock_responses = [
        EvalResponse(
            case_id=cases[0].id,
            answer_text=f"Verified figure is {cases[0].golden_value} from {cases[0].target_file}.",
            cited_files=(cases[0].target_file,),
            tool_calls=("search", "download_document"),
        ).model_dump(),
        EvalResponse(
            case_id=cases[1].id,
            answer_text=f"Chart shows {cases[1].canary_trap.canary_value}.",
            cited_files=(),
            tool_calls=("search",),
        ).model_dump(),
    ]
    responses_path.write_text(json.dumps(mock_responses, indent=2), encoding="utf-8")

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
    grade_data = json.loads(res_grade.output)
    assert grade_data["counts"][LeakageVerdict.CORRECT_WITH_DOWNLOAD.value] == 1
    assert grade_data["counts"][LeakageVerdict.CROSS_FILE_LEAK_CANARY.value] == 1

    # Also verify CLI qualify exits with code 1 when a violation exists
    bad_cases_path = tmp_path / "bad_cases.json"
    bad_case = cases[0].model_copy(update={"golden_value": "5%"})
    bad_cases_path.write_text(
        json.dumps([bad_case.model_dump()], indent=2),
        encoding="utf-8",
    )
    res_bad = runner.invoke(
        app,
        [
            "qualify",
            "--corpus-dir",
            str(out_dir),
            "--cases",
            str(bad_cases_path),
        ],
    )
    assert res_bad.exit_code == 1
