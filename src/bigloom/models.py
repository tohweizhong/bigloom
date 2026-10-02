"""Typed data models for BigLoom qualification and leakage grading."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CanaryTrap(FrozenModel):
    """A planted value in a smaller distractor file that detects cross-file leakage."""

    distractor_file: str
    canary_value: str


class ManifestEntry(FrozenModel):
    """Metadata and planted facts for one rendered target file and its small trap file."""

    file_id: str
    format: Literal["docx", "xlsx", "pptx", "pdf"]
    target_file: str
    target_size_bytes: int
    target_sha256: str
    distractor_file: str
    distractor_size_bytes: int
    distractor_sha256: str
    topic: str
    period: str
    distractor_period: str
    text_metric_label: str
    text_golden_value: str
    text_canary_value: str
    text_unit_index: int
    image_chart_title: str
    image_golden_value: str
    image_canary_value: str


class EvalCase(FrozenModel):
    """One large-file evaluation question and its anti-leakage contract."""

    id: str
    query: str
    target_file: str
    modality: Literal["text", "image"]
    golden_value: str
    acceptable_values: tuple[str, ...] = ()
    min_unit_index: int = Field(default=1, ge=1)
    canary_trap: CanaryTrap | None = None

    @property
    def all_golden_values(self) -> tuple[str, ...]:
        seen: list[str] = []
        for val in (self.golden_value, *self.acceptable_values):
            cleaned = val.strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return tuple(seen)


class ViolationCode(StrEnum):
    """Reasons why a corpus or evaluation case fails build-time qualification."""

    MISSING_TARGET_FILE = "missing_target_file"
    GOLDEN_MISSING_IN_TARGET = "golden_missing_in_target"
    DUPLICATE_GOLDEN_IN_OTHER_FILE = "duplicate_golden_in_other_file"
    IMAGE_FACT_LEAKED_IN_TEXT = "image_fact_leaked_in_text"
    SHALLOW_PLACEMENT_SNIPPET_RISK = "shallow_placement_snippet_risk"
    CANARY_MISSING_IN_DISTRACTOR = "canary_missing_in_distractor"
    CANARY_COLLIDES_WITH_TARGET = "canary_collides_with_target"
    TARGET_NOT_RANKED_FIRST = "target_not_ranked_first"
    LOW_ENTROPY_GOLDEN_VALUE = "low_entropy_golden_value"


class QualificationViolation(FrozenModel):
    """One build-time anti-leakage violation."""

    case_id: str
    code: ViolationCode
    detail: str


class QualificationReport(FrozenModel):
    """Complete result of the build-time qualification gate."""

    passed: bool
    total_files: int
    total_cases: int
    violations: tuple[QualificationViolation, ...]


class LeakageVerdict(StrEnum):
    """Eval-time classification of each query response."""

    CORRECT_WITH_DOWNLOAD = "CORRECT_WITH_DOWNLOAD"
    SNIPPET_ONLY_LEAK = "SNIPPET_ONLY_LEAK"
    CROSS_FILE_LEAK_CANARY = "CROSS_FILE_LEAK_CANARY"
    CROSS_FILE_LEAK_CITATION = "CROSS_FILE_LEAK_CITATION"
    WRONG_ANSWER = "WRONG_ANSWER"


class EvalResponse(FrozenModel):
    """Observed response and AssistLog telemetry for one evaluation query."""

    case_id: str
    answer_text: str
    cited_files: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()


class CaseGrade(FrozenModel):
    """Leakage-aware grade for one evaluation query."""

    case_id: str
    verdict: LeakageVerdict
    matched_golden: bool
    matched_canary: bool
    cited_wrong_file: bool
    used_download_tool: bool
    detail: str


class GradeReport(FrozenModel):
    """Summary and per-query grades for an evaluation run."""

    total_cases: int
    counts: dict[str, int]
    results: tuple[CaseGrade, ...]
