import json
import tempfile
import unittest
from pathlib import Path

from pyquda_agent.intent.interpreter import interpret_request
from pyquda_agent.sessions.state import SessionState
from pyquda_agent.sessions.state import load_session
from pyquda_agent.sessions.state import merge_session_into_current
from pyquda_agent.sessions.state import save_session
from pyquda_agent.tasks.clarifier import build_questions
from pyquda_agent.tasks.parser import parse_task_description


class StatefulClarificationTests(unittest.TestCase):
    def test_saved_session_preserves_confirmed_fields_and_minimal_missing_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            draft = parse_task_description("please compute pion 2pt outputs/run.py")
            draft.clarified_fields["gauge_path"] = "/tmp/cfg.lime"
            draft.missing_fields = ["mass", "lattice_size"]
            physics = interpret_request("please compute the pion two-point correlator")
            state = SessionState(
                task_description="req",
                draft=draft,
                asked_questions=[],
                physics_target=physics,
                backend_assistance={"selected_backend": "codex", "fallback": True, "fallback_category": "timeout"},
                confirmed_fields={"gauge_path": "/tmp/cfg.lime"},
                rejected_options={"start_from": "not propagator"},
                minimal_missing_fields=["mass", "lattice_size"],
            )
            save_session(path, state)
            loaded = load_session(path)
            self.assertEqual(loaded.confirmed_fields["gauge_path"], "/tmp/cfg.lime")
            self.assertEqual(loaded.minimal_missing_fields, ["mass", "lattice_size"])
            self.assertEqual(loaded.backend_assistance["fallback_category"], "timeout")

    def test_build_questions_does_not_repeat_already_clarified_fields(self):
        draft = parse_task_description("please compute pion 2pt outputs/run.py")
        draft.clarified_fields["gauge_path"] = "/tmp/cfg.lime"
        draft.field_sources["gauge_path"] = "clarified"
        questions = build_questions(draft, max_questions=10)
        self.assertFalse(any(question.field_name == "gauge_path" for question in questions))

    def test_build_questions_can_prioritize_resumed_pending_fields(self):
        draft = parse_task_description("please compute pion 2pt outputs/run.py")
        questions = build_questions(
            draft,
            max_questions=4,
            preferred_fields=["cluster_launch", "resource_path"],
        )
        self.assertFalse(any(question.field_name in {"cluster_launch", "resource_path"} for question in questions))

    def test_resume_session_inherits_confirmed_fields_without_overriding_new_request(self):
        saved_draft = parse_task_description("please compute pion 2pt outputs/run.py")
        saved_draft.gauge_path = "/tmp/old_cfg.lime"
        saved_draft.field_sources["gauge_path"] = "clarified"
        saved_physics = interpret_request("please compute the pion two-point correlator")
        state = SessionState(
            task_description="old",
            draft=saved_draft,
            asked_questions=[],
            physics_target=saved_physics,
            confirmed_fields={"gauge_path": "/tmp/old_cfg.lime", "resource_path": ".cache/quda"},
        )
        current_draft = parse_task_description("please compute pion 2pt from gauge /tmp/new_cfg.lime outputs/run.py")
        current_physics = interpret_request("I want a meson correlator script")
        merged_draft, merged_physics = merge_session_into_current(
            current_draft=current_draft,
            current_physics=current_physics,
            saved_state=state,
        )
        self.assertEqual(merged_draft.gauge_path, "/tmp/new_cfg.lime")
        self.assertEqual(merged_draft.resource_path, ".cache/quda")
        self.assertEqual(merged_draft.field_sources["resource_path"], "inherited")
        self.assertEqual(merged_draft.inherited_fields["resource_path"], ".cache/quda")
        self.assertEqual(merged_physics.confirmed_interpretation["target_id"], "pion_two_point_correlator")


if __name__ == "__main__":
    unittest.main()
