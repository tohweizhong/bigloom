"""Derive the planted labels and the natural questions from a WorldLoom world.

The measure in each label comes from a WorldLoom fact kind in the chosen document. The
question wording comes from the WorldLoom evaluation text, with the pack overrides applied
(the pack `evaluation_text`). BigLoom adds only the test-design part: the word "revised
forecast", which marks the value that the final document holds and the draft does not.
"""

from __future__ import annotations

import calendar
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from worldloom.models import ArtifactIR
    from worldloom.world import World

# Test design: the final document holds a revised forecast. The draft holds another value.
PLANTED_QUALIFIER = "revised {noun} forecast"
# A question that opens "What was" or "What is" with no article before the noun phrase.
_ARTICLE_GAP = re.compile(r"^(What (?:was|is))\s+(?!the\b|a\b|an\b)", flags=re.IGNORECASE)


@dataclass(frozen=True)
class Measure:
    """One WorldLoom measure: the fact kind without its state suffix, and its noun."""

    base: str
    noun: str


@dataclass(frozen=True)
class Plan:
    """The labels and questions for one target file."""

    text_label: str
    text_question: str
    chart_title: str
    chart_categories: tuple[str, ...]
    chart_peak: int
    image_question: str


def sentence_case(text: str) -> str:
    """Upper-case the first letter only, so acronyms such as CET1 keep their case."""
    return text[:1].upper() + text[1:]


def period_of(world: World, ir: ArtifactIR) -> str:
    """Return the most common fact period in the document, or the world period."""
    facts = {f.id: f for f in world.facts}
    periods = [facts[f].period for f in ir.fact_ids() if f in facts and facts[f].period]
    return Counter(periods).most_common(1)[0][0] if periods else (world.period or "")


def _base(kind: str) -> str:
    for suffix in (".actual", ".budget", ".variance", ".forecast"):
        if kind.endswith(suffix):
            return kind[: -len(suffix)]
    return kind


def _is_money(unit: str, currency: str) -> bool:
    """Return True for a unit in the company currency, for example "AUD" or "AUD_thousands"."""
    head = unit.split("_", 1)[0].upper()
    if currency:
        return head == currency.upper()
    return unit.endswith(("_thousands", "_millions"))


def _measures(world: World, fact_ids: Sequence[str] | None, *, money: bool) -> list[Measure]:
    """Return the measures in `fact_ids` (or the whole world), most frequent first."""
    from worldloom.narrative.composer import measure_noun

    currency = (world.company.currency or "").upper()
    wanted = set(fact_ids) if fact_ids is not None else None
    counts: Counter[str] = Counter()
    nouns: dict[str, str] = {}
    nonzero: set[str] = set()
    for fact in world.facts:
        if wanted is not None and fact.id not in wanted:
            continue
        value = getattr(fact, "value", None)
        unit = getattr(value, "unit", None) if value is not None else None
        if not unit:
            continue
        if money and not _is_money(unit, currency):
            continue
        if not money and unit != "percent":
            continue
        base = _base(fact.kind)
        noun = measure_noun(base) or measure_noun(fact.kind)
        if not noun:
            continue
        counts[base] += 1
        nouns.setdefault(base, noun)
        if getattr(value, "amount", 0):
            nonzero.add(base)
    ranked = sorted((b for b in counts if b in nonzero), key=lambda b: (-counts[b], b))
    return [Measure(b, nouns[b]) for b in ranked]


def _pick(candidates: Sequence[Measure], used: set[str]) -> Measure | None:
    for m in candidates:
        if m.noun not in used:
            return m
    return None


def period_text(period: str) -> str:
    """Return "March 2026" for "2026-03". Return other forms unchanged."""
    match = re.fullmatch(r"(\d{4})-(\d{2})", period.strip())
    if not match:
        return period
    return f"{calendar.month_name[int(match.group(2))]} {match.group(1)}"


def evaluation_text(world: World) -> dict[str, str]:
    """Return the WorldLoom evaluation text with the pack overrides applied."""
    from worldloom.generators import episode_text
    from worldloom.generators.evaluation import EVAL_TEXT

    pack = (world.recipe or {}).get("pack") or {}
    return episode_text.merged(EVAL_TEXT, pack.get("evaluation_text") or None, field="evaluation_text")


