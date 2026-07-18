"""Deterministic, evidence-grounded tools for the ButterflyLens analyst."""

from .catalog import TOOL_ORDER, contract_document, tool_definitions
from .evaluation import EvaluationContractError, grade_trace
from .repository import ArtifactIntegrityError, SubmittedEvidenceRepository
from .tools import EvidenceToolbox, ToolContractError, ToolInputError

__all__ = [
    "ArtifactIntegrityError",
    "EvidenceToolbox",
    "EvaluationContractError",
    "SubmittedEvidenceRepository",
    "TOOL_ORDER",
    "ToolContractError",
    "ToolInputError",
    "contract_document",
    "grade_trace",
    "tool_definitions",
]
