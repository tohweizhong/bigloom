"""Build-time anti-leakage qualification gate powered by WorldLoom."""

from __future__ import annotations

import hashlib
import re
import zipfile
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from worldloom.evaluate.bm25 import Bm25
from worldloom.evaluate.tfidf import TfIdf
from worldloom.native_artifacts import NativeSnapshot, NativeUnit, inspect_artifact

from .evidence import BALLAST_NAME
from .models import (
    EvalCase,
    QualificationReport,
    QualificationViolation,
    ViolationCode,
)
from .realism import file_findings

SUPPORTED_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".pdf"}
#: The best passage of a target and of its trap must rank in positions 1 to TOP_K.
TOP_K = 3
#: A Word passage, and a long sheet passage, holds about this many words.
WORDS_PER_PASSAGE = 250
_LOW_ENTROPY_RE = re.compile(r"^\d{1,3}(?:\.0+)?%?$")


def _is_low_entropy_value(value: str) -> bool:
    """Return True when value is too short or is a bare 1-to-3 digit number or percentage."""
    cleaned = value.strip()
    if len(cleaned) < 4:
        return True
    return bool(_LOW_ENTROPY_RE.fullmatch(cleaned))


class PdfSnapshot(NativeSnapshot):
    """A PDF snapshot that also keeps the prose of each page, without table text.

    `prose_pages` holds the text set in the body font or larger: paragraphs and headings.
    WorldLoom sets table cells, captions, and running heads in smaller fonts, so they drop out.
    The realism readings use it, so that DOCX and PDF follow the same rule.
    """

    prose_pages: tuple[str, ...] = ()


def _prose_pages(fragments: Sequence[Sequence[tuple[float, str]]]) -> tuple[str, ...]:
    """Return, for each page, the fragments in the body font size or larger.

    The body size is the largest font size that carries at least a fifth of the characters
    in long fragments. Table text is smaller, and headings carry few characters.
    """
    weight: dict[float, int] = {}
    for page in fragments:
        for size, text in page:
            if len(text.split()) >= 5:
                weight[size] = weight.get(size, 0) + len(text)
    if not weight:
        return tuple("" for _ in fragments)
    total = sum(weight.values())
    body = max(size for size, chars in weight.items() if chars >= total / 5)
    return tuple("\n".join(text for size, text in page if size >= body - 0.3) for page in fragments)


def _without_ballast(payload: bytes) -> bytes:
    """Return the OOXML package without the BigLoom padding member.

    `inspect_artifact` reads every package member into memory and refuses packages above
    512 MiB expanded. The padding member holds no text, so the reader drops it first.
    """
    with zipfile.ZipFile(BytesIO(payload)) as src:
        if BALLAST_NAME not in src.namelist():
            return payload
        out = BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                if info.filename != BALLAST_NAME:
                    dst.writestr(info, src.read(info.filename))
        return out.getvalue()


def inspect_file_bytes(payload: bytes, suffix: str) -> NativeSnapshot:
    """Inspect native document bytes: WorldLoom for OOXML, pypdf for PDF.

    A PDF unit is one text line, with the locator "page:<n>/line:<m>". `pdf_pages` joins
    the lines of each page again.

    For OOXML, the BigLoom padding member is dropped before inspection, so files up to
    1 GiB stay inside the WorldLoom inspection budget. The snapshot keeps the size and the
    digest of the original file.
    """
    ext = suffix.lower().removeprefix(".")
    if ext in ("docx", "pptx", "xlsx"):
        snap = inspect_artifact(_without_ballast(payload), ext)
        metrics = {**snap.metrics, "file_size_bytes": len(payload)}
        return snap.model_copy(update={"sha256": hashlib.sha256(payload).hexdigest(), "metrics": metrics})
    if ext == "pdf":
        reader = PdfReader(BytesIO(payload))
        units: list[NativeUnit] = []
        metrics = {"file_size_bytes": len(payload), "pages": len(reader.pages)}
        fragments: list[list[tuple[float, str]]] = []
        for page_idx, page in enumerate(reader.pages, 1):
            found: list[tuple[float, str]] = []

            def visit(text: str, cm: object, tm: object, font: object, size: float, found=found) -> None:
                if text.strip():
                    found.append((round(float(size), 1), text.strip()))

            text = page.extract_text(visitor_text=visit) or ""
            # One unit for each text line, so depth counts lines, as DOCX counts paragraphs.
            lines = [line for line in text.splitlines() if line.strip()] or [""]
            units.extend(NativeUnit(locator=f"page:{page_idx}/line:{n}", text=line) for n, line in enumerate(lines, 1))
            fragments.append(found)
            images = len(page.images)
            if images:
                metrics[f"images_page_{page_idx}"] = images

        return PdfSnapshot(
            format="pdf",
            sha256=hashlib.sha256(payload).hexdigest(),
            units=tuple(units),
            metrics=metrics,
            prose_pages=_prose_pages(fragments),
        )
    raise ValueError(f"Unsupported file extension: {suffix}")


