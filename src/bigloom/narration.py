"""Agent-written prose through the WorldLoom narration handshake (`--writer handshake`).

The template writer gives each document a few hundred words. This module lets an agent
write the prose of the documents that can become targets, through the WorldLoom handshake.
WorldLoom states the rules and validates every response. BigLoom adds only the choice of
documents. All other sections keep the WorldLoom template writer.

The steps:

1. `prepare` builds a corpus with no prose. It chooses the candidate target documents and
   writes `narration/requests.json` with their WorldLoom requests only.
2. An agent answers each request in `narration/responses.json`. The rules are in the file:
   no digits outside `{{fact:ID}}` references, only the facts in the request, the voice,
   and about `target_words` words.
3. `accept` validates the responses with WorldLoom. When all pass, it commits them, fills
   the other sections with the template writer, and saves the corpus. The ledger then
   replays the corpus with no model call.
4. `bigloom build --corpus-dir <out>/corpus` builds the targets from that corpus.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .corpus import (
    CorpusError,
    build_worldloom_corpus,
    install_pack_types,
    require_worldloom,
)

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.world import World

NARRATION_DIR = "narration"
REQUESTS_FILE = "requests.json"
PLAN_FILE = "plan.json"
#: Candidate documents beyond one for each format, so the build can skip a document that fails a check.
SPARE_DOCUMENTS = 2


@dataclass(frozen=True)
class Prepared:
    """What `prepare` wrote."""

    corpus_dir: Path
    requests_path: Path
    artifact_ids: tuple[str, ...]
    requests: int
    target_words: int


def _load(corpus_dir: Path) -> World:
    require_worldloom()
    from worldloom.world import World

    world = World.load(corpus_dir)
    install_pack_types(world)
    return world


def _composed(world: World) -> World:
    from worldloom.narrative.composer import ComposedProvider

    return world.narrate(ComposedProvider.for_world(world))


def choose_candidates(world: World, requests: Sequence[Mapping[str, Any]], formats: Sequence[str], spares: int) -> list[str]:
    """Return the artifact ids that get agent prose: the documents with the largest word briefs.

    A candidate must render in one of `formats`. No two candidates share a document type,
    because a test set uses each type once.
    """
    from .build import _renderable

    formats_of = _renderable(_composed(world), list(formats))  # type: ignore[arg-type]
    types = {i.id: i.artifact_type for i in world.artifact_intents}
    intent_of = {ir.id: ir.intent_id for ir in world.artifact_irs}
    words: dict[str, int] = {}
    for req in requests:
        words[req["artifact_id"]] = words.get(req["artifact_id"], 0) + int(req.get("target_words", 0))
    ranked = sorted(words, key=lambda a: (-words[a], a))
    chosen: list[str] = []
    used_types: set[str] = set()
    for artifact_id in ranked:
        kind = types.get(intent_of.get(artifact_id, ""), "")
        if not set(formats) & formats_of.get(artifact_id, set()) or kind in used_types:
            continue
        chosen.append(artifact_id)
        used_types.add(kind)
        if len(chosen) >= len(formats) + spares:
            break
    if not chosen:
        raise CorpusError(f"No WorldLoom document in this corpus renders as {', '.join(formats)}.")
    return chosen


def public_terms(request: dict[str, Any], world: World) -> dict[str, Any]:
    """Add public-sector terms to a request whose facts measure gross profit or gross margin.

    Loop v2. The fact labels come from WorldLoom ledger keys (`financial.gross_profit.actual`), so
    every writer reads "profit" many times and no other word. A statutory board reports a surplus.
    The request `terminology` now names the word to write, the same word that BigLoom plants
    (`questions.PUBLIC_SECTOR_NOUNS`). The fact keys and values do not change.
    """
    from .questions import PUBLIC_SECTOR_NOUNS, _public_sector

    if not _public_sector(world):
        return request
    kinds = {str(f.get("kind", "")) for f in request.get("facts", [])}
    terms = dict(request.get("terminology") or {})
    for base, noun in PUBLIC_SECTOR_NOUNS.items():
        if any(k.startswith(base + ".") or k == base for k in kinds):
            stem = base.rsplit(".", 1)[-1]
            terms[stem] = f"This agency reports a {noun}. Write \"{noun}\" for the {base} facts, never a profit or margin term."
    if terms == (request.get("terminology") or {}):
        return request
    return {**request, "terminology": terms}


def prepare(
    out_dir: Path,
    *,
    seed: int,
    formats: Sequence[str] = ("docx", "pdf"),
    world_pack: str | None = None,
    domain: str | None = None,
    locale: str | None = None,
    facets: Mapping[str, str] | None = None,
    spares: int = SPARE_DOCUMENTS,
) -> Prepared:
    """Build a corpus with no prose, choose the candidate documents, and write their requests."""
    from worldloom.narrative import handshake

    corpus_dir = build_worldloom_corpus(
        out_dir / "corpus", seed=seed, locale=locale, pack=world_pack, domain=domain, facets=facets, narrate=False
    )
    world = _load(corpus_dir)
    document = handshake.requests_document(world)
    chosen = choose_candidates(world, document["requests"], formats, spares)
    document["requests"] = [public_terms(r, world) for r in document["requests"] if r["artifact_id"] in chosen]
    folder = out_dir / NARRATION_DIR
    folder.mkdir(parents=True, exist_ok=True)
    requests_path = folder / REQUESTS_FILE
    requests_path.write_text(handshake.dump(document), encoding="utf-8")
    (folder / PLAN_FILE).write_text(json.dumps({"artifact_ids": chosen, "formats": list(formats)}, indent=2) + "\n", encoding="utf-8")
    return Prepared(
        corpus_dir=corpus_dir,
        requests_path=requests_path,
        artifact_ids=tuple(chosen),
        requests=len(document["requests"]),
        target_words=sum(int(r.get("target_words", 0)) for r in document["requests"]),
    )


class _RoutingProvider:
    """Serve agent prose for the chosen documents and template prose for all others.

    WorldLoom records one provider id for a narration pass, so the id names both writers.
    """

    def __init__(self, agent: Any, template: Any, chosen: set[str], model_id: str) -> None:
        self.agent = agent
        self.template = template
        self.chosen = chosen
        self.id = f"{model_id}+{template.id}"

    def complete(self, request: Any, prompt: Any, facts: Any, *, feedback: str = "") -> Any:
        provider = self.agent if request.artifact_id in self.chosen else self.template
        return provider.complete(request, prompt, facts, feedback=feedback)


def accept(out_dir: Path, responses_path: Path, *, model_id: str = "agent") -> dict[str, Any]:
    """Validate the agent responses with WorldLoom, and commit them when all pass.

    Return a report: `accepted`, the number of responses, and the violations of each
    rejected response. Nothing is written unless every chosen request passes.
    """
    from worldloom.narrative import ResponseProvider, handshake
    from worldloom.narrative.composer import ComposedProvider

    corpus_dir = out_dir / "corpus"
    plan = json.loads((out_dir / NARRATION_DIR / PLAN_FILE).read_text(encoding="utf-8"))
    chosen = set(plan["artifact_ids"])
    world = _load(corpus_dir)
    responses = handshake.parse_responses(json.loads(responses_path.read_text(encoding="utf-8")))
    verdicts = handshake.review(world, responses)
    mine = {name: v for name, v in verdicts.items() if name.split("/", 1)[0] in chosen or name in responses}
    rejected = {
        name: [{"code": v.code, "detail": v.detail} for v in verdict.violations]
        for name, verdict in sorted(mine.items())
        if not verdict.accepted
    }
    report: dict[str, Any] = {"accepted": not rejected, "responses": len(responses), "rejected": rejected}
    if rejected:
        return report
    template = ComposedProvider.for_world(world)
    narrated = world.narrate(_RoutingProvider(ResponseProvider(responses, model_id=model_id), template, chosen, model_id), retries=0)
    narrated.export(corpus_dir, overwrite=True)
    report["corpus_dir"] = str(corpus_dir)
    report["agent_words"] = sum(len(r.text.split()) for r in responses.values())
    return report
