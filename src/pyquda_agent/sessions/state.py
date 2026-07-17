"""Persist and restore task drafts."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
import json

from pyquda_agent.intent.interpreter import MESON_UNSPECIFIED_TARGET_ID
from pyquda_agent.intent.schema import PhysicsTargetArtifact
from pyquda_agent.tasks.schema import Pion2ptTaskDraft


@dataclass
class SessionState:
    task_description: str
    draft: Pion2ptTaskDraft
    asked_questions: list[dict]
    physics_target: PhysicsTargetArtifact | None = None
    backend_assistance: dict | None = None
    confirmed_fields: dict | None = None
    rejected_options: dict | None = None
    minimal_missing_fields: list[str] | None = None
    workflow_match: dict | None = None
    context_bundle: dict | None = None
    implementation_plan: dict | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["draft"] = self.draft.to_dict()
        payload["physics_target"] = self.physics_target.to_dict() if self.physics_target is not None else None
        return payload


def save_session(path: Path, state: SessionState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_session(path: Path) -> SessionState:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SessionState(
        task_description=payload["task_description"],
        draft=Pion2ptTaskDraft.from_dict(payload["draft"]),
        asked_questions=payload.get("asked_questions", []),
        physics_target=PhysicsTargetArtifact.from_dict(payload["physics_target"]) if payload.get("physics_target") else None,
        backend_assistance=payload.get("backend_assistance"),
        confirmed_fields=payload.get("confirmed_fields"),
        rejected_options=payload.get("rejected_options"),
        minimal_missing_fields=payload.get("minimal_missing_fields"),
        workflow_match=payload.get("workflow_match"),
        context_bundle=payload.get("context_bundle"),
        implementation_plan=payload.get("implementation_plan"),
    )


def merge_session_into_current(
    *,
    current_draft: Pion2ptTaskDraft,
    current_physics: PhysicsTargetArtifact,
    saved_state: SessionState,
) -> tuple[Pion2ptTaskDraft, PhysicsTargetArtifact]:
    confirmed_fields = saved_state.confirmed_fields or {}
    for field_name, value in confirmed_fields.items():
        if not hasattr(current_draft, field_name):
            continue
        current_value = getattr(current_draft, field_name)
        if current_value not in (None, [], {}, ""):
            continue
        setattr(current_draft, field_name, value)
        current_draft.inherited_fields[field_name] = value
        current_draft.field_sources[field_name] = "inherited"

    saved_physics = saved_state.physics_target
    current_target_id = (current_physics.inferred_interpretation or {}).get("target_id")
    if (
        saved_physics is not None
        and saved_physics.confirmed_interpretation is not None
        and current_physics.confirmed_interpretation is None
        and current_target_id in (None, MESON_UNSPECIFIED_TARGET_ID)
    ):
        current_physics.confirmed_interpretation = dict(saved_physics.confirmed_interpretation)
        current_physics.candidate_targets = list(saved_physics.candidate_targets)
        current_physics.formula_proposals = list(saved_physics.formula_proposals)
        current_physics.status = "confirmed"
        target_id = saved_physics.confirmed_interpretation.get("target_id")
        if target_id is not None:
            current_physics.inherited_fields["target_id"] = target_id
            current_physics.clarified_fields.setdefault("target_id", target_id)
            current_physics.task_type_hint = saved_physics.task_type_hint or current_physics.task_type_hint
    return current_draft, current_physics
