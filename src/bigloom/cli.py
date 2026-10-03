"""Command-line interface for BigLoom."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .adapters import import_run_responses
from .build import build_corpus
from .grade import grade_responses
from .models import EvalCase, EvalResponse, GradeReport
from .qualify import load_corpus_snapshots, qualify_corpus
from .queries import generate_queries, load_manifest
from .report import render_scorecard_markdown

app = typer.Typer(
    name="bigloom",
    help="Large-file synthesis and target-leakage gates on top of WorldLoom.",
    add_completion=False,
)


@app.command()
def build(
    out_dir: Annotated[Path, typer.Option("--out-dir", file_okay=False)],
    sizes_mb: Annotated[str, typer.Option("--sizes-mb")] = "18,50,100",
    formats: Annotated[str, typer.Option("--formats")] = "docx,xlsx,pptx,pdf",
    seed: Annotated[int, typer.Option("--seed")] = 42,
    corpus_dir: Annotated[
        Path | None, typer.Option("--corpus-dir", exists=True, file_okay=False)
    ] = None,
    world_pack: Annotated[str | None, typer.Option("--world-pack")] = None,
    domain: Annotated[str | None, typer.Option("--domain")] = None,
) -> None:
    """Synthesize large target files and paired < 1 MB distractor trap files."""
    parsed_sizes = tuple(float(x.strip()) for x in sizes_mb.split(",") if x.strip())
    parsed_formats = tuple(x.strip() for x in formats.split(",") if x.strip())
    entries = build_corpus(
        out_dir=out_dir,
        sizes_mb=parsed_sizes,
        seed=seed,
        formats=parsed_formats,
        corpus_dir=corpus_dir,
        world_pack=world_pack,
        domain=domain,
    )
    summary = {
        "out_dir": str(out_dir),
        "manifest": str(out_dir / "manifest.jsonl"),
        "total_large_files": len(entries),
    }
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def queries(
    manifest_path: Annotated[Path, typer.Option("--manifest", exists=True, dir_okay=False)],
    out_path: Annotated[Path, typer.Option("--out", dir_okay=False)],
) -> None:
    """Generate two high-entropy evaluation cases per large file from manifest.jsonl."""
    cases = generate_queries(manifest_path=manifest_path, out_path=out_path)
    summary = {
        "out": str(out_path),
        "total_cases": len(cases),
    }
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def qualify(
    corpus_dir: Annotated[Path, typer.Option("--corpus-dir", exists=True, file_okay=False)],
    cases_path: Annotated[Path, typer.Option("--cases", exists=True, dir_okay=False)],
    check_retrieval: Annotated[
        bool, typer.Option("--check-retrieval/--no-check-retrieval")
    ] = True,
) -> None:
    """Qualify a rendered directory and evaluation cases against target leakage."""
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw_cases]
    snapshots = load_corpus_snapshots(corpus_dir)
    report = qualify_corpus(snapshots, cases, check_retrieval=check_retrieval)
    typer.echo(report.model_dump_json(indent=2))
    if not report.passed:
        raise typer.Exit(code=1)


@app.command(name="import-run")
def import_run(
    input_path: Annotated[Path, typer.Option("--input", exists=True)],
    out_path: Annotated[Path, typer.Option("--out", dir_okay=False)],
    cases_path: Annotated[
        Path | None, typer.Option("--cases", exists=True, dir_okay=False)
    ] = None,
) -> None:
    """Convert saved evaluation logs (JSON, JSONL, agent traces, CSV) into EvalResponse JSON."""
    cases: list[EvalCase] | None = None
    if cases_path is not None:
        raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
        cases = [EvalCase.model_validate(item) for item in raw_cases]
    responses = import_run_responses(input_path, out_path=out_path, cases=cases)
    summary = {
        "out": str(out_path),
        "total_responses": len(responses),
    }
    typer.echo(json.dumps(summary, indent=2))


@app.command()
def grade(
    cases_path: Annotated[Path, typer.Option("--cases", exists=True, dir_okay=False)],
    responses_path: Annotated[Path, typer.Option("--responses", exists=True, dir_okay=False)],
) -> None:
    """Grade evaluation responses and classify target-leakage verdicts."""
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    raw_responses = json.loads(responses_path.read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw_cases]
    responses = [EvalResponse.model_validate(item) for item in raw_responses]
    report = grade_responses(cases, responses)
    typer.echo(report.model_dump_json(indent=2))


@app.command()
def report(
    cases_path: Annotated[Path, typer.Option("--cases", exists=True, dir_okay=False)],
    grade_report_path: Annotated[
        Path, typer.Option("--grade-report", exists=True, dir_okay=False)
    ],
    out_path: Annotated[Path, typer.Option("--out", dir_okay=False)],
    manifest_path: Annotated[
        Path | None, typer.Option("--manifest", exists=True, dir_okay=False)
    ] = None,
) -> None:
    """Render a Markdown evaluation scorecard by file size tier, format, and modality."""
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw_cases]
    grade_report = GradeReport.model_validate_json(
        grade_report_path.read_text(encoding="utf-8")
    )
    entries = load_manifest(manifest_path) if manifest_path is not None else None
    render_scorecard_markdown(
        cases=cases,
        grade_report=grade_report,
        manifest_entries=entries,
        out_path=out_path,
    )
    typer.echo(json.dumps({"out": str(out_path), "total_cases": len(cases)}, indent=2))


def main() -> None:
    """Run the BigLoom CLI application."""
    app()


if __name__ == "__main__":
    main()
