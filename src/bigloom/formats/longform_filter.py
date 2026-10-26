"""Remove WorldLoom IDs and machine appendices from documents while BigLoom renders.

WorldLoom `longform.document()` builds the long document that the enterprise renderers
draw. It adds four appendices that list ledger IDs ("Sources of figures", "Data lineage",
"Measures and sources", "Chronology of events"), a "Fact" column with fact IDs in the
figure tables, artifact IDs in source captions and in the "Related documents" table, and a
document reference made of IDs. Real documents hold none of these. Search judges also used
them as a clue that a file is synthetic.

BigLoom does not change WorldLoom. While BigLoom renders, `filtered_longform()` wraps
`worldloom.longform.document` and passes each result through `filter_document`. The wrap
ends when the render pass ends.
"""

from __future__ import annotations

import contextlib
import functools
import inspect
import re
from collections.abc import Iterator
from dataclasses import replace
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.longform import Block, LongDocument, Part
    from worldloom.world import World

#: WorldLoom appendices that list ledger records. A test fails when WorldLoom renames one.
REMOVED_APPENDICES: tuple[str, ...] = (
    "Sources of figures",
    "Data lineage",
    "Measures and sources",
    "Chronology of events",
    "Related documents",
)
#: IR sections that list ledger records or synthetic sign-off rosters.
REMOVED_IR_SECTIONS: tuple[str, ...] = ("Lineage", "Approval")
#: The key of WorldLoom's "Related documents" appendix table. Only this table drops copied columns,
#: so a figure table with two equal columns (budget and actual) keeps both.
RELATED_TABLE = "related"
#: Table columns that hold only ledger IDs.
ID_COLUMNS: tuple[str, ...] = ("reference",)
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
#: A WorldLoom ID such as ART-0002, FACT-0017, or CO-0001-FINANCE-ART-0024.
_ID = re.compile(r"\b(?:[A-Z]{2,6}-)+\d{4}\b")
_PAREN_ID = re.compile(r"\s*\((?:[A-Z]{2,6}-)+\d{4}\)")


def missing_worldloom_headings() -> list[str]:
    """Return the removed headings that the WorldLoom source no longer holds."""
    from worldloom import documents, longform

    source = inspect.getsource(longform)
    missing = [h for h in REMOVED_APPENDICES if f'heading="{h}"' not in source]
    doc_source = inspect.getsource(documents)
    return missing + [h for h in REMOVED_IR_SECTIONS if f'heading="{h}"' not in doc_source]


def scrub_ir(ir: Any) -> Any:
    """Return a copy of an IR without ledger sections and without ID columns or ID cells.

    The workbook renderer draws IR sections directly, not through `longform.document`.
    """
    sections = [
        sec.model_copy(update={"table": _table(sec.table)}) if sec.table is not None else sec
        for sec in ir.sections
        if sec.heading not in REMOVED_IR_SECTIONS
    ]
    return ir.model_copy(update={"sections": sections})


def world_ids(world: World) -> set[str]:
    """Return every WorldLoom record ID in a world: facts, events, documents, and master data."""
    pools: list[Any] = [
        world.facts, world.events, world.artifact_irs, world.artifact_intents, world.business_units,
        world.sites, world.systems, world.services, world.people, world.categories, world.lore,
    ]
    ids = {str(world.company.id)}
    for pool in pools:
        for item in pool or ():
            ident = getattr(item, "id", None)
            if ident:
                ids.add(str(ident))
    return {i for i in ids if _ID.fullmatch(i)}


def readable_reference(reference: str, company: str, period: str, artifact_id: str) -> str:
    """Return a document reference that a person would write, for example "GTA/FIN/2026/024".

    It takes the company initials, the first three letters of the WorldLoom domain, the year
    of the period, and the document number.
    """
    name = re.sub(r"\([^)]*\)", " ", company)
    initials = "".join(w[0] for w in re.findall(r"[A-Za-z][A-Za-z]+", name) if w[0].isupper())[:6] or "DOC"
    parts = reference.split("-")
    domain = next((p for p in parts if p.isalpha() and len(p) > 2 and p not in ("ART", "FACT")), "GEN")[:3].upper()
    year = (re.search(r"\d{4}", period or "") or re.search(r"\d{4}", reference))
    number = int(re.sub(r"\D", "", artifact_id) or 0) % 1000
    return f"{initials}/{domain}/{year.group(0) if year else '0000'}/{number:03d}"


_NAMES: dict[str, str] = {}
"""ID to plain words, for the render pass in progress. `filtered_longform` fills it."""
_REFS: dict[str, str] = {}
"""Document ID to a readable reference ("GTA/FIN/2026/019"), for the render pass in progress."""
_TEXT_FACTS: list[str] = []
"""Text-valued facts that start with a capitalised regular word, for the render pass in progress."""


