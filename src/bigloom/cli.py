"""Command-line interface for BigLoom."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .grade import grade_responses
from .models import EvalCase, EvalResponse
from .qualify import load_corpus_snapshots, qualify_corpus

app = typer.Typer(
    name="bigloom",
    help="Large-file synthesis and target-leakage gates on top of WorldLoom.",
    add_completion=False,
)


@app.command()
def qualify(
    corpus_dir: Path = typer.Option(..., "--corpus-dir", exists=True, file_okay=False),
    cases_path: Path = typer.Option(..., "--cases", exists=True, dir_okay=False),
    check_retrieval: bool = typer.Option(True, "--check-retrieval/--no-check-retrieval"),
) -> None:
    """Qualify a rendered directory and evaluation cases against target leakage."""
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw_cases]
    snapshots = load_corpus_snapshots(corpus_dir)
    report = qualify_corpus(snapshots, cases, check_retrieval=check_retrieval)
    typer.echo(report.model_dump_json(indent=2))
    if not report.passed:
        raise typer.Exit(code=1)


@app.command()
def grade(
    cases_path: Path = typer.Option(..., "--cases", exists=True, dir_okay=False),
    responses_path: Path = typer.Option(..., "--responses", exists=True, dir_okay=False),
) -> None:
    """Grade evaluation responses and classify target-leakage verdicts."""
    raw_cases = json.loads(cases_path.read_text(encoding="utf-8"))
    raw_responses = json.loads(responses_path.read_text(encoding="utf-8"))
    cases = [EvalCase.model_validate(item) for item in raw_cases]
    responses = [EvalResponse.model_validate(item) for item in raw_responses]
    report = grade_responses(cases, responses)
    typer.echo(report.model_dump_json(indent=2))
