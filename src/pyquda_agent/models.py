"""Shared data models for pyquda-agent."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field


@dataclass
class ContextSnippet:
    source: str
    path: str
    score: float
    summary: str
    excerpt: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ContextBundle:
    task_type: str
    index_summary: dict
    snippets: list[ContextSnippet] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type,
            "index_summary": self.index_summary,
            "snippets": [item.to_dict() for item in self.snippets],
        }


@dataclass
class GenerationResult:
    output_path: str
    script_style: str
    used_backend: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImplementationPlan:
    workflow_id: str
    task_type: str
    references: list[dict] = field(default_factory=list)
    external_citations: list[dict] = field(default_factory=list)
    convention_decisions: list[dict] = field(default_factory=list)
    clarification_trace: list[dict] = field(default_factory=list)
    runtime_readiness: dict | None = None
    physics_choices: dict = field(default_factory=dict)
    pyquda_choices: dict = field(default_factory=dict)
    runtime_choices: dict = field(default_factory=dict)
    validation_checks: list[str] = field(default_factory=list)
    field_resolution: dict = field(default_factory=dict)
    unresolved_fields: list[str] = field(default_factory=list)
    unsupported_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
