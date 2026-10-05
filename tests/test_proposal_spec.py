"""Unit tests for ProposalSpec YAML validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from bigloom.proposal.spec import EvidencePosition, ProposalSpec, load_proposal_spec


def test_bundled_proposal_specs_validate() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    gsw = load_proposal_spec(repo_root / "specs" / "gsw_proposal.yaml")
    tuas = load_proposal_spec(repo_root / "specs" / "tuas_proposal.yaml")
    pdd = load_proposal_spec(repo_root / "specs" / "pdd_proposal.yaml")

    assert gsw.id_prefix == "GSW"
    assert gsw.sizes_mb == [200]
    assert tuas.id_prefix == "TUAS"
    assert tuas.sizes_mb == [500]
    assert pdd.id_prefix == "PDD"
    assert pdd.sizes_mb == [1024]
    assert "GSW" in pdd.leak_terms


def test_minimal_user_spec_derives_defaults(tmp_path: Path) -> None:
    minimal_yaml = tmp_path / "minimal.yaml"
    minimal_yaml.write_text(
        "world_pack: retail-close\n"
        "subject: National Coastal Digital Twin Programme\n"
        "sizes_mb:\n"
        "  - 200\n",
        encoding="utf-8",
    )
    spec = load_proposal_spec(minimal_yaml)
    assert spec.world_pack == "retail-close"
    assert spec.subject == "National Coastal Digital Twin Programme"
    assert spec.sizes_mb == [200]
    assert spec.id_prefix == "NCDT"
    assert spec.ref_prefix == "NCDT-DT"
    assert spec.title.startswith("National Coastal Digital Twin Programme:")
    assert spec.filename.endswith("_FINAL.docx")
    assert spec.trap_filename.endswith("_superseded.docx")
    assert len(spec.chapters) >= 15
    assert spec.middle_chapter in spec.chapters
    assert spec.figures == 96


def test_missing_required_field_names_field(tmp_path: Path) -> None:
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("domain: retail\nsizes_mb: [10]\n", encoding="utf-8")

    with pytest.raises(ValidationError) as exc_info:
        load_proposal_spec(bad_yaml)

    err_text = str(exc_info.value)
    assert "subject" in err_text


def test_both_world_pack_and_domain_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProposalSpec(
            world_pack="retail-close",
            domain="retail",
            subject="Test Proposal",
            sizes_mb=[5],
        )

    assert "world_pack" in str(exc_info.value) or "domain" in str(exc_info.value)


def test_invalid_evidence_position_and_modality_rejected() -> None:
    with pytest.raises(ValidationError) as pos_err:
        EvidencePosition(position="nowhere", modality="text")  # type: ignore[arg-type]
    assert "position" in str(pos_err.value)

    with pytest.raises(ValidationError) as mod_err:
        EvidencePosition(position="start", modality="audio")  # type: ignore[arg-type]
    assert "modality" in str(mod_err.value)