def text_fact_phrases(world: World) -> list[str]:
    """Return text-valued facts that start with a capitalised regular word, longest first."""
    proper = {str(world.company.name)}
    for pool in (world.business_units, world.sites, world.systems, world.services, world.people, world.categories):
        for item in pool or ():
            if getattr(item, "name", None):
                proper.add(str(item.name))
    out: set[str] = set()
    for fact in world.facts:
        text = (getattr(fact, "text_value", None) or "").strip().rstrip(".")
        if text and re.match(r"^[A-Z][a-z]*\b", text) and not any(text.startswith(p) for p in proper if p):
            out.add(text)
    return sorted(out, key=len, reverse=True)


def document_refs(world: World) -> dict[str, str]:
    """Return a readable reference for each WorldLoom document, in the form of the document's own."""
    out: dict[str, str] = {}
    for ir in world.artifact_irs:
        try:
            domain = str(world.artifact_intents.by_id(ir.intent_id).domain)
        except Exception:  # an IR with no intent keeps the generic domain
            domain = "general"
        raw = f"{world.company.id}-{domain.upper()}-{ir.id}"
        out[ir.id] = readable_reference(raw, world.company.name, world.period or "", ir.id)
    return out


def _clean(text: str) -> str:
    """Remove "(ID)" asides, replace a bare ID with plain words, and lowercase mid-sentence text facts."""
    text = _PAREN_ID.sub("", text or "")
    text = _ID.sub(lambda m: _NAMES.get(m.group(0), "the record"), text)
    for phrase in _TEXT_FACTS:
        text = re.sub(rf"(?<=[a-z,;:])(\s+){re.escape(phrase)}", rf"\1{phrase[0].lower()}{phrase[1:]}", text)
    return text


def id_names(world: World) -> dict[str, str]:
    """Return plain words for each WorldLoom ID: a quoted short statement for a text fact,
    the row label for a figure, the name of an entity, and the title of a document."""
    from worldloom import longform

    names: dict[str, str] = {}
    for fact in world.facts:
        text = (getattr(fact, "text_value", None) or "").strip().rstrip(".")
        if text:
            words = text.split()
            names[fact.id] = "\u201c" + " ".join(words[:8]) + ("\u2026" if len(words) > 8 else "") + "\u201d"
        else:
            names[fact.id] = "the " + longform.fact_label(fact).lower()
    for pool in (world.business_units, world.sites, world.systems, world.services, world.people, world.categories):
        for item in pool or ():
            if getattr(item, "id", None) and getattr(item, "name", None):
                names[str(item.id)] = str(item.name)
    for ir in world.artifact_irs:
        names[ir.id] = ir.title
    names[str(world.company.id)] = world.company.name
    return names


def _is_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID.fullmatch(value.strip()))


def _table(table: Any) -> Any:
    """Drop ID columns (declared, or holding only IDs), clear ID cells, and relabel ID rows."""
    if table is None:
        return None
    drop = set(ID_COLUMNS)
    for column in table.columns:
        values = [row.cells[column.key].value for row in table.rows if column.key in row.cells]
        filled = [v for v in values if v not in (None, "")]
        if filled and all(_is_id(v) for v in filled):
            drop.add(column.key)
    columns = [c for c in table.columns if c.key not in drop]
    rows = []
    for row in table.rows:
        cells = {
            k: (v.model_copy(update={"value": ""}) if _is_id(v.value) else v)
            for k, v in row.cells.items()
            if k not in drop
        }
        label = row.label
        if _is_id(label):
            title = cells.get("title")
            ref = _REFS.get(label.strip())
            label = ref or (str(title.value) if title is not None and title.value is not None else "")
        rows.append(row.model_copy(update={"cells": cells, "label": _clean(label)}))
    if table.key == RELATED_TABLE:
        columns, rows = _drop_copied_columns(columns, rows)
    return table.model_copy(update={"columns": columns, "rows": rows, "title": _clean(table.title)})


def _drop_copied_columns(columns: list[Any], rows: list[Any]) -> tuple[list[Any], list[Any]]:
    """Drop a column whose value equals an earlier column's value in every row (case is ignored).

    WorldLoom's "Related documents" table gives each document the same words for its type and for
    its role in the pack, so one column repeats the other. A real register does not.
    """
    def norm(row: Any, key: str) -> str:
        cell = row.cells.get(key)
        return " ".join(str(cell.value if cell is not None and cell.value is not None else "").split()).lower()

    kept: list[Any] = []
    for column in columns:
        copied = rows and any(
            all(norm(r, column.key) == norm(r, k.key) and norm(r, column.key) for r in rows) for k in kept
        )
        if not copied:
            kept.append(column)
    keys = {c.key for c in kept}
    rows = [r.model_copy(update={"cells": {k: v for k, v in r.cells.items() if k in keys}}) for r in rows]
    return kept, rows


def _block(block: Block, old: str, new: str) -> Block:
    number = block.number
    if old != new and number.startswith(f"{old}."):
        number = new + number[len(old):]
    return replace(
        block, text=_clean(block.text), caption=_clean(block.caption), source=_clean(block.source),
        number=number, table=_table(block.table),
    )


