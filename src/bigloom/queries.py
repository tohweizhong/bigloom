"""Generate evaluation questions and canary trap specifications from manifest.jsonl.

The build writes each question into the manifest from the WorldLoom evaluation text (see
`questions.py`). This module pairs each question with its golden value and its trap.
"""

from __future__ import annotations

import csv
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


def _currency_aliases(value: str) -> tuple[str, ...]:
    """Return bare numeric aliases when value starts with a 3-letter currency code."""
    parts = value.strip().split(" ", 1)
    if len(parts) == 2 and len(parts[0]) == 3 and parts[0].isalpha():
        return (parts[1].strip(),)
    return ()


def generate_queries(manifest_path: Path, out_path: Path | None = None) -> list[EvalCase]:
    """Build two evaluation cases (one text, one image) per large file in manifest_path."""
    entries = load_manifest(manifest_path)
    cases: list[EvalCase] = []

    for entry in entries:
        if not entry.text_question or not entry.image_question:
            raise ValueError(
                f"Manifest entry '{entry.file_id}' has no questions. Rebuild the corpus with `bigloom build`."
            )
        text_case = EvalCase(
            id=f"{entry.file_id}-text",
            query=entry.text_question,
            target_file=entry.target_file,
            modality="text",
            golden_value=entry.text_golden_value,
            acceptable_values=_currency_aliases(entry.text_golden_value),
            min_unit_index=5,
            canary_trap=CanaryTrap(
                distractor_file=entry.distractor_file,
                canary_value=entry.text_canary_value,
            ),
        )
        image_case = EvalCase(
            id=f"{entry.file_id}-image",
            query=entry.image_question,
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
        csv_path = out_path.with_name("evals.csv")
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["query", "golden"])
            for case in cases:
                writer.writerow([case.query, case.golden_value])

    return cases
