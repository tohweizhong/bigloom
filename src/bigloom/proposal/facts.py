"""Load WorldLoom entities and select canonical and draft facts for bigloom proposal."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from worldloom import sdk
from worldloom.models import CanonicalFact
from worldloom.narrative import references
from worldloom.render.values import corpus_locale
from worldloom.world import World

from .spec import ProposalSpec

DEFAULT_GIVEN = (
    "Wei Ming",
    "Hui Min",
    "Jun Jie",
    "Xin Yi",
    "Kai Wen",
    "Li Ting",
    "Muhammad",
    "Nurul",
    "Arjun",
    "Priya",
    "Daniel",
    "Rachel",
)
DEFAULT_SURNAMES = (
    "Tan",
    "Lim",
    "Lee",
    "Ng",
    "Ong",
    "Wong",
    "Goh",
    "Chua",
    "Koh",
    "Teo",
    "Abdullah",
    "Kumar",
)


@dataclass(frozen=True)
class WorldEntities:
    """WorldLoom organisation entities and canonical FactLedger resolved at runtime."""

    world: World
    agency_name: str
    currency: str
    marking: str
    short_mark: str
    given_names: tuple[str, ...]
    surnames: tuple[str, ...]
    business_units: tuple[str, ...]
    systems: tuple[str, ...]
    sites: tuple[str, ...]
    zones: tuple[str, ...]
    packages: tuple[str, ...]
    phases: tuple[str, ...]
    phase1_sites: str
    module_name: str


@dataclass(frozen=True)
class ProposalTextFact:
    """One proposal text fact backed by a WorldLoom FactLedger entry and draft twin."""

    fid: str
    where: Literal["start", "middle", "end"]
    question: str
    answer: str
    sentence: str
    trap_answer: str
    trap_sentence: str
    fact_id: str
    trap_fact_id: str
    relation: Literal["supersedes", "comparator"]


def _load_world(spec: ProposalSpec, seed: int) -> tuple[World, dict[str, object]]:
    """Load a WorldLoom World from a bundled pack, corpus directory, org-pack JSON, or domain."""
    pack_meta: dict[str, object] = {}
    if spec.world_pack:
        candidate = Path(spec.world_pack)
        if candidate.is_file() and candidate.suffix.lower() == ".json":
            pack_meta = json.loads(candidate.read_text(encoding="utf-8"))
            base_domain = str(pack_meta.get("base", "retail")).strip().lower()
            world = sdk.company(base_domain, seed=seed).build().world
            return world, pack_meta
        return World.load(spec.world_pack), pack_meta

    domain = (spec.domain or "retail").strip().lower()
    return sdk.company(domain, seed=seed).build().world, pack_meta


def load_world_entities(spec: ProposalSpec, *, seed: int = 2026) -> WorldEntities:
    """Extract agency name, currency, markings, names, and entities from WorldLoom at runtime."""
    world, pack_meta = _load_world(spec, seed)

    agency_name = (
        spec.agency_name
        or str(pack_meta.get("company_name") or "").strip()
        or world.company.name
    )
    currency = (
        (spec.currency or "").strip().upper()
        or str(pack_meta.get("currency") or "").strip().upper()
        or (world.company.currency or "SGD").strip().upper()
    )
    marking = (
        spec.marking
        or "OFFICIAL (CLOSED) // SENSITIVE NORMAL (SYNTHETIC TEST DATA)"
    )
    short_mark = (
        spec.short_mark
        or "OFFICIAL (CLOSED) // SENSITIVE NORMAL"
    )

    given: list[str] = []
    surnames: list[str] = []
    name_pools = pack_meta.get("name_pools")
    if isinstance(name_pools, dict):
        given.extend(str(x) for x in name_pools.get("given", []) if x)
        surnames.extend(str(x) for x in name_pools.get("family", []) if x)
    for person in world.people:
        parts = person.name.split()
        if len(parts) >= 2:
            first, last = " ".join(parts[:-1]), parts[-1]
            if first not in given:
                given.append(first)
            if last not in surnames:
                surnames.append(last)
    if len(given) < 4:
        given.extend(x for x in DEFAULT_GIVEN if x not in given)
    if len(surnames) < 4:
        surnames.extend(x for x in DEFAULT_SURNAMES if x not in surnames)

    business_units = tuple(bu.name for bu in world.business_units)
    systems = tuple(sys.name for sys in world.systems)
    sites = tuple(site.name for site in world.sites)

    zones_list = list(spec.zones) if spec.zones else list(sites)
    while len(zones_list) < 6:
        zones_list.append(f"Zone {len(zones_list) + 1}")
    zones = tuple(zones_list)

    pkg_list = list(spec.packages) if spec.packages else list(business_units) + list(systems)
    while len(pkg_list) < 6:
        pkg_list.append(f"Work Package {len(pkg_list) + 1}")
    packages = tuple(pkg_list[:8])

    if spec.phases:
        phases = tuple(spec.phases)
    else:
        phases = (
            f"Phase 1: {zones[0]} and {zones[1]}",
            f"Phase 2A: {zones[2]}",
            f"Phase 2B: {zones[3]}",
            f"Phase 3: {zones[4]}",
            f"Phase 4: {zones[5]}",
            "Phase 5: Full programme operations",
        )

    phase1_sites = spec.phase1_sites or f"{zones[0]} and {zones[1]}"
    module_name = spec.module_name or f"{zones[2]} twin module"

    return WorldEntities(
        world=world,
        agency_name=agency_name,
        currency=currency,
        marking=marking,
        short_mark=short_mark,
        given_names=tuple(given),
        surnames=tuple(surnames),
        business_units=business_units,
        systems=systems,
        sites=sites,
        zones=zones,
        packages=packages,
        phases=phases,
        phase1_sites=phase1_sites,
        module_name=module_name,
    )


def _find_fact_pair(
    facts: tuple[CanonicalFact, ...],
    facts_by_id: dict[str, CanonicalFact],
    used_ids: set[str],
    used_answers: set[str],
    locale: object,
    *,
    prefer_supersedes: bool = False,
    prefer_numeric: bool = True,
) -> tuple[CanonicalFact, CanonicalFact, Literal["supersedes", "comparator"], str, str]:
    """Select one target fact and its predecessor or comparator fact from WorldLoom."""
    if prefer_supersedes:
        for f in facts:
            if f.id in used_ids or not f.supersedes:
                continue
            pred = facts_by_id.get(f.supersedes)
            if pred is None or pred.id in used_ids:
                continue
            ans = references.render_value(f, locale=locale)  # type: ignore[arg-type]
            trap = references.render_value(pred, locale=locale)  # type: ignore[arg-type]
            if ans and trap and ans != trap and ans not in used_answers:
                return f, pred, "supersedes", ans, trap

    by_kind: dict[str, list[CanonicalFact]] = {}
    for f in facts:
        if prefer_numeric and f.value is None:
            continue
        by_kind.setdefault(f.kind, []).append(f)

    for group in by_kind.values():
        for i, target in enumerate(group):
            if target.id in used_ids:
                continue
            ans = references.render_value(target, locale=locale)  # type: ignore[arg-type]
            if not ans or ans in used_answers:
                continue
            for trap_fact in group[i + 1 :]:
                if trap_fact.id in used_ids:
                    continue
                trap = references.render_value(trap_fact, locale=locale)  # type: ignore[arg-type]
                if trap and trap != ans and trap not in used_answers:
                    return target, trap_fact, "comparator", ans, trap

    raise ValueError("Unable to find enough distinct canonical/comparator fact pairs in WorldLoom.")


def select_proposal_facts(
    spec: ProposalSpec,
    entities: WorldEntities,
    *,
    seed: int = 2026,
) -> list[ProposalTextFact]:
    """Build six start/middle/end proposal facts backed by WorldLoom FactLedger entries."""
    rng = random.Random(seed)
    facts = tuple(entities.world.facts)
    facts_by_id = {f.id: f for f in facts}
    locale = corpus_locale(entities.world)
    used_ids: set[str] = set()
    used_answers: set[str] = set()

    def claim_pair(*, prefer_supersedes: bool = False) -> tuple[CanonicalFact, CanonicalFact, Literal["supersedes", "comparator"], str, str]:
        target, trap_fact, rel, ans, trap = _find_fact_pair(
            facts,
            facts_by_id,
            used_ids,
            used_answers,
            locale,
            prefer_supersedes=prefer_supersedes,
        )
        used_ids.add(target.id)
        used_ids.add(trap_fact.id)
        used_answers.add(ans)
        used_answers.add(trap)
        return target, trap_fact, rel, ans, trap

    def pick_person() -> str:
        return f"{rng.choice(entities.given_names)} {rng.choice(entities.surnames)}"

    f1, tf1, r1, m_val, tm_val = claim_pair(prefer_supersedes=False)
    m = f"{entities.currency} {m_val.lstrip('$£€ ')}"
    tm = f"{entities.currency} {tm_val.lstrip('$£€ ')}"

    f2, tf2, r2, _, _ = claim_pair(prefer_supersedes=True)
    sp = pick_person()
    tsp = pick_person()
    while tsp == sp:
        tsp = pick_person()
    role = "Deputy Chief Executive (Synthetic)"

    f3, tf3, r3, n, tn = claim_pair(prefer_supersedes=False)
    f4, tf4, r4, _, _ = claim_pair(prefer_supersedes=True)
    d = f"{rng.randint(1, 28)} {rng.choice(['Mar', 'Jun', 'Sep', 'Nov'])} {rng.choice([2028, 2029])} (ledger {f4.id})"
    td = f"{rng.randint(1, 28)} {rng.choice(['Feb', 'May', 'Aug', 'Oct'])} 2027 (ledger {tf4.id})"

    f5, tf5, r5, _, _ = claim_pair(prefer_supersedes=False)
    rf = f"{spec.ref_prefix}/2026/{f5.id}"
    trf = f"{spec.ref_prefix}/2025/{tf5.id}"

    f6, tf6, r6, p_raw, tp_raw = claim_pair(prefer_supersedes=False)
    p = p_raw if p_raw.endswith("%") else f"{p_raw} ({f6.id})"
    tp = tp_raw if tp_raw.endswith("%") else f"{tp_raw} ({tf6.id})"

    return [
        ProposalTextFact(
            fid="T1",
            where="start",
            question=(
                f"According to {spec.doc_ref}, what is the total capital funding "
                "requested for the programme?"
            ),
            answer=m,
            sentence=(
                f"The total capital funding requested for the {spec.short_title} is {m}, "
                "phased over six financial years."
            ),
            trap_answer=tm,
            trap_sentence=f"The total capital funding requested for the {spec.short_title} is {tm}.",
            fact_id=f1.id,
            trap_fact_id=tf1.id,
            relation=r1,
        ),
        ProposalTextFact(
            fid="T2",
            where="start",
            question=f"According to {spec.doc_ref}, who is the accountable programme sponsor?",
            answer=sp,
            sentence=f"The accountable programme sponsor is {sp}, {role}.",
            trap_answer=tsp,
            trap_sentence=f"The accountable programme sponsor is {tsp}, {role}.",
            fact_id=f2.id,
            trap_fact_id=tf2.id,
            relation=r2,
        ),
        ProposalTextFact(
            fid="T3",
            where="middle",
            question=(
                f"According to {spec.doc_ref}, how many edge sensor nodes will "
                f"Phase 1 deploy across {entities.phase1_sites}?"
            ),
            answer=n,
            sentence=f"Phase 1 deploys {n} edge sensor nodes across {entities.phase1_sites}.",
            trap_answer=tn,
            trap_sentence=f"Phase 1 deploys {tn} edge sensor nodes across {entities.phase1_sites}.",
            fact_id=f3.id,
            trap_fact_id=tf3.id,
            relation=r3,
        ),
        ProposalTextFact(
            fid="T4",
            where="middle",
            question=f"According to {spec.doc_ref}, what is the go-live date for the {entities.module_name}?",
            answer=d,
            sentence=f"The {entities.module_name} goes live on {d}.",
            trap_answer=td,
            trap_sentence=f"The {entities.module_name} goes live on {td}.",
            fact_id=f4.id,
            trap_fact_id=tf4.id,
            relation=r4,
        ),
        ProposalTextFact(
            fid="T5",
            where="end",
            question=f"According to {spec.doc_ref}, what is the approval reference number?",
            answer=rf,
            sentence=f"Approval reference number: {rf}.",
            trap_answer=trf,
            trap_sentence=f"Approval reference number: {trf}.",
            fact_id=f5.id,
            trap_fact_id=tf5.id,
            relation=r5,
        ),
        ProposalTextFact(
            fid="T6",
            where="end",
            question=f"According to {spec.doc_ref}, what contingency did the approving authority approve?",
            answer=p,
            sentence=f"The approving authority approved a contingency of {p} of the capital funding.",
            trap_answer=tp,
            trap_sentence=f"The approving authority approved a contingency of {tp} of the capital funding.",
            fact_id=f6.id,
            trap_fact_id=tf6.id,
            relation=r6,
        ),
    ]
