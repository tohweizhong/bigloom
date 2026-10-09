"""BigLoom proposal generator package on top of WorldLoom."""

from .builder import (
    DocxLocator,
    ProposalBuildResult,
    build_proposal,
    write_proposal_docx,
)
from .facts import (
    ProposalTextFact,
    WorldEntities,
    load_world_entities,
    select_proposal_facts,
)
from .plates import Fig, encode_all, encode_job, make_figs, make_trap_figs
from .prose import (
    VertexGeminiClient,
    build_context,
    load_prose,
    section_count,
    write_prose,
)
from .spec import EvidencePosition, ProposalSpec, ProseConfig, load_proposal_spec
from .verify import ProposalVerificationReport, find_leaks, verify_proposal_outputs

__all__ = [
    "DocxLocator",
    "EvidencePosition",
    "Fig",
    "ProposalBuildResult",
    "ProposalSpec",
    "ProposalTextFact",
    "ProposalVerificationReport",
    "ProseConfig",
    "VertexGeminiClient",
    "WorldEntities",
    "build_context",
    "build_proposal",
    "encode_all",
    "encode_job",
    "find_leaks",
    "load_proposal_spec",
    "load_prose",
    "load_world_entities",
    "make_figs",
    "make_trap_figs",
    "section_count",
    "select_proposal_facts",
    "verify_proposal_outputs",
    "write_proposal_docx",
    "write_prose",
]
