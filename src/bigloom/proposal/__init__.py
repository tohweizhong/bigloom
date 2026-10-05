"""BigLoom proposal generator package on top of WorldLoom."""

from .facts import (
    ProposalTextFact,
    WorldEntities,
    load_world_entities,
    select_proposal_facts,
)
from .spec import EvidencePosition, ProposalSpec, ProseConfig, load_proposal_spec

__all__ = [
    "EvidencePosition",
    "ProposalSpec",
    "ProposalTextFact",
    "ProseConfig",
    "WorldEntities",
    "load_proposal_spec",
    "load_world_entities",
    "select_proposal_facts",
]