def _direct_template(text: dict[str, str], measure: Measure) -> str | None:
    """Return the WorldLoom direct-lookup question for the measure, if one exists."""
    stem = measure.base.rsplit(".", 1)[-1].removesuffix("_pct")
    return text.get(f"q.direct.group_{stem}")


def _scope(title: str, company: str) -> str:
    return title if company in title else f"{company} {title}"


def text_question(text: dict[str, str], measure: Measure, label: str, period: str, scope: str) -> str:
    """Return the text question in the WorldLoom wording, scoped to one document."""
    template = _direct_template(text, measure)
    when = period_text(period)
    if template and "{period}" in template:
        sentence = template.format(period=when)
        hit = re.search(rf"\b{re.escape(measure.noun)}\b", sentence, flags=re.IGNORECASE)
        if hit:
            sentence = sentence[: hit.start()] + label + sentence[hit.end() :]
            # The label is one specific figure, so it takes "the": "What was the total revised ...".
            sentence = _ARTICLE_GAP.sub(r"\1 the ", sentence, count=1)
            return sentence.rstrip("?").rstrip() + f" in the {scope}?"
    return f"What is the {label} for {when} in the {scope}?"


def _dimensions(world: World) -> list[tuple[str, tuple[str, ...]]]:
    dims: list[tuple[str, tuple[str, ...]]] = []
    units = tuple(bu.name for bu in world.business_units)
    if len(units) >= 2:
        dims.append(("business unit", units[:6]))
    cats = tuple(c.name for c in getattr(world, "categories", ()) or ())
    if len(cats) >= 2:
        dims.append(("category", cats[:6]))
    sites = tuple(s.name for s in world.sites)
    if len(sites) >= 2:
        dims.append(("site", sites[:6]))
    return dims


def plan_targets(world: World, irs: Sequence[ArtifactIR], peaks: Sequence[int], used: set[str]) -> list[Plan]:
    """Return one plan for each document. No two plans in one call share a label.

    `used` holds the labels of earlier groups. A plan avoids them when the world has enough
    measures, so that a test set reuses no label.
    """
    text = evaluation_text(world)
    company = world.company.name
    money_all = _measures(world, None, money=True)
    pct_all = _measures(world, None, money=False)
    dims = _dimensions(world)
    if not money_all:
        raise ValueError("The WorldLoom world has no money facts, so BigLoom cannot plant a text fact.")
    if not dims:
        raise ValueError("The WorldLoom world has fewer than two business units, categories, or sites.")
    local: set[str] = set()
    plans: list[Plan] = []
    for ir, peak in zip(irs, peaks, strict=True):
        period = period_of(world, ir)
        scope = _scope(ir.title, company)
        own = _measures(world, list(ir.fact_ids()), money=True)
        money = _pick(own, local | used) or _pick(money_all, local | used) or _pick(own + money_all, local)
        if money is None:
            money = money_all[len(plans) % len(money_all)]
        text_label = PLANTED_QUALIFIER.format(noun=money.noun)
        local.add(money.noun)

        own_pct = _measures(world, list(ir.fact_ids()), money=False)
        pct = (
            _pick(own_pct + pct_all, local | used)
            or _pick(own_pct + pct_all, local)
            or (own_pct + pct_all or [None])[0]
        )
        image_noun = pct.noun if pct else f"{money.noun} growth"
        local.add(image_noun)
        # Choose the first dimension whose chart title no earlier target in the set uses.
        # `used` holds earlier chart titles too, so plans made one at a time stay unique.
        base_title = sentence_case(PLANTED_QUALIFIER.format(noun=image_noun))
        options = [(d, c, f"{base_title} by {d}") for d, c in dims]
        _dim, cats, chart_title = next(
            (o for o in options if o[2] not in used and o[2] not in local), options[len(plans) % len(options)]
        )
        local.add(chart_title)
        name = cats[peak % len(cats)]
        image_question = (
            f"In the {scope} for {period_text(period)}, what {image_noun} forecast does "
            f"the chart \"{chart_title}\" show for {name}?"
        )
        plans.append(
            Plan(
                text_label=text_label,
                text_question=text_question(text, money, text_label, period, scope),
                chart_title=chart_title,
                chart_categories=cats,
                chart_peak=peak % len(cats),
                image_question=image_question,
            )
        )
    used.update(local)
    return plans
