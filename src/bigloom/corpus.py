"""Read a WorldLoom corpus as BigLoom input, or build one with the WorldLoom CLI.

BigLoom takes its content from a WorldLoom corpus folder (`world.json` plus JSONL files).
When the caller gives no corpus, BigLoom runs `worldloom build` for one period with the
`enterprise` realism profile and the WorldLoom template writer (`ComposedProvider`).
When a corpus has sections with no prose, BigLoom fills them with the same writer.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.world import World

WORLDLOOM_PIN = "3fcf194"
WORLDLOOM_REPO = "https://github.com/vamsiramakrishnan/worldloom"
INSTALL_COMMAND = f"pip install 'worldloom[all] @ git+{WORLDLOOM_REPO}@{WORLDLOOM_PIN}'"
COMPOSED_MODEL_ID = "composed-prose-2"
CACHE_ENV = "BIGLOOM_CORPUS_CACHE"
#: Narration writers that this track supports. The roadmap adds "handshake", "claude", and "codex".
WRITERS: tuple[str, ...] = ("template",)
DEFAULT_WRITER = "template"


class CorpusError(ValueError):
    """The corpus is missing, is not a WorldLoom corpus, or cannot be built."""


@dataclass(frozen=True)
class CorpusProvenance:
    """What a BigLoom run read from WorldLoom, so that the run can be repeated."""

    corpus_dir: str
    worldloom_commit: str
    world_seed: int
    recipe_digest: str
    narration: str
    model_id: str
    prompt_version: str


def require_worldloom() -> None:
    """Stop with the install command when the WorldLoom package is not installed."""
    try:
        import worldloom  # noqa: F401
    except ImportError as exc:
        raise CorpusError(
            f"The WorldLoom package is not installed. BigLoom needs WorldLoom commit {WORLDLOOM_PIN}. "
            f"Install it with: {INSTALL_COMMAND}"
        ) from exc


def worldloom_default_period() -> str:
    """Return the default reporting period of `worldloom build`, read from the WorldLoom CLI."""
    import inspect

    from worldloom import cli

    option = inspect.signature(cli.build).parameters["period"].default
    return str(getattr(option, "default", option))


def months_before(period: str, months: int) -> str:
    """Return the `YYYY-MM` period that is `months` months before `period`."""
    year, month = (int(part) for part in period.split("-")[:2])
    index = year * 12 + (month - 1) - months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def worldloom_commit() -> str:
    """Return the short Git commit of the installed WorldLoom checkout, or the pinned commit."""
    import worldloom

    root = Path(worldloom.__file__).resolve().parent
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short=7", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return out.stdout.strip() or WORLDLOOM_PIN
    except (OSError, subprocess.CalledProcessError):
        return WORLDLOOM_PIN


def _worldloom_cli() -> str:
    beside = Path(sys.executable).with_name("worldloom")
    if beside.is_file():
        return str(beside)
    found = shutil.which("worldloom")
    if not found:
        raise CorpusError(f"The `worldloom` command is not on PATH. Install it with: {INSTALL_COMMAND}")
    return found


def _build_args(
    out: Path,
    *,
    seed: int,
    locale: str | None,
    pack: str | None,
    domain: str | None,
    facets: Mapping[str, str] | None,
) -> list[str]:
    args = [
        _worldloom_cli(), "build", "--seed", str(seed),
        "--realism", "enterprise", "--narrate", "--out", str(out), "--overwrite",
    ]
    engine = "retail"
    if pack:
        args += ["--pack", pack]
        try:
            engine = str(json.loads(Path(pack).read_text(encoding="utf-8")).get("base", "retail")).strip().lower()
        except (OSError, ValueError):
            engine = "retail"
    elif domain:
        from worldloom import domains

        found = domains.by_name(domain.strip().lower())
        if found is None:
            raise CorpusError(f"Unknown WorldLoom domain '{domain}'. Known domains: {', '.join(domains.names())}.")
        args += ["--archetype", found.default_archetype]
        engine = found.name
    if engine == "retail":
        # Only the retail close takes an incident flag and a period count. Other engines run one episode.
        args += ["--incident", "--periods", "1"]
    if locale:
        args += ["--locale", locale.strip().lower()]
    for key, value in sorted((facets or {}).items()):
        args += ["--facet", f"{key}={value}"]
    return args


def build_worldloom_corpus(
    out: Path,
    *,
    seed: int,
    locale: str | None = None,
    pack: str | None = None,
    domain: str | None = None,
    facets: Mapping[str, str] | None = None,
) -> Path:
    """Run `worldloom build` into `out`. Reuse a cached copy when the same inputs ran before."""
    args = _build_args(out, seed=seed, locale=locale, pack=pack, domain=domain, facets=facets)
    key_parts = [WORLDLOOM_PIN, *args[2:]]
    key_parts[key_parts.index(str(out))] = "<out>"
    if pack and Path(pack).is_file():
        key_parts.append(hashlib.sha256(Path(pack).read_bytes()).hexdigest())
    key = hashlib.sha256("\x00".join(key_parts).encode()).hexdigest()[:20]
    cache_root = os.environ.get(CACHE_ENV)
    cached = Path(cache_root) / key if cache_root else None
    if cached is not None and (cached / "world.json").is_file():
        if out.exists():
            shutil.rmtree(out)
        shutil.copytree(cached, out)
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0 or not (out / "world.json").is_file():
        tail = (result.stderr or result.stdout).strip().splitlines()[-5:]
        raise CorpusError("`worldloom build` failed: " + " | ".join(tail))
    if cached is not None:
        cached.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(out, cached, dirs_exist_ok=True)
    return out


def _recipe_digest(world: World) -> str:
    payload = json.dumps(world.recipe, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def install_pack_types(world: World) -> int:
    """Register the document types of the company pack that the corpus recipe records.

    `worldloom build` registers pack document types while it builds. A corpus loaded later
    does not register them again, so its renderers skip every pack type. This installs
    them from the recipe record. Return the number of types in the record.
    """
    record = world.recipe.get("pack") if isinstance(world.recipe, dict) else None
    if not isinstance(record, dict) or not record.get("artifact_types"):
        return 0
    from worldloom import doctypes, packs

    pack = packs.Pack.model_validate(record)
    doctypes.install(pack.artifact_types)
    return len(pack.artifact_types)


def _narrate_open_sections(world: World) -> tuple[World, bool]:
    """Fill sections with no prose with `ComposedProvider`. Return the world and True when it filled any."""
    from worldloom.narrative.composer import ComposedProvider

    open_sections = any(s.awaiting_prose for ir in world.artifact_irs for s in ir.sections)
    if not open_sections:
        return world, False
    return world.narrate(ComposedProvider.for_world(world)), True


def resolve_corpus(
    *,
    corpus_dir: Path | None,
    out_dir: Path,
    seed: int,
    world_pack: str | None = None,
    domain: str | None = None,
    locale: str | None = None,
    facets: Mapping[str, str] | None = None,
    writer: str = DEFAULT_WRITER,
) -> tuple[World, CorpusProvenance]:
    """Return the WorldLoom world for a run and its provenance.

    Order: an explicit corpus folder, then a named or bundled corpus in `world_pack`,
    then a new corpus that `worldloom build` writes into `out_dir/corpus`.
    """
    if writer not in WRITERS:
        raise CorpusError(f"Unknown writer '{writer}'. Writers that work: {', '.join(WRITERS)}.")
    require_worldloom()
    from worldloom.world import World

    if world_pack and domain:
        raise CorpusError("Specify at most one of world_pack or domain.")

    pack_file: str | None = None
    if corpus_dir is not None:
        if not (corpus_dir / "world.json").is_file():
            raise CorpusError(
                f"'{corpus_dir}' is not a WorldLoom corpus: it has no world.json. "
                "Build one with `worldloom build --out <dir>`, or omit --corpus-dir."
            )
        source = corpus_dir
    elif world_pack and not (Path(world_pack).is_file() and world_pack.lower().endswith(".json")):
        source = Path(world_pack)
    else:
        pack_file = world_pack
        source = build_worldloom_corpus(
            out_dir / "corpus", seed=seed, locale=locale, pack=pack_file, domain=domain, facets=facets
        )

    try:
        world = World.load(source)
    except (OSError, ValueError) as exc:
        raise CorpusError(f"Cannot load the WorldLoom corpus '{source}': {exc}") from exc

    install_pack_types(world)
    world, filled = _narrate_open_sections(world)
    ledger = list(world.ledger)
    model_ids = sorted({e.model_id for e in ledger})
    prompt_versions = sorted({e.prompt_version for e in ledger})
    if filled:
        narration = "partial"
    elif model_ids and model_ids != [COMPOSED_MODEL_ID]:
        narration = "agent"
    else:
        narration = "composed"
    provenance = CorpusProvenance(
        corpus_dir=str(source),
        worldloom_commit=worldloom_commit(),
        world_seed=int(world.seed),
        recipe_digest=_recipe_digest(world),
        narration=narration,
        model_id=",".join(model_ids) or COMPOSED_MODEL_ID,
        prompt_version=",".join(prompt_versions),
    )
    return world, provenance
