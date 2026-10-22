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
from .proposal import build_proposal, load_proposal_spec, verify_proposal_outputs
from .qualify import load_corpus_snapshots, qualify_corpus
from .queries import generate_queries, load_manifest
from .report import render_scorecard_markdown
from .wizard import parse_facets, run_interactive_wizard

app = typer.Typer(
    name="bigloom",
    help="Large-file synthesis and target-leakage gates on top of WorldLoom.",
    add_completion=False,
)
narrate_app = typer.Typer(help="Agent-written prose through the WorldLoom narration handshake.")
app.add_typer(narrate_app, name="narrate")


@narrate_app.command("prepare")
def narrate_prepare(
    out_dir: Annotated[Path, typer.Option("--out-dir", file_okay=False)],
    seed: Annotated[int, typer.Option("--seed")] = 42,
    formats: Annotated[str, typer.Option("--formats")] = "docx,pdf",
    world_pack: Annotated[str | None, typer.Option("--world-pack")] = None,
    domain: Annotated[str | None, typer.Option("--domain")] = None,
    locale: Annotated[str | None, typer.Option("--locale")] = None,
    facets: Annotated[str, typer.Option("--facets", help="Comma-separated key=value pairs.")] = "",
) -> None:
    """Build a corpus with no prose and write the requests for the candidate target documents."""
    from .narration import prepare

    result = prepare(
        out_dir, seed=seed, formats=[f.strip() for f in formats.split(",") if f.strip()],
        world_pack=world_pack, domain=domain, locale=locale, facets=parse_facets(facets),
    )
    typer.echo(json.dumps({
        "corpus_dir": str(result.corpus_dir), "requests": str(result.requests_path),
        "documents": list(result.artifact_ids), "sections": result.requests, "target_words": result.target_words,
    }, indent=2))


@narrate_app.command("accept")
def narrate_accept(
    out_dir: Annotated[Path, typer.Option("--out-dir", file_okay=False, exists=True)],
    responses: Annotated[Path, typer.Option("--from", exists=True, dir_okay=False)],
    model_id: Annotated[str, typer.Option("--model-id")] = "agent",
) -> None:
    """Validate the agent responses with WorldLoom. Commit them only when every response passes."""
    from .narration import accept

    report = accept(out_dir, responses, model_id=model_id)
    typer.echo(json.dumps(report, indent=2))
    if not report["accepted"]:
        raise typer.Exit(code=1)


@app.command()
def init(
    out_dir: Annotated[Path, typer.Option("--out", file_okay=False)] = Path("/tmp/bigloom-run"),
    sizes_mb: Annotated[str, typer.Option("--sizes-mb")] = "18,50,100",
    formats: Annotated[str, typer.Option("--formats")] = "docx,xlsx,pptx,pdf",
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    writer: Annotated[str, typer.Option("--writer", help="Narration writer: template (default) or handshake (needs --corpus-dir from `bigloom narrate`).")] = "template",
) -> None:
    """Interactive wizard that asks for company details and runs WorldLoom and BigLoom."""
    summary = run_interactive_wizard(
        out_dir=out_dir,
        seed=seed,
        default_sizes_mb=sizes_mb,
        default_formats=formats,
        writer=writer,
    )
    typer.echo(json.dumps(summary, indent=2))
    if summary.get("executed") and summary.get("qualified") is False:
        raise typer.Exit(code=1)


@app.command()
def proposal(
    spec_path: Annotated[Path, typer.Option("--spec", exists=True, dir_okay=False)],
    out_dir: Annotated[Path, typer.Option("--out", file_okay=False)],
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    skip_prose: Annotated[bool, typer.Option("--skip-prose")] = False,
) -> None:
    """Build large .docx funding proposals (up to 1 GiB) and < 1 MB trap twins from a YAML spec."""
    spec = load_proposal_spec(spec_path)
    result = build_proposal(spec, out_dir=out_dir, seed=seed, skip_prose=skip_prose)
    verification = verify_proposal_outputs(spec, out_dir=out_dir, build_result=result)
    summary = {
        "out": str(out_dir),
        "passed": verification.passed,
        "manifest_entries": result.manifest_entries,
        "total_eval_rows": verification.total_eval_rows,
        "errors": verification.errors,
    }
    typer.echo(json.dumps(summary, indent=2))
    if not verification.passed:
        raise typer.Exit(code=1)


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
    locale: Annotated[str | None, typer.Option("--locale")] = None,
    facets: Annotated[str | None, typer.Option("--facets")] = None,
    subject: Annotated[str | None, typer.Option("--subject")] = None,
    writer: Annotated[str, typer.Option("--writer", help="Narration writer: template (default) or handshake (needs --corpus-dir from `bigloom narrate`).")] = "template",
) -> None:
    """Synthesize large target files (up to 1 GiB) and paired < 1 MB distractor trap files."""
    parsed_sizes = tuple(float(x.strip()) for x in sizes_mb.split(",") if x.strip())
    parsed_formats = tuple(x.strip() for x in formats.split(",") if x.strip())
    parsed_facets = parse_facets(facets) if facets else None
    entries = build_corpus(
        out_dir=out_dir,
        sizes_mb=parsed_sizes,
        seed=seed,
        formats=parsed_formats,
        corpus_dir=corpus_dir,
        world_pack=world_pack,
        domain=domain,
        locale=locale,
        facets=parsed_facets,
        subject=subject,
        writer=writer,
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