def pdf_pages(snap: NativeSnapshot) -> list[str]:
    """Return the text of each PDF page, joined from its line units."""
    pages: dict[int, list[str]] = {}
    for unit in snap.units:
        number = int(unit.locator.split("/")[0].removeprefix("page:"))
        pages.setdefault(number, []).append(unit.text)
    count = max([snap.metrics.get("pages", 0), *pages])
    return ["\n".join(t for t in pages.get(n, []) if t) for n in range(1, count + 1)]


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


def _reader_units(snap: NativeSnapshot) -> list[NativeUnit]:
    """Return the units a reader sees: no workbook type markers, sheet states, or formulas."""
    return [
        u
        for u in snap.units
        if u.text and not u.locator.endswith(("/type", "/state")) and not u.text.startswith("=")
    ]


def _chunk(lines: Sequence[str]) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    count = 0
    for line in lines:
        buf.append(line)
        count += len(line.split())
        if count >= WORDS_PER_PASSAGE:
            out.append("\n".join(buf))
            buf, count = [], 0
    if buf:
        out.append("\n".join(buf))
    return out


def passages_of(snap: NativeSnapshot) -> list[str]:
    """Split one file into passages: a page for PDF, a slide for PPTX, a sheet for XLSX, word chunks for DOCX.

    Search systems index passages, not whole files. A file then takes the position of its
    best passage, so a long workbook competes with its relevant sheet, not with all its cells.
    """
    units = _reader_units(snap)
    if snap.format in ("pdf", "pptx", "xlsx"):
        groups: dict[str, list[str]] = {}
        for u in units:
            groups.setdefault(u.locator.split("/")[0], []).append(u.text)
        result: list[str] = []
        for lines in groups.values():
            result.extend(_chunk(lines))
        return result
    return _chunk([u.text for u in units])


def _file_order(engine: Bm25 | TfIdf, query: str, owners: Sequence[str]) -> list[str]:
    order: list[str] = []
    for idx, _score in engine.rank(query, limit=len(owners)):
        if owners[idx] not in order:
            order.append(owners[idx])
    return order


def _unit_matches(units: Sequence[NativeUnit], needle: str) -> list[tuple[int, str]]:
    """Return 1-based unit indices and locators where needle appears on word boundaries."""
    low_needle = needle.strip().lower()
    if not low_needle:
        return []
    pattern = re.compile(
        r"(?<![0-9a-z])" + re.escape(low_needle) + r"(?![0-9a-z])(?!\.\d)"
    )
    hits: list[tuple[int, str]] = []
    for idx, unit in enumerate(units, 1):
        if pattern.search(unit.text.lower()):
            hits.append((idx, unit.locator))
    return hits


def qualify_corpus(
    snapshots: dict[str, NativeSnapshot],
    cases: Sequence[EvalCase],
    *,
    check_retrieval: bool = True,
    check_realism: bool = True,
) -> QualificationReport:
    """Run all build-time anti-leakage checks across snapshots and evaluation cases.

    With `check_realism`, each DOCX and PDF file must also pass the realism readings in
    `realism.file_findings`. A realism violation names the file in `case_id` as "file:<path>".
    """
    violations: list[QualificationViolation] = []
    if check_realism:
        for rel in sorted(snapshots):
            for finding in file_findings(snapshots[rel]):
                violations.append(
                    QualificationViolation(case_id=f"file:{rel}", code=ViolationCode(finding.code), detail=finding.detail)
                )
    file_names = sorted(snapshots.keys())
    owners: list[str] = []
    passage_texts: list[str] = []
    for rel in file_names:
        for passage in passages_of(snapshots[rel]):
            owners.append(rel)
            passage_texts.append(passage)
    use_retrieval = check_retrieval and len(file_names) > 1 and bool(passage_texts)
    bm25 = Bm25(passage_texts) if use_retrieval else None
    tfidf = TfIdf(passage_texts) if use_retrieval else None

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
        elif case.modality == "image" and target_hits:
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

        # Retrieval check: the best passage of the target and of its trap must rank in 1..TOP_K.
        if bm25 is not None and tfidf is not None:
            wanted = [case.target_file]
            if case.canary_trap is not None and case.canary_trap.distractor_file in snapshots:
                wanted.append(case.canary_trap.distractor_file)
            positions: dict[str, dict[str, int | None]] = {}
            passed = False
            for name, engine in (("bm25", bm25), ("tfidf", tfidf)):
                order = _file_order(engine, case.query, owners)
                pos = {f: (order.index(f) + 1 if f in order else None) for f in wanted}
                positions[name] = pos
                if all(p is not None and p <= TOP_K for p in pos.values()):
                    passed = True
            if not passed:
                violations.append(
                    QualificationViolation(
                        case_id=case.id,
                        code=ViolationCode.TARGET_OR_TRAP_NOT_IN_TOP3,
                        detail=(
                            f"Target and trap must both rank in positions 1 to {TOP_K}. "
                            f"BM25 positions: {positions['bm25']}. TF-IDF positions: {positions['tfidf']}."
                        ),
                    )
                )

    return QualificationReport(
        passed=len(violations) == 0,
        total_files=len(snapshots),
        total_cases=len(cases),
        violations=tuple(violations),
    )
