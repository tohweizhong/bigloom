"""Unit tests for WorldLoom entity loading and FactLedger fact selection."""

from __future__ import annotations

from pathlib import Path

from bigloom.proposal.facts import load_world_entities, select_proposal_facts
from bigloom.proposal.spec import load_proposal_spec


def test_load_world_entities_and_select_facts_from_world_pack() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    spec = load_proposal_spec(repo_root / "specs" / "gsw_proposal.yaml")

    entities = load_world_entities(spec, seed=2026)
    assert entities.agency_name
    assert entities.currency == "SGD"
    assert entities.marking
    assert entities.short_mark
    assert len(entities.given_names) >= 4
    assert len(entities.surnames) >= 4
    assert len(entities.world.facts) > 0

    ledger_ids = {f.id for f in entities.world.facts}
    text_facts = select_proposal_facts(spec, entities, seed=2026)

    assert len(text_facts) == 6
    positions = [f.where for f in text_facts]
    assert positions == ["start", "start", "middle", "middle", "end", "end"]

    answers = [f.answer for f in text_facts]
    assert len(set(answers)) == len(answers)

    for tf in text_facts:
        assert tf.fact_id in ledger_ids
        assert tf.trap_fact_id in ledger_ids
        assert tf.fact_id != tf.trap_fact_id
        assert tf.answer != tf.trap_answer
        assert tf.answer in tf.sentence
        assert tf.trap_answer not in tf.sentence
        assert tf.trap_answer in tf.trap_sentence
        assert tf.relation in {"supersedes", "comparator"}


def test_minimal_spec_resolves_worldloom_runtime_entities() -> None:
    from bigloom.proposal.spec import ProposalSpec

    spec = ProposalSpec(
        world_pack="retail-close",
        subject="Minimal Runtime Resolution Test",
        sizes_mb=[5],
    )
    entities = load_world_entities(spec, seed=2026)
    assert entities.agency_name == entities.world.company.name
    assert entities.currency == entities.world.company.currency
    assert len(entities.zones) >= 6
    assert len(entities.packages) >= 6
    assert len(entities.phases) == 6
    assert entities.phase1_sites
    assert entities.module_name

    facts = select_proposal_facts(spec, entities, seed=2026)
    assert len(facts) == 6
    assert all(f.answer != f.trap_answer for f in facts)