def _part(part: Part, number: str | None = None) -> Part:
    old = part.number
    new = number or old
    children = tuple(
        _part(child, new + child.number[len(old):] if child.number.startswith(old) else child.number)
        for child in part.children
    )
    return replace(
        part, number=new, heading=_clean(part.heading), blocks=tuple(_block(b, old, new) for b in part.blocks),
        children=children,
    )


def _distinct_comments(comments: tuple[Any, ...]) -> tuple[Any, ...]:
    """Keep the first review comment of each text.

    WorldLoom can give every section the same reviewer comment, so the review record repeats one
    sentence four times. A real reviewer does not write the same comment on every section.
    """
    seen: set[str] = set()
    out = []
    for c in comments:
        key = " ".join(c.text.split()).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return tuple(out)


def filter_document(doc: LongDocument) -> LongDocument:
    """Return the document without ledger appendices, ID columns, ID captions, or an ID reference.

    It also clears synthetic frontmatter and review/revision scaffolding, and empties the fields
    that the renderers write into file properties: the fact list, the provenance, and metadata that
    holds IDs.
    """
    kept = [p for p in doc.appendices if p.heading not in REMOVED_APPENDICES]
    appendices = tuple(_part(p, _LETTERS[i]) for i, p in enumerate(kept))
    reference = doc.reference
    if _ID.search(reference):
        reference = readable_reference(reference, doc.company, doc.period, doc.artifact_id)
    history = tuple(replace(r, status="", summary="") for r in doc.history)
    metadata = {k: v for k, v in doc.metadata.items() if not _ID.search(str(v))}
    return replace(
        doc,
        abstract="",
        subtitle="",
        reference=reference,
        parts=tuple(_part(p) for p in doc.parts),
        appendices=appendices,
        comments=(),
        history=history,
        revision=replace(doc.revision, status="", summary=_clean(doc.revision.summary)),
        related=(),
        provenance={},
        fact_ids=(),
        metadata=metadata,
    )


@functools.cache
def _check_headings() -> None:
    from ..corpus import CorpusError

    missing = missing_worldloom_headings()
    if missing:
        raise CorpusError(
            f"WorldLoom no longer has the appendices {missing}. Update REMOVED_APPENDICES in "
            "bigloom/formats/longform_filter.py before you build."
        )


@contextlib.contextmanager
def filtered_longform() -> Iterator[None]:
    """Wrap `worldloom.longform.document` and enterprise PDF/presenter helpers for one render pass."""
    from reportlab.platypus import PageBreak
    from worldloom import longform
    from worldloom.render.enterprise import pdf as epdf
    from worldloom.render.enterprise import presenter as epres

    _check_headings()
    original = longform.document
    orig_dist = epdf._distribution
    orig_ref = epdf._reference
    orig_doc_class = epdf._doc_class
    orig_shorten = epres._shorten

    def document(world: Any, *args: Any, **kwargs: Any) -> LongDocument:
        if not _NAMES:
            _NAMES.update(id_names(world))
            _REFS.update(document_refs(world))
            _TEXT_FACTS.extend(text_fact_phrases(world))
        return filter_document(original(world, *args, **kwargs))

    def _clean_doc_class(*args: Any, **kwargs: Any) -> Any:
        cls = orig_doc_class(*args, **kwargs)

        class _CleanReport(cls):  # type: ignore[valid-type, misc]
            def multiBuild(self, story: list[Any], *b_args: Any, **b_kwargs: Any) -> Any:
                for pt in self.pageTemplates:
                    if pt.id == "body":
                        pt.onPageEnd = lambda canvas, d: None
                first_pb = next((i for i, f in enumerate(story) if isinstance(f, PageBreak)), None)
                first_sec = next((i for i, f in enumerate(story) if getattr(f, "_wl_level", None) == 0), None)
                if first_pb is not None and first_sec is not None and first_sec > first_pb:
                    story = story[: first_pb + 1] + story[first_sec:]
                return super().multiBuild(story, *b_args, **b_kwargs)

        return _CleanReport

    def _clean_shorten(text: str, limit: int) -> str:
        if limit >= epres._BULLET_CHARS:
            return (text or "").strip()
        return orig_shorten(text, limit)

    longform.document = document  # type: ignore[assignment]
    epdf._distribution = lambda d: [d.audience]  # type: ignore[assignment]
    epdf._reference = lambda d: [("Reference", d.reference), ("Date", d.revision.at.strftime("%d %B %Y"))]  # type: ignore[assignment]
    epdf._doc_class = _clean_doc_class  # type: ignore[assignment]
    epres._shorten = _clean_shorten  # type: ignore[assignment]
    try:
        yield
    finally:
        longform.document = original  # type: ignore[assignment]
        epdf._distribution = orig_dist  # type: ignore[assignment]
        epdf._reference = orig_ref  # type: ignore[assignment]
        epdf._doc_class = orig_doc_class  # type: ignore[assignment]
        epres._shorten = orig_shorten  # type: ignore[assignment]
        _NAMES.clear()
        _REFS.clear()
        _TEXT_FACTS.clear()
