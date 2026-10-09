"""Post-build byte and anti-leakage verification for bigloom proposal outputs."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from worldloom.native_artifacts import inspect_artifact

from .spec import ProposalSpec

if TYPE_CHECKING:
    from .builder import ProposalBuildResult


class ProposalVerificationReport(BaseModel):
    """Result of post-build verification on generated proposal .docx files and evals."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    total_target_files: int
    total_eval_rows: int
    errors: list[str]


def _contains_token(haystack: str, needle: str) -> bool:
    """Return True when `needle` appears on word boundaries inside `haystack`."""
    cleaned = needle.strip().lower()
    if not cleaned:
        return False
    pattern = re.compile(
        r"(?<![0-9a-z])" + re.escape(cleaned) + r"(?![0-9a-z])(?!\.\d)"
    )
    return bool(pattern.search(haystack.lower()))


def find_leaks(texts: list[str], leak_terms: list[str]) -> list[str]:
    """Return sorted leak_terms that appear in any of `texts` (case-insensitive word boundary)."""
    if not leak_terms:
        return []
    found: set[str] = set()
    for text in texts:
        for term in leak_terms:
            if re.search(rf"\b{re.escape(term)}", text, re.IGNORECASE):
                found.add(term)
    return sorted(found)


def verify_proposal_outputs(
    spec: ProposalSpec,
    out_dir: Path,
    build_result: ProposalBuildResult,
) -> ProposalVerificationReport:
    """Verify ZIP integrity, XML identity across sizes, fact placement, and trap isolation."""
    errors: list[str] = []

    if not build_result.target_paths:
        errors.append("No target .docx files were built.")

    if not build_result.trap_path.is_file():
        errors.append(f"Missing trap file: {build_result.trap_path}")
    else:
        trap_size = build_result.trap_path.stat().st_size
        if trap_size >= 1_048_576:
            errors.append(f"Trap file exceeds 1 MiB ({trap_size} bytes).")
        with zipfile.ZipFile(build_result.trap_path) as zf:
            bad_member = zf.testzip()
            if bad_member:
                errors.append(f"Trap ZIP corrupted at member {bad_member}.")
            if "worldloom/shape-ballast.bin" in zf.namelist():
                errors.append("Trap .docx contains forbidden worldloom/shape-ballast.bin.")

    xml_payloads: list[bytes] = []
    for path in build_result.target_paths:
        if not path.is_file():
            errors.append(f"Missing target file: {path}")
            continue
        with zipfile.ZipFile(path) as zf:
            bad_member = zf.testzip()
            if bad_member:
                errors.append(f"Target ZIP {path.name} corrupted at member {bad_member}.")
            if "worldloom/shape-ballast.bin" in zf.namelist():
                errors.append(
                    f"Target {path.name} contains forbidden worldloom/shape-ballast.bin."
                )
            xml_payloads.append(zf.read("word/document.xml"))

    if len(xml_payloads) > 1:
        first_xml = xml_payloads[0]
        for idx, other_xml in enumerate(xml_payloads[1:], start=2):
            if other_xml != first_xml:
                errors.append(
                    f"Target size #{idx} word/document.xml differs from target #1."
                )

    if build_result.target_paths and build_result.target_paths[0].is_file():
        primary_bytes = build_result.target_paths[0].read_bytes()
        snap = inspect_artifact(primary_bytes, "docx")
        units_by_locator = {u.locator: (idx, u.text) for idx, u in enumerate(snap.units, start=1)}
        all_target_text = "\n".join(u.text for u in snap.units if u.text)

        last_plate_idx = 0
        for idx, u in enumerate(snap.units, start=1):
            if re.match(r"^Plate \d+:", u.text.strip()):
                last_plate_idx = idx

        for row in build_result.eval_rows:
            row_id = str(row["id"])
            modality = str(row["modality"])
            position = str(row["position"])
            answer = str(row["answer"])
            trap_answer = str(row["trap_answer"])
            locator = row.get("locator")
            if not isinstance(locator, dict):
                errors.append(f"{row_id}: missing locator dictionary.")
                continue

            if modality == "text":
                unit_loc = str(locator.get("unit_locator", ""))
                if unit_loc not in units_by_locator:
                    errors.append(f"{row_id}: unit_locator {unit_loc!r} not found in snapshot.")
                else:
                    unit_idx, unit_text = units_by_locator[unit_loc]
                    if not _contains_token(unit_text, answer):
                        errors.append(
                            f"{row_id}: answer {answer!r} missing at locator {unit_loc}."
                        )
                    if position == "end" and unit_idx <= last_plate_idx:
                        errors.append(
                            f"{row_id}: end fact at unit {unit_idx} is not after last plate "
                            f"caption at unit {last_plate_idx}."
                        )
            elif modality == "image":
                if _contains_token(all_target_text, answer):
                    errors.append(
                        f"{row_id}: image-only fact {answer!r} leaked into document text."
                    )

            if _contains_token(all_target_text, trap_answer):
                errors.append(
                    f"{row_id}: trap_answer {trap_answer!r} leaked into target document text."
                )

        if spec.leak_terms:
            leaks = find_leaks(
                [all_target_text, json.dumps(build_result.eval_rows)],
                spec.leak_terms,
            )
            if leaks:
                errors.append(f"Forbidden leak_terms detected in output: {leaks}")

    return ProposalVerificationReport(
        passed=(len(errors) == 0),
        total_target_files=len(build_result.target_paths),
        total_eval_rows=len(build_result.eval_rows),
        errors=errors,
    )
