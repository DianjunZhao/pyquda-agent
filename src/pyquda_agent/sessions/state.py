"""Persist and restore task drafts."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
import json

from pyquda_agent.tasks.schema import Pion2ptTaskDraft


@dataclass
class SessionState:
    task_description: str
    draft: Pion2ptTaskDraft
    asked_questions: list[dict]
    context_bundle: dict | None = None
    implementation_plan: dict | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["draft"] = self.draft.to_dict()
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
        context_bundle=payload.get("context_bundle"),
        implementation_plan=payload.get("implementation_plan"),
    )
