"""Build large target files and small trap files from WorldLoom documents.

WorldLoom writes every document: its content, its prose, and its layout. BigLoom chooses
one document for each target, adds the test evidence (a text fact, an image fact, and a
canary trap), and pads the file to its target size. BigLoom writes no prose of its own.

Each size group uses its own WorldLoom world, unless the caller gives one corpus. Inside
a group, each target is a different document type, so no two targets are copies.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from .corpus import CorpusError, CorpusProvenance, resolve_corpus
from .formats import FORMATS, Format, Target, handler_for
from .formats.longform_filter import filtered_longform, scrub_ir
from .models import ManifestEntry
from .qualify import inspect_file_bytes
from .queries import generate_queries
from .questions import period_of, plan_targets
from .realism import (
    GATE_SENTENCE_WORDS,
    MAX_REPEATED_SENTENCE_RATE,
    file_findings,
    mask,
    repeated_sentence_rate,
    split_sentences,
    world_names,
)

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.models import ArtifactIR
    from worldloom.world import World

TRAP_MAX_BYTES = 1024 * 1024
#: The text fact must sit at this unit (a Word paragraph or cell, or a PDF text line) or deeper.
MIN_TEXT_DEPTH = 6


def _renderable(world: World, formats: Sequence[Format]) -> dict[str, set[str]]:
    """Render the world once. Return, for each document, the formats WorldLoom wrote for it.

    WorldLoom decides the formats of each document type. Revision files do not count.
    """
    out: dict[str, set[str]] = {}
    for item in world.render(*sorted(set(formats)))._rendered:
        path = str(item.path).replace("\\", "/")
        if not item.artifact_id or "/revisions/" in path:
            continue
        out.setdefault(item.artifact_id, set()).add(path.rsplit(".", 1)[-1])
    return out


#: Loop v2 target selection. A target prefers a document family (the WorldLoom filing domain) that
#: no earlier target in the group uses, then a type from this list, then the most prose. The real
#: reference holds service standards, guides, and product pages, while the old targets were all
#: finance documents and one incident review. `knowledge_article` is left out: its brief is about
#: 380 words in 2 sections, which is thin for a 2 MB or 5 MB file.
PREFERRED_TYPES: tuple[str, ...] = ("service_impact_assessment",)
#: Types that are never a target (see `PREFERRED_TYPES` for the reason).
EXCLUDED_TYPES: tuple[str, ...] = ("knowledge_article",)


def family_rank(domain: str, artifact_type: str, used_domains: set[str]) -> tuple[int, int]:
    """Return the selection rank of a document type: a new family first, then a preferred type."""
    return (int(domain in used_domains), int(artifact_type not in PREFERRED_TYPES))


def _choose(
    world: World,
    fmt: Format,
    formats_of: Mapping[str, set[str]],
    used_ids: set[str],
    used_types: set[str],
    rejected: Sequence[str] = (),
) -> tuple[ArtifactIR, str]:
    """Choose an unused document of a type not yet used, among the documents WorldLoom renders in `fmt`.

    A document from a family that no earlier target uses wins, then a preferred type
    (`family_rank`), then the most body prose, then the most visible sections.
    """
    intents = {i.id: i for i in world.artifact_intents}
    used_domains = {str(i.domain) for i in world.artifact_intents if i.artifact_type in used_types}
    candidates = []
    for ir in world.artifact_irs:
        intent = intents.get(ir.intent_id)
        if intent is None or fmt not in formats_of.get(ir.id, ()) or ir.id in used_ids:
            continue
        if intent.artifact_type in used_types or intent.artifact_type in EXCLUDED_TYPES:
            continue
        visible = [s for s in ir.sections if not s.hidden]
        words = sum(len((s.body or "").split()) for s in visible)
        rank = family_rank(str(intent.domain), intent.artifact_type, used_domains)
        candidates.append((rank, -words, -len(visible), ir.id, ir, intent.artifact_type))
    if not candidates:
        why = f" Rejected: {'; '.join(rejected)}." if rejected else ""
        raise CorpusError(
            f"No unused WorldLoom document type renders as {fmt} in this world.{why} Use other formats, "
            "fewer sizes, or a pack with more document types (for example packs/govtech.json)."
        )
    candidates.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
    _, _, _, _, ir, artifact_type = candidates[0]
    used_ids.add(ir.id)
    used_types.add(artifact_type)
    return ir, artifact_type


def _prose_defect(ir: ArtifactIR, names: Sequence[str]) -> str:
    """Return why the WorldLoom prose of a document fails the realism gate, or an empty string."""
    sentences = [
        mask(sentence, names)
        for sec in ir.sections
        if sec.body and not sec.hidden
        for sentence in split_sentences(sec.body, GATE_SENTENCE_WORDS)
    ]
    rate = repeated_sentence_rate(sentences)
    if rate > MAX_REPEATED_SENTENCE_RATE:
        return f"{rate:.0%} of its sentences repeat"
    return ""


def style_seed_for(world_seed: int, ir_id: str) -> int:
    """Return a stable style seed for one document. WorldLoom renderers read it from IR metadata."""
    return int(hashlib.sha256(f"{world_seed}:{ir_id}:style".encode()).hexdigest()[:8], 16)


def _with_style_seed(ir: ArtifactIR, seed: int) -> ArtifactIR:
    return ir.model_copy(update={"metadata": {**ir.metadata, "style_seed": str(seed)}})


def _unique_money(rng: random.Random, used: set[str], currency: str) -> str:
    while True:
        value = f"{currency} {rng.randint(1, 9)},{rng.randint(100, 999)},{rng.randint(100, 999)}"
        if value not in used:
            used.add(value)
            return value


def _unique_pct(rng: random.Random, used: set[str]) -> str:
    while True:
        value = f"{rng.randint(11, 89)}.{rng.randint(11, 99)}%"
        if value not in used:
            used.add(value)
            return value


#: Retail units that a public-sector document does not use, and the word it uses instead. The
#: govtech pack runs on the WorldLoom retail engine, so one fact counts "affected records" in SKUs.
PUBLIC_SECTOR_UNITS: dict[str, str] = {"SKUs": "records"}


def public_units(world: World) -> World:
    """Return the world for rendering, with public-sector unit words for a public-sector pack.

    Only the unit word changes, and only for this render pass. The fact ids, amounts, and the
    corpus on disk do not change, so the writer requests and the fact checks stay the same.
    """
    from .questions import _public_sector

    if not _public_sector(world):
        return world
    facts = []
    changed = False
    for fact in world.facts:
        value = getattr(fact, "value", None)
        unit = getattr(value, "unit", None) if value is not None else None
        if unit in PUBLIC_SECTOR_UNITS:
            fact = fact.model_copy(update={"value": value.model_copy(update={"unit": PUBLIC_SECTOR_UNITS[unit]})})
            changed = True
        facts.append(fact)
    return replace(world, _facts=tuple(facts)) if changed else world


def _render_pass(world: World, irs: Mapping[str, ArtifactIR], formats: Sequence[Format]) -> dict[tuple[str, str], bytes]:
    """Render the world with replaced IRs. Return payloads keyed by (artifact id, file kind).

    The file kind is the extension for a main file, or "v0.1.docx" for the first Word revision.
    """
    staged = replace(public_units(world), _artifact_irs=tuple(scrub_ir(irs.get(ir.id, ir)) for ir in world.artifact_irs))
    # Remove WorldLoom IDs and ledger appendices from every document of this pass.
    with filtered_longform():
        rendered = staged.render(*sorted(set(formats)))._rendered
    out: dict[tuple[str, str], bytes] = {}
    for item in rendered:
        if not item.artifact_id or item.artifact_id not in irs:
            continue
        name = Path(item.path).name
        if "/revisions/" in item.path or "/revisions/" in str(item.path).replace("\\", "/"):
            if "-v0.1." in name:
                out[(item.artifact_id, "v0.1." + name.rsplit(".", 1)[-1])] = item.payload
            continue
        ext = name.rsplit(".", 1)[-1]
        out.setdefault((item.artifact_id, ext), item.payload)
    return out


def _text_index(payload: bytes, ext: str, value: str) -> int:
    """Return the 1-based unit (a Word paragraph or cell, or a PDF line) where `value` first appears, or 0."""
    snap = inspect_file_bytes(payload, "." + ext)
    for idx, unit in enumerate(snap.units, 1):
        if value in unit.text or value.replace(" ", "") in unit.text.replace(" ", "").replace("\n", ""):
            return idx
    return 0


def build_corpus(
    out_dir: Path,
    *,
    sizes_mb: Sequence[float] = (18.0, 50.0, 100.0),
    seed: int = 42,
    formats: Sequence[str] = FORMATS,
    corpus_dir: Path | None = None,
    world_pack: str | None = None,
    domain: str | None = None,
    locale: str | None = None,
    facets: Mapping[str, str] | None = None,
    subject: str | None = None,
    writer: str = "template",
) -> list[ManifestEntry]:
    """Build large target files (up to 1 GiB) and paired trap files under 1 MB from WorldLoom documents."""
    if not sizes_mb or any(s <= 0 or s > 1024.0 for s in sizes_mb):
        raise ValueError("Every entry in sizes_mb must be between 0 and 1024 MiB (1 GiB).")
    fmts: list[Format] = []
    for raw in formats:
        fmt = raw.lower().strip().removeprefix(".")
        if fmt not in FORMATS:
            raise ValueError(f"Unsupported format '{raw}'.")
        fmts.append(handler_for(fmt).fmt)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "large").mkdir(parents=True, exist_ok=True)
    (out_dir / "traps").mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    used_values: set[str] = set()
    entries: list[ManifestEntry] = []
    counter = 0
    shared = corpus_dir is not None or bool(world_pack and not world_pack.lower().endswith(".json"))
    shared_world: tuple[World, CorpusProvenance] | None = None
    used_ids: set[str] = set()
    used_types: set[str] = set()
    used_labels: set[str] = set()

    for gi, size_mb in enumerate(sizes_mb):
        if shared:
            if shared_world is None:
                shared_world = resolve_corpus(
                    corpus_dir=corpus_dir, out_dir=out_dir, seed=seed, world_pack=world_pack,
                    domain=domain, locale=locale, facets=facets, writer=writer,
                )
            world, prov = shared_world
        else:
            used_ids, used_types = set(), set()
            world, prov = resolve_corpus(
                corpus_dir=None, out_dir=out_dir, seed=seed + gi, world_pack=world_pack, domain=domain,
                locale=locale, facets=facets, writer=writer, corpus_name="corpus" if gi == 0 else f"corpus-{gi + 1}",
            )
        currency = (world.company.currency or "SGD").upper()
        size_bytes = int(size_mb * 1024 * 1024)
        size_tag = f"{size_mb:g}mb".replace(".", "_")
        irs = {ir.id: ir for ir in world.artifact_irs}
        if not world.artifact_irs:
            raise CorpusError(
                f"The WorldLoom corpus '{prov.corpus_dir}' has no planned documents. BigLoom needs "
                "WorldLoom documents. Omit world_pack to build a new corpus, or give a pack JSON file."
            )
        formats_of = _renderable(world, fmts)
        names = world_names(world)
        for fmt in fmts:
            handler = handler_for(fmt)
            rejected: list[str] = []
            while True:
                ir, artifact_type = _choose(world, fmt, formats_of, used_ids, used_types, rejected)
                defect = _prose_defect(ir, names)
                if defect:
                    rejected.append(f"{artifact_type}: {defect}")
                    continue
                labels_before = set(used_labels)
                plan = plan_targets(world, [ir], [rng.randrange(6)], used_labels)[0]
                t = Target(
                    file_id=f"bl-{counter + 1:03d}-{fmt}-{size_tag}", fmt=fmt, size_bytes=size_bytes, ir_id=ir.id,
                    artifact_type=artifact_type, label=plan.text_label, chart_title=plan.chart_title,
                    chart_categories=plan.chart_categories, chart_peak=plan.chart_peak,
                    text_question=plan.text_question, image_question=plan.image_question,
                    text_golden=_unique_money(rng, used_values, currency),
                    text_canary=_unique_money(rng, used_values, currency),
                    image_golden=_unique_pct(rng, used_values), image_canary=_unique_pct(rng, used_values),
                )
                style_seed = style_seed_for(int(world.seed), t.ir_id)
                base_ir = _with_style_seed(irs[t.ir_id], style_seed)
                # One render pass for each target, so a planted value reaches no other document.
                main = _render_pass(world, {t.ir_id: handler.golden_ir(t, base_ir)}, [t.fmt]).get((t.ir_id, t.fmt))
                canary = _render_pass(world, {t.ir_id: handler.canary_ir(t, base_ir)}, [t.fmt])
                trap = canary.get((t.ir_id, handler.trap_kind()))
                if main is None or trap is None:
                    raise CorpusError(f"WorldLoom did not render {t.ir_id} as {t.fmt}.")
                findings = file_findings(inspect_file_bytes(main, "." + t.fmt))
                if findings:
                    # Safety step: the rendered file fails a realism reading. Try the next document.
                    rejected.append(f"{artifact_type}: {findings[0].code} ({findings[0].detail})")
                    used_labels.clear()
                    used_labels.update(labels_before)
                    continue
                depth = _text_index(main, t.fmt, t.text_golden) if handler.text_fact_in_render else MIN_TEXT_DEPTH
                if depth < MIN_TEXT_DEPTH:
                    # The document is too short to hold the fact deep enough. Try the next one.
                    rejected.append(f"{artifact_type}: the text fact sits at unit {depth}, below {MIN_TEXT_DEPTH}")
                    used_labels.clear()
                    used_labels.update(labels_before)
                    continue
                break
            counter += 1
            target_bytes = handler.finish_target(t, main, seed + counter)
            trap_bytes = handler.finish_trap(t, trap)
            final_depth = _text_index(target_bytes, t.fmt, t.text_golden)
            if final_depth < MIN_TEXT_DEPTH:
                raise CorpusError(f"The text fact of {t.file_id} sits at unit {final_depth}, below {MIN_TEXT_DEPTH}.")
            if len(trap_bytes) >= TRAP_MAX_BYTES:
                raise CorpusError(f"Trap for {t.file_id} is {len(trap_bytes)} bytes, above the 1 MB limit.")
            target_rel = f"large/{t.file_id}_final.{t.fmt}"
            trap_rel = f"traps/{t.file_id}_draft.{t.fmt}"
            (out_dir / target_rel).write_bytes(target_bytes)
            (out_dir / trap_rel).write_bytes(trap_bytes)
            ir = irs[t.ir_id]
            period = period_of(world, ir)
            topic = ir.title if world.company.name in ir.title else f"{world.company.name} {ir.title}"
            if subject and subject.strip():
                topic = f"{topic} — {subject.strip()}"
            entries.append(
                ManifestEntry(
                    file_id=t.file_id, format=t.fmt, target_file=target_rel, target_size_bytes=len(target_bytes),
                    target_sha256=hashlib.sha256(target_bytes).hexdigest(), distractor_file=trap_rel,
                    distractor_size_bytes=len(trap_bytes), distractor_sha256=hashlib.sha256(trap_bytes).hexdigest(),
                    topic=topic, period=period, distractor_period=f"{period} draft",
                    text_metric_label=t.label, text_golden_value=t.text_golden, text_canary_value=t.text_canary,
                    text_unit_index=final_depth,
                    image_chart_title=t.chart_title, image_golden_value=t.image_golden,
                    image_canary_value=t.image_canary, text_question=t.text_question,
                    image_question=t.image_question, document_title=ir.title, document_type=t.artifact_type,
                    style_seed=style_seed,
                    worldloom_commit=prov.worldloom_commit, world_seed=prov.world_seed,
                    recipe_digest=prov.recipe_digest, narration=prov.narration, model_id=prov.model_id,
                    prompt_version=prov.prompt_version,
                )
            )

    manifest_path = out_dir / "manifest.jsonl"
    manifest_path.write_text("\n".join(e.model_dump_json() for e in entries) + "\n", encoding="utf-8")
    generate_queries(manifest_path, out_dir / "cases.json")
    return entries
