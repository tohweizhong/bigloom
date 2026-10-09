"""Unit tests for proposal DOCX assembly, multi-size XML identity, verification, and CLI (Phase 3)."""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from bigloom.cli import app
from bigloom.proposal.builder import DocxLocator, build_proposal
from bigloom.proposal.spec import ProposalSpec, ProseConfig
from bigloom.proposal.verify import find_leaks, verify_proposal_outputs


def _make_small_spec(*, sizes_mb: list[int] | None = None, leak_terms: list[str] | None = None) -> ProposalSpec:
    return ProposalSpec(
        world_pack="retail-close",
        subject="Greater Southern Waterfront Digital Twin Programme",
        sizes_mb=sizes_mb or [1, 2],
        chapters=[
            "Executive summary",
            "Strategic context and programme vision",
            "Implementation plan and phasing",
            "Financial analysis and budget",
            "Risk management",
            "Annex A: Glossary and abbreviations",
        ],
        middle_chapter="Implementation plan and phasing",
        sections_per_chapter=1,
        annex_sections=1,
        figures=6,
        leak_terms=leak_terms or [],
        prose=ProseConfig(provider="deterministic", workers=2),
    )


def test_multi_size_build_shares_identical_document_xml_and_no_ballast(tmp_path: Path) -> None:
    """Two sizes in sizes_mb produce identical word/document.xml and differ only in word/media/."""
    spec = _make_small_spec(sizes_mb=[1, 2])
    result = build_proposal(spec, out_dir=tmp_path, seed=2026)

    assert len(result.manifest_entries) == 2
    path_1 = tmp_path / result.manifest_entries[0]["file"]
    path_2 = tmp_path / result.manifest_entries[1]["file"]
    assert path_1.is_file()
    assert path_2.is_file()
    assert path_2.stat().st_size > path_1.stat().st_size

    with zipfile.ZipFile(path_1) as z1, zipfile.ZipFile(path_2) as z2:
        assert "worldloom/shape-ballast.bin" not in z1.namelist()
        assert "worldloom/shape-ballast.bin" not in z2.namelist()
        xml_1 = z1.read("word/document.xml")
        xml_2 = z2.read("word/document.xml")
        assert xml_1 == xml_2

        media_1 = {n: z1.read(n) for n in z1.namelist() if n.startswith("word/media/")}
        media_2 = {n: z2.read(n) for n in z2.namelist() if n.startswith("word/media/")}
        assert set(media_1.keys()) == set(media_2.keys())
        assert sum(len(v) for v in media_2.values()) > sum(len(v) for v in media_1.values())


