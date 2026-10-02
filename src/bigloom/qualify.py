"""Build-time anti-leakage qualification gate powered by WorldLoom."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from typing import Sequence

from pypdf import PdfReader
from worldloom.evaluate.bm25 import Bm25
from worldloom.evaluate.tfidf import TfIdf
from worldloom.native_artifacts import NativeSnapshot, NativeUnit, inspect_artifact

from .models import (
    EvalCase,
    QualificationReport,
    QualificationViolation,
    ViolationCode,
)

SUPPORTED_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".pdf"}
_LOW_ENTROPY_RE = re.compile(r"^\d{1,3}(?:\.0+)?%?$")


def _is_low_entropy_value(value: str) -> bool:
    """Return True when value is too short or is a bare 1-to-3 digit number or percentage."""
    cleaned = value.strip()
    if len(cleaned) < 4:
        return True
    if _LOW_ENTROPY_RE.fullmatch(cleaned):
        return True
    return False


def inspect_file_bytes(payload: bytes, suffix: str) -> NativeSnapshot:
    """Inspect native document bytes via WorldLoom or pypdf for PDF files."""
    ext = suffix.lower().removeprefix(".")
    if ext in ("docx", "pptx", "xlsx"):
        return inspect_artifact(payload, ext)
    if ext == "pdf":
        reader = PdfReader(BytesIO(payload))
        units: list[NativeUnit] = []
        for page_idx, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            units.append(NativeUnit(locator=f"page:{page_idx}", text=text))
        import hashlib

        return NativeSnapshot(
            format="pdf",
            sha256=hashlib.sha256(payload).hexdigest(),
            units=tuple(units),
            metrics={"file_size_bytes": len(payload), "pages": len(reader.pages)},
        )
    raise ValueError(f"Unsupported file extension: {suffix}")


def load_corpus_snapshots(corpus_dir: Path) -> dict[str, NativeSnapshot]:
    """Load and inspect all supported files under corpus_dir keyed by relative POSIX path."""
    snapshots: dict[str, NativeSnapshot] = {}
    root = corpus_dir.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        rel = path.relative_to(root).as_posix()
        snapshots[rel] = inspect_file_bytes(path.read_bytes(), path.suffix)
    return snapshots


def _unit_matches(units: Sequence[NativeUnit], needle: str) -> list[tuple[int, str]]:
    """Return 1-based unit indices and locators where needle appears (case-insensitive)."""
    low_needle = needle.lower()
    hits: list[tuple[int, str]] = []
    for idx, unit in enumerate(units, 1):
        if low_needle in unit.text.lower():
            hits.append((idx, unit.locator))
    return hits


def qualify_corpus(
    snapshots: dict[str, NativeSnapshot],
    cases: Sequence[EvalCase],
    *,
    check_retrieval: bool = True,
) -> QualificationReport:
    """Run all build-time anti-leakage checks across snapshots and evaluation cases."""
    violations: list[QualificationViolation] = []
    file_names = sorted(snapshots.keys())
    full_texts = {
        rel: "\n".join(u.text for u in snap.units if u.text)
        for rel, snap in snapshots.items()
    }

    bm25 = Bm25([full_texts[f] for f in file_names]) if (check_retrieval and file_names) else None
    tfidf = TfIdf([full_texts[f] for f in file_names]) if (check_retrieval and file_names) else None

    for case in cases:
        for val in case.all_golden_values:
            if _is_low_entropy_value(val):
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.LOW_ENTROPY_GOLDEN_VALUE,
                        detail=(
                            f"Golden value '{val}' is too short or easy to guess. "
                            "Use a multi-digit figure, two-decimal percentage, or specific code."
                        ),
                    )
                )

        if case.target_file not in snapshots:
            violations.append(
                QualificationViolation(
                    case_id=case.id,
                    code=ViolationCode.MISSING_TARGET_FILE,
                    detail=f"Target file '{case.target_file}' is missing from the corpus.",
                )
            )
            continue

        target_snap = snapshots[case.target_file]
        target_hits: list[tuple[int, str]] = []
        for val in case.all_golden_values:
            target_hits.extend(_unit_matches(target_snap.units, val))

        if case.modality == "text":
            if not target_hits:
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.GOLDEN_MISSING_IN_TARGET,
                        detail=f"Golden value '{case.golden_value}' was not found in '{case.target_file}'.",
                    )
                )
            else:
                earliest_index = min(idx for idx, _ in target_hits)
                if earliest_index < case.min_unit_index:
                    violations.append(
                        QualificationViolation(
                            case_id=case.id,
                            code=ViolationCode.SHALLOW_PLACEMENT_SNIPPET_RISK,
                            detail=(
                                f"Golden value appears at unit {earliest_index} "
                                f"(< min_unit_index={case.min_unit_index}), risking snippet leakage."
                            ),
                        )
                    )
        elif case.modality == "image":
            if target_hits:
                locators = ", ".join(loc for _, loc in target_hits[:3])
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.IMAGE_FACT_LEAKED_IN_TEXT,
                        detail=(
                            f"Image-only golden value '{case.golden_value}' leaked into text "
                            f"of '{case.target_file}' at {locators}."
                        ),
                    )
                )

        # Global uniqueness check across all other files in the corpus.
        for other_file, other_snap in snapshots.items():
            if other_file == case.target_file:
                continue
            for val in case.all_golden_values:
                other_hits = _unit_matches(other_snap.units, val)
                if other_hits:
                    locators = ", ".join(loc for _, loc in other_hits[:3])
                    violations.append(
                        QualificationViolation(
                            case_id=case.id,
                            code=ViolationCode.DUPLICATE_GOLDEN_IN_OTHER_FILE,
                            detail=(
                                f"Golden value '{val}' also appears in '{other_file}' "
                                f"at {locators}."
                            ),
                        )
                    )

        # Canary trap validation if configured.
        if case.canary_trap is not None:
            trap = case.canary_trap
            if _is_low_entropy_value(trap.canary_value):
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.LOW_ENTROPY_GOLDEN_VALUE,
                        detail=(
                            f"Canary value '{trap.canary_value}' is too short or easy to match by chance."
                        ),
                    )
                )
            if trap.distractor_file not in snapshots:
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.CANARY_MISSING_IN_DISTRACTOR,
                        detail=f"Canary distractor file '{trap.distractor_file}' is missing.",
                    )
                )
            else:
                dist_hits = _unit_matches(snapshots[trap.distractor_file].units, trap.canary_value)
                if not dist_hits:
                    violations.append(
                        QualificationViolation(
                            case_id=case.id,
                            code=ViolationCode.CANARY_MISSING_IN_DISTRACTOR,
                            detail=(
                                f"Canary value '{trap.canary_value}' was not found in "
                                f"distractor file '{trap.distractor_file}'."
                            ),
                        )
                    )
            if _unit_matches(target_snap.units, trap.canary_value):
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.CANARY_COLLIDES_WITH_TARGET,
                        detail=(
                            f"Canary value '{trap.canary_value}' collides with text inside "
                            f"target file '{case.target_file}'."
                        ),
                    )
                )

        # Retrieval check using WorldLoom BM25 and TF-IDF.
        if check_retrieval and bm25 is not None and tfidf is not None and len(file_names) > 1:
            bm25_top = bm25.rank(case.query, limit=1)
            tfidf_top = tfidf.rank(case.query, limit=1)
            bm25_winner = file_names[bm25_top[0][0]] if bm25_top else None
            tfidf_winner = file_names[tfidf_top[0][0]] if tfidf_top else None
            if bm25_winner != case.target_file and tfidf_winner != case.target_file:
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.TARGET_NOT_RANKED_FIRST,
                        detail=(
                            f"Target '{case.target_file}' did not rank first in BM25 "
                            f"('{bm25_winner}') or TF-IDF ('{tfidf_winner}')."
                        ),
                    )
                )

    return QualificationReport(
        passed=len(violations) == 0,
        total_files=len(snapshots),
        total_cases=len(cases),
        violations=tuple(violations),
    )
