"""Schemas for intent interpretation and clarification."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field


@dataclass
class ClarifyingQuestion:
    field_name: str
    prompt: str
    category: str
    scope: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PhysicsTargetArtifact:
    user_request: str
    status: str = "needs_interpretation"
    normalized_request: str | None = None
    candidate_targets: list[dict] = field(default_factory=list)
    inferred_interpretation: dict | None = None
    confirmed_interpretation: dict | None = None
    formula_proposals: list[dict] = field(default_factory=list)
    inherited_fields: dict[str, object] = field(default_factory=dict)
    user_confirmed_fields: dict[str, object] = field(default_factory=dict)
    inferred_fields: dict[str, object] = field(default_factory=dict)
    clarified_fields: dict[str, object] = field(default_factory=dict)
    parser_guesses: dict[str, object] = field(default_factory=dict)
    fixed_by_workflow_fields: dict[str, object] = field(default_factory=dict)
    unsupported_fields: dict[str, str] = field(default_factory=dict)
    local_references: list[str] = field(default_factory=list)
    external_citations: list[dict] = field(default_factory=list)
    external_lookup: dict = field(default_factory=dict)
    llm_assistance: dict = field(default_factory=dict)
    knowledge_boundary: dict = field(default_factory=dict)
    clarification_trace: list[dict] = field(default_factory=list)
    unsupported_reasons: list[str] = field(default_factory=list)
    chosen_workflow_target: str | None = None
    task_type_hint: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PhysicsTargetArtifact":
        return cls(**data)