def test_verify_proposal_outputs_checks_inspect_artifact_positions_and_trap_isolation(
    tmp_path: Path,
) -> None:
    """verify_proposal_outputs confirms text locators, end-after-last-image, image isolation, and trap twin."""
    spec = _make_small_spec(sizes_mb=[1])
    result = build_proposal(spec, out_dir=tmp_path, seed=2026)

    verification = verify_proposal_outputs(spec, out_dir=tmp_path, build_result=result)
    assert verification.passed, f"Unexpected errors: {verification.errors}"
    assert verification.total_eval_rows == 9

    # Check trap file is under 1 MB
    trap_path = tmp_path / "traps" / spec.trap_filename
    assert trap_path.is_file()
    assert trap_path.stat().st_size < 1_048_576

    # Check manifest.jsonl, evals.jsonl, and evals.csv
    manifest_lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(manifest_lines) == 1
    manifest_item = json.loads(manifest_lines[0])
    assert len(manifest_item["sha256"]) == 64
    assert len(manifest_item["trap_sha256"]) == 64

    eval_lines = (tmp_path / "evals.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(eval_lines) == 9
    for line in eval_lines:
        row = json.loads(line)
        locator = DocxLocator.model_validate(row["locator"])
        assert locator.unit_locator.startswith(("paragraph:", "image:"))
        if row["modality"] == "text":
            assert row["fact_id"]
            assert row["trap_fact_id"]

    with (tmp_path / "evals.csv").open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["query", "golden"]
    assert len(rows) == 10


def test_find_leaks_and_leak_term_rejection(tmp_path: Path) -> None:
    """find_leaks detects forbidden topic terms and build_proposal fails when leak_terms match."""
    found = find_leaks(["This text mentions Keppel Club and Tuas."], ["Keppel", "Tuas", "Punggol"])
    assert found == ["Keppel", "Tuas"]

    bad_spec = _make_small_spec(sizes_mb=[1], leak_terms=["Waterfront"])
    with pytest.raises(ValueError, match="Waterfront"):
        build_proposal(bad_spec, out_dir=tmp_path, seed=2026)


def test_cli_bigloom_proposal_end_to_end(tmp_path: Path) -> None:
    """bigloom proposal CLI loads a YAML spec and writes docx, traps, manifest, and evals."""
    spec_path = tmp_path / "test_spec.yaml"
    spec_data = {
        "world_pack": "retail-close",
        "subject": "Greater Southern Waterfront Digital Twin Programme",
        "sizes_mb": [1],
        "chapters": [
            "Executive summary",
            "Implementation plan and phasing",
            "Annex A: Glossary and abbreviations",
        ],
        "middle_chapter": "Implementation plan and phasing",
        "sections_per_chapter": 1,
        "annex_sections": 1,
        "figures": 6,
        "prose": {"provider": "deterministic", "workers": 2},
    }
    spec_path.write_text(yaml.safe_dump(spec_data), encoding="utf-8")

    out_dir = tmp_path / "out"
    runner = CliRunner()
    res = runner.invoke(
        app,
        ["proposal", "--spec", str(spec_path), "--out", str(out_dir), "--seed", "42"],
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["passed"] is True
    assert (out_dir / "manifest.jsonl").is_file()
    assert (out_dir / "evals.jsonl").is_file()
    assert (out_dir / "evals.csv").is_file()


def test_verify_proposal_outputs_detects_tampered_evals_and_ballast(tmp_path: Path) -> None:
    """verify_proposal_outputs flags bad locators, image text leaks, trap leaks, and ballast."""
    spec = _make_small_spec(sizes_mb=[1])
    result = build_proposal(spec, out_dir=tmp_path, seed=2026)

    # Inject a forbidden shape-ballast.bin into the target .docx
    with zipfile.ZipFile(result.target_paths[0], "a") as zf:
        zf.writestr("worldloom/shape-ballast.bin", b"ballast")

    # Tamper with eval_rows to trigger locator, image-in-text, and trap-in-target errors
    tampered_rows = [dict(r) for r in result.eval_rows]
    tampered_rows[0]["locator"] = {"unit_locator": "paragraph:99999"}
    tampered_rows[4]["locator"] = {"unit_locator": "paragraph:1"}  # end fact before last plate
    tampered_rows[6]["answer"] = "Greater Southern Waterfront"  # image fact present in text
    tampered_rows[0]["trap_answer"] = "Greater Southern Waterfront"  # trap present in text

    from bigloom.proposal.builder import ProposalBuildResult

    bad_result = ProposalBuildResult(
        manifest_entries=result.manifest_entries,
        eval_rows=tampered_rows,
        target_paths=result.target_paths,
        trap_path=result.trap_path,
    )
    report = verify_proposal_outputs(spec, out_dir=tmp_path, build_result=bad_result)
    assert report.passed is False
    assert any("shape-ballast.bin" in err for err in report.errors)
    assert any("paragraph:99999" in err for err in report.errors)
    assert any("not after last plate" in err for err in report.errors)
    assert any("image-only fact" in err for err in report.errors)
    assert any("trap_answer" in err for err in report.errors)


def test_custom_evidence_positions_and_pydantic_models(tmp_path: Path) -> None:
    """Custom evidence_positions filter evaluation rows and validate against frozen Pydantic models."""
    from bigloom.proposal.builder import ProposalEvalRow, ProposalManifestEntry
    from bigloom.proposal.spec import EvidencePosition

    spec = ProposalSpec(
        world_pack="retail-close",
        subject="Greater Southern Waterfront Digital Twin Programme",
        sizes_mb=[1],
        chapters=[
            "Executive summary",
            "Implementation plan and phasing",
            "Annex A: Glossary and abbreviations",
        ],
        middle_chapter="Implementation plan and phasing",
        sections_per_chapter=1,
        annex_sections=1,
        figures=6,
        evidence_positions=[
            EvidencePosition(position="start", modality="text"),
            EvidencePosition(position="end", modality="text"),
            EvidencePosition(position="middle", modality="image"),
        ],
        prose=ProseConfig(provider="deterministic", workers=2),
    )
    result = build_proposal(spec, out_dir=tmp_path, seed=2026)
    assert len(result.eval_rows) == 3

    manifest_model = ProposalManifestEntry.model_validate(result.manifest_entries[0])
    assert manifest_model.size_mb == 1

    eval_models = [ProposalEvalRow.model_validate(row) for row in result.eval_rows]
    assert [m.position for m in eval_models] == ["start", "end", "middle"]
    assert [m.modality for m in eval_models] == ["text", "text", "image"]


