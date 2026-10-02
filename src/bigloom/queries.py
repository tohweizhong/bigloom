"""Generate evaluation questions and canary trap specifications from manifest.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from .models import CanaryTrap, EvalCase, ManifestEntry


def load_manifest(manifest_path: Path) -> list[ManifestEntry]:
    """Load ManifestEntry records from a JSONL manifest file."""
    entries: list[ManifestEntry] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        entries.append(ManifestEntry.model_validate_json(cleaned))
    return entries


def generate_queries(manifest_path: Path, out_path: Path | None = None) -> list[EvalCase]:
    """Build two evaluation cases (one text, one image) per large file in manifest_path."""
    entries = load_manifest(manifest_path)
    cases: list[EvalCase] = []

    for entry in entries:
        text_case = EvalCase(
            id=f"{entry.file_id}-text",
            query=(
                f"What is the {entry.text_metric_label} in the "
                f"{entry.topic} {entry.period} Final Audit Report?"
            ),
            target_file=entry.target_file,
            modality="text",
            golden_value=entry.text_golden_value,
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entry.distractor_file,
                canary_value=entry.text_canary_value,
            ),
        )
        image_case = EvalCase(
            id=f"{entry.file_id}-image",
            query=(
                f"What is the verified metric on the {entry.image_chart_title} "
                f"chart in the {entry.topic} {entry.period} Final Audit Report?"
            ),
            target_file=entry.target_file,
            modality="image",
            golden_value=entry.image_golden_value,
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entry.distractor_file,
                canary_value=entry.image_canary_value,
            ),
        )
        cases.extend((text_case, image_case))

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [case.model_dump() for case in cases]
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return cases
