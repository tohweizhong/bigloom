"""Pydantic models and YAML loader for bigloom proposal specifications.

Separates inputs into:
1. User-supplied inputs in the YAML file (`world_pack` or `domain`, `subject`, `sizes_mb`).
2. WorldLoom runtime inputs (`World` entities and `FactLedger` facts, resolved in `facts.py`).
3. BigLoom derived defaults (titles, filenames, prefixes, and chapter skeleton from `genre`).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidencePosition(BaseModel):
    """Placement and modality for one evaluation fact in a proposal document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    position: Literal["start", "middle", "end"]
    modality: Literal["text", "image"]


class ProseConfig(BaseModel):
    """Prose generation settings for a proposal build."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Literal["deterministic", "gemini"] = "deterministic"
    model: str = "gemini-3.8-flash"
    project: str = "weizhong-project03"
    account: str | None = None
    workers: int = Field(default=8, ge=1)


DEFAULT_EVIDENCE_POSITIONS: tuple[EvidencePosition, ...] = (
    EvidencePosition(position="start", modality="text"),
    EvidencePosition(position="start", modality="text"),
    EvidencePosition(position="middle", modality="text"),
    EvidencePosition(position="middle", modality="text"),
    EvidencePosition(position="end", modality="text"),
    EvidencePosition(position="end", modality="text"),
    EvidencePosition(position="start", modality="image"),
    EvidencePosition(position="middle", modality="image"),
    EvidencePosition(position="end", modality="image"),
)

DEFAULT_FUNDING_PROPOSAL_CHAPTERS: tuple[str, ...] = (
    "Executive summary",
    "Strategic context and programme vision",
    "Problem statement and needs analysis",
    "Stakeholders, governance, and decision rights",
    "Proposed solution overview",
    "Technical architecture on Government on Commercial Cloud",
    "Data management, privacy, and security (IM8)",
    "Implementation plan and phasing",
    "Procurement strategy",
    "Financial analysis and budget",
    "Risk management",
    "Benefits realisation and key performance indicators",
    "Change management and stakeholder engagement",
    "Sustainability and climate resilience",
    "Annex A: Glossary and abbreviations",
    "Annex B: Detailed functional and non-functional requirements",
    "Annex C: Site plates and reference drawings",
    "Annex D: Summary of agency and public consultation",
    "Annex E: Assumptions, dependencies, and constraints",
)

_STOPWORDS = frozenset({"AND", "THE", "FOR", "OF", "IN", "ON", "TO", "WITH", "A", "AN"})


def _slugify(text: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+", text)
    return "-".join(tokens[:8]) or "Proposal"


def _derive_prefix(subject: str) -> str:
    words = [w.upper() for w in re.findall(r"[A-Za-z0-9]+", subject) if w.upper() not in _STOPWORDS]
    if not words:
        return "PRP"
    if len(words[0]) <= 4 and words[0].isalpha():
        initials = "".join(w[0] for w in words[:4])
        return initials if len(initials) >= 3 else words[0][:3]
    initials = "".join(w[0] for w in words[:4])
    return initials if len(initials) >= 3 else (words[0][:3]).upper()


class ProposalSpec(BaseModel):
    """Validated specification for building a large .docx proposal and trap twin.

    Required from user:
    - Exactly one of `world_pack` or `domain`
    - `subject` (one-line topic description)
    - `sizes_mb` (one or more target sizes in MiB, such as `[200, 500, 1024]`)

    Optional user overrides (otherwise derived by BigLoom or filled from WorldLoom at runtime):
    - `genre`, `prose`, `figures`, `evidence_positions`, `leak_terms`, `zones`, `packages`, `phases`
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # 1. Required from user
    world_pack: str | None = None
    domain: str | None = None
    subject: str = Field(min_length=3)
    sizes_mb: list[int] = Field(min_length=1)

    # 2. Optional user overrides (derived from subject/genre or WorldLoom at runtime when omitted)
    genre: Literal["funding_proposal"] = "funding_proposal"
    currency: str | None = None
    agency_name: str | None = None
    marking: str | None = None
    short_mark: str | None = None

    title: str = ""
    short_title: str = ""
    doc_ref: str = ""
    filename: str = ""
    trap_filename: str = ""
    id_prefix: str = ""
    ref_prefix: str = ""
    office: str = ""
    phase1_sites: str = ""
    module_name: str = ""
    approval_annex: str = "Annex F: Approval record"
    middle_chapter: str = "Implementation plan and phasing"
    context: str = ""

    sections_per_chapter: int = Field(default=6, ge=1)
    annex_sections: int = Field(default=3, ge=1)
    figures: int = Field(default=0, ge=0)

    chapters: list[str] = Field(default_factory=list)
    zones: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    phases: list[str] = Field(default_factory=list)
    leak_terms: list[str] = Field(default_factory=list)

    evidence_positions: list[EvidencePosition] = Field(
        default_factory=lambda: list(DEFAULT_EVIDENCE_POSITIONS)
    )
    prose: ProseConfig = Field(default_factory=ProseConfig)

    @model_validator(mode="before")
    @classmethod
    def _derive_defaults(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        raw = dict(data)
        subject = str(raw.get("subject") or "").strip()
        if not subject:
            return raw

        slug = _slugify(subject)
        prefix = str(raw.get("id_prefix") or _derive_prefix(subject)).strip()
        raw.setdefault("id_prefix", prefix)
        raw.setdefault("ref_prefix", f"{prefix}-DT")
        raw.setdefault("title", f"{subject}: Proposal for Funding Approval")
        raw.setdefault("short_title", subject)
        raw.setdefault("doc_ref", f"the {subject} funding proposal (final, v1.0)")
        raw.setdefault("filename", f"{slug}_Proposal-for-Funding-Approval_v1.0_FINAL.docx")
        raw.setdefault("trap_filename", f"{slug}_Proposal_DRAFT_v0.1_superseded.docx")
        raw.setdefault("office", f"{subject} Programme Office")
        if not raw.get("chapters"):
            raw["chapters"] = list(DEFAULT_FUNDING_PROPOSAL_CHAPTERS)
        if not raw.get("figures"):
            sizes = raw.get("sizes_mb") or [200]
            max_mb = max(int(s) for s in sizes) if isinstance(sizes, list) and sizes else 200
            raw["figures"] = max(24, min(480, round(max_mb * 0.48)))
        return raw

    @model_validator(mode="after")
    def _validate_world_and_chapters(self) -> ProposalSpec:
        if bool(self.world_pack) == bool(self.domain):
            raise ValueError("Specify exactly one of 'world_pack' or 'domain'.")
        if any(size <= 0 for size in self.sizes_mb):
            raise ValueError("Every entry in 'sizes_mb' must be a positive integer.")
        if self.middle_chapter not in self.chapters:
            raise ValueError(
                f"middle_chapter {self.middle_chapter!r} must appear in 'chapters'."
            )
        return self


def load_proposal_spec(path: Path) -> ProposalSpec:
    """Load and validate a YAML proposal spec from disk."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"Expected YAML mapping in {path}, got {type(raw).__name__}.")
    return ProposalSpec.model_validate(raw)
