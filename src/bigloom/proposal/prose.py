"""Cached prose generator for bigloom proposal (deterministic offline and Vertex Gemini)."""

from __future__ import annotations

import concurrent.futures as cf
import json
import random
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .facts import WorldEntities
from .spec import ProposalSpec


class ProseClientProtocol(Protocol):
    """Protocol for a text generation client used by write_prose."""

    def generate(
        self,
        prompt: str,
        *,
        json_mode: bool = False,
        temperature: float = 0.8,
    ) -> str: ...


class VertexGeminiClient:
    """Vertex AI Gemini REST client with token caching and retry backoff."""

    def __init__(
        self,
        project: str,
        account: str | None = None,
        model: str = "gemini-3.8-flash",
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.project = project
        self.account = account
        self.model = model
        self.sleep_fn = sleep_fn
        self.token = ""
        self.token_time = 0.0

    def _token(self) -> str:
        if not self.token or time.time() - self.token_time > 40 * 60:
            cmd = ["gcloud", "auth", "print-access-token"]
            if self.account:
                cmd += ["--account", self.account]
            self.token = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.token_time = time.time()
        return self.token

    def generate(
        self,
        prompt: str,
        *,
        json_mode: bool = False,
        temperature: float = 0.8,
    ) -> str:
        """Call Vertex AI generateContent and stop immediately on HTTP 401 or 403."""
        url = (
            f"https://aiplatform.googleapis.com/v1/projects/{self.project}/locations/global/"
            f"publishers/google/models/{self.model}:generateContent"
        )
        config: dict[str, object] = {"temperature": temperature, "maxOutputTokens": 8192}
        if json_mode:
            config["responseMimeType"] = "application/json"
        body = json.dumps(
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": config,
            }
        ).encode("utf-8")

        last_err: Exception | None = None
        for attempt in range(5):
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._token()}",
                    "Content-Type": "application/json",
                    "X-Goog-User-Project": self.project,
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=300) as res:
                    data = json.loads(res.read())
                parts = data["candidates"][0]["content"]["parts"]
                return "".join(p.get("text", "") for p in parts if not p.get("thought"))
            except urllib.error.HTTPError as err:
                if err.code in (401, 403):
                    detail = err.read()[:300] if err.fp else b""
                    raise RuntimeError(
                        f"Vertex AI permission error {err.code}: {detail!r}"
                    ) from err
                last_err = err
            except (urllib.error.URLError, KeyError, IndexError, TimeoutError) as err:
                last_err = err
            self.sleep_fn((2**attempt) * 3)
        raise RuntimeError(f"Gemini call failed after retries: {last_err}")


def section_count(spec: ProposalSpec, chapter: str) -> int:
    """Return the number of sections for a chapter or annex."""
    return spec.annex_sections if chapter.startswith("Annex") else spec.sections_per_chapter


def build_context(spec: ProposalSpec, entities: WorldEntities) -> str:
    """Build the system context prompt for a proposal topic and WorldLoom organisation."""
    if spec.context.strip():
        return spec.context.strip()
    zones_preview = ", ".join(entities.zones[:6])
    packages_preview = ", ".join(entities.packages[:6])
    return (
        f"You are writing part of a SYNTHETIC test document. The author is "
        f"{entities.agency_name}. The document is a formal funding proposal titled "
        f"'{spec.title}'. The programme covers sites and zones such as {zones_preview} "
        f"and work packages such as {packages_preview}. Write in formal British English, "
        "in the voice of a public-sector programme office. Use plain prose. IMPORTANT: "
        "do not state any specific dollar amount, budget total, contingency percentage, "
        "approval reference number, go-live date, sponsor name, or count of sensor nodes. "
        "Use qualitative words for these. Other numbers (areas, timelines in years, "
        "service levels) are allowed. Do not use Markdown headings or bold text. "
        "Separate paragraphs with one blank line. You can use short bullet lists that "
        "start with '- '."
    )


def _deterministic_section_titles(
    spec: ProposalSpec,
    entities: WorldEntities,
    chapter: str,
    count: int,
) -> list[str]:
    """Generate deterministic section titles for a chapter offline."""
    aspects = (
        "Programme scope and operational baseline",
        "Governance interface and agency coordination",
        "Architecture, data standards, and service controls",
        "Site readiness and phased delivery controls",
        "Assurance, service resilience, and risk mitigation",
        "Operational sustainment and performance review",
        "Inter-agency telemetry and platform integration",
        "Lifecycle management and continuous improvement",
    )
    titles: list[str] = []
    for i in range(count):
        zone = entities.zones[i % len(entities.zones)]
        aspect = aspects[i % len(aspects)]
        titles.append(f"{chapter}: {aspect} for {zone}")
    return titles


def _deterministic_section_prose(
    spec: ProposalSpec,
    entities: WorldEntities,
    chapter: str,
    title: str,
    ci: int,
    si: int,
    seed: int,
) -> str:
    """Generate deterministic multi-paragraph prose using WorldLoom entities without network calls."""
    rng = random.Random(f"{seed}:{ci}:{si}:{title}")
    paragraphs: list[str] = []
    for p_idx in range(6):
        zone = entities.zones[(ci + si + p_idx) % len(entities.zones)]
        pkg = entities.packages[(ci + p_idx) % len(entities.packages)]
        phase = entities.phases[(si + p_idx) % len(entities.phases)]
        bu = (
            entities.business_units[p_idx % len(entities.business_units)]
            if entities.business_units
            else spec.office
        )
        sys_name = (
            entities.systems[p_idx % len(entities.systems)]
            if entities.systems
            else "core telemetry platform"
        )
        lead = f"{rng.choice(entities.given_names)} {rng.choice(entities.surnames)}"
        para = (
            f"{entities.agency_name} coordinates the {spec.short_title} through the {spec.office} "
            f"in partnership with {bu}. Within the section '{title}' of '{chapter}', delivery teams "
            f"align the {pkg} workstream with the {sys_name} across {zone} under {phase}. "
            f"Operational working groups led by {lead} review interface schedules, data quality "
            f"thresholds, and service continuity procedures across each participating precinct. "
            f"All engineering baselines, telemetry schemas, and commissioning checklists follow "
            f"standard agency governance without altering the approved programme baseline."
        )
        paragraphs.append(para)

    bullets = "\n".join(
        [
            f"- Align {entities.packages[0]} workflows across {entities.zones[0]} and {entities.zones[1]}.",
            f"- Maintain service availability and audit traceability through {entities.agency_name}.",
            f"- Complete operational readiness reviews before transitioning to {entities.phases[-1]}.",
        ]
    )
    paragraphs.insert(3, bullets)
    return "\n\n".join(paragraphs)


def write_prose(
    cache: Path,
    spec: ProposalSpec,
    entities: WorldEntities,
    *,
    client: ProseClientProtocol | None = None,
    seed: int = 2026,
) -> None:
    """Populate the outline and section prose cache for all chapters in spec."""
    cache.mkdir(parents=True, exist_ok=True)
    use_gemini = client is not None or spec.prose.provider == "gemini"
    gem: ProseClientProtocol | None = client
    if use_gemini and gem is None:
        gem = VertexGeminiClient(
            project=spec.prose.project,
            account=spec.prose.account,
            model=spec.prose.model,
        )

    context_prompt = build_context(spec, entities)

    def outline(ci: int) -> None:
        path = cache / f"outline_{ci:02d}.json"
        if path.exists():
            return
        chapter = spec.chapters[ci]
        n = section_count(spec, chapter)
        if gem is None:
            titles = _deterministic_section_titles(spec, entities, chapter, n)
        else:
            prompt = (
                f"{context_prompt}\n\nList exactly {n} section titles for the chapter "
                f"'{chapter}'. Each title is specific to this programme and different "
                'from the others. Return JSON: {"sections": ["...", ...]}.'
            )
            raw = gem.generate(prompt, json_mode=True, temperature=0.6)
            titles = list(json.loads(raw)["sections"])[:n]
            while len(titles) < n:
                titles.append(f"{chapter} - Part {len(titles) + 1}")
        path.write_text(json.dumps(titles, indent=1), encoding="utf-8")

    def section(ci: int, si: int, title: str) -> None:
        path = cache / f"section_{ci:02d}_{si:02d}.txt"
        if path.exists() and path.stat().st_size > 200:
            return
        if gem is None:
            text = _deterministic_section_prose(
                spec,
                entities,
                spec.chapters[ci],
                title,
                ci,
                si,
                seed,
            )
        else:
            prompt = (
                f"{context_prompt}\n\nWrite the section '{title}' of the chapter "
                f"'{spec.chapters[ci]}'. Write between 1,100 and 1,400 words. Give "
                "concrete detail: named sites, agency roles, process steps, service "
                "levels, and design choices. Do not repeat the section title at the start."
            )
            text = gem.generate(prompt).strip()
        path.write_text(text, encoding="utf-8")

    workers = max(1, spec.prose.workers)
    with cf.ThreadPoolExecutor(workers) as pool:
        list(pool.map(outline, range(len(spec.chapters))))

    jobs: list[tuple[int, int, str]] = []
    for ci in range(len(spec.chapters)):
        titles = json.loads((cache / f"outline_{ci:02d}.json").read_text(encoding="utf-8"))
        jobs.extend((ci, si, str(t)) for si, t in enumerate(titles))

    with cf.ThreadPoolExecutor(workers) as pool:
        for fut in cf.as_completed([pool.submit(section, *j) for j in jobs]):
            fut.result()


def load_prose(cache: Path, spec: ProposalSpec) -> list[tuple[str, list[tuple[str, str]]]]:
    """Load cached chapter outlines and section bodies from disk."""
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for ci, chapter in enumerate(spec.chapters):
        titles = json.loads((cache / f"outline_{ci:02d}.json").read_text(encoding="utf-8"))
        secs = [
            (str(t), (cache / f"section_{ci:02d}_{si:02d}.txt").read_text(encoding="utf-8"))
            for si, t in enumerate(titles)
        ]
        out.append((chapter, secs))
    return out
