import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_v13_codex_runtime_readiness import main


class ValidateV13CodexRuntimeReadinessTests(unittest.TestCase):
    def test_main_writes_v13_codex_runtime_readiness_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backend_execution = root / "backend_execution.json"
            runtime_check = root / "pyquda_runtime_check.json"
            runtime_candidates = root / "runtime_candidates.json"
            goal_audit = root / "goal_audit.json"
            readme = root / "README.md"
            bootstrap = root / "PYQUDA_RUNTIME_BOOTSTRAP.md"
            output = root / "v13_codex_runtime_readiness.json"

            backend_execution.write_text(
                json.dumps(
                    {
                        "backend_summary": {
                            "states": {"api": "usable", "auto": "usable", "codex": "fallback_only"},
                            "usable_backends": ["api", "auto"],
                            "fallback_only_backends": ["codex"],
                        },
                        "backends": [
                            {
                                "backend": "codex",
                                "availability_state": "fallback_only",
                                "repair_contract": {
                                    "category": "timeout",
                                    "detail_category": "codex_normalization_timeout",
                                    "repair_action_state": "conditional",
                                    "repair_actionable": False,
                                    "verification_command": "PYTHONPATH=src python3 -m pyquda_agent.cli run '...' --backend api",
                                    "repair_action_command": "PYTHONPATH=src python3 -m pyquda_agent.cli run '...' --backend api",
                                    "recommended_fix": "Switch to --backend api",
                                    "next_step": "Codex timed out on the normalization path.",
                                },
                                "cases": [
                                    {
                                        "case": "rough_pion",
                                        "backend_diagnostic": {
                                            "status": "fallback",
                                            "category": "timeout",
                                            "detail_category": "codex_normalization_timeout",
                                        },
                                        "backend_path": {
                                            "codex_preflight_skipped": True,
                                            "intent_primary_timeout_seconds": 30.0,
                                            "timeout_recovery_skipped": True,
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            runtime_check.write_text(
                json.dumps(
                    {
                        "status": "environment_missing",
                        "runtime_level": "environment_missing",
                        "blocker_categories": ["module_missing"],
                        "missing_modules": ["cupy", "pyquda"],
                        "primary_blocker": {"category": "module_missing", "module": "cupy"},
                        "shortest_remaining_steps": [
                            "Install CuPy into the target Python environment.",
                            "Build or install pyquda into the same environment.",
                        ],
                        "repo_pythonpath_diagnostic": {
                            "status": "not_attempted",
                            "detail": "Re-run with --use-repo-pythonpath for checkout visibility diagnostics.",
                        },
                    }
                ),
                encoding="utf-8",
            )
            runtime_candidates.write_text(
                json.dumps(
                    {
                        "any_ready": False,
                        "ready_candidates": [],
                        "summary": {
                            "best_candidate_status": "blocked",
                            "best_candidate_python": "/tmp/python3.13",
                            "blocker_categories": ["module_missing"],
                            "shortest_remaining_blockers": ["cupy", "pyquda"],
                        },
                    }
                ),
                encoding="utf-8",
            )
            goal_audit.write_text(
                json.dumps(
                    {
                        "backend_availability": {"api": "usable", "auto": "usable", "codex": "fallback_only"},
                    }
                ),
                encoding="utf-8",
            )
            readme.write_text("codex fallback_only\nruntime_proved\n", encoding="utf-8")
            bootstrap.write_text("scan_runtime_candidates.py\ncodex\nruntime_proved\n", encoding="utf-8")

            exit_code = main(
                [
                    "--backend-execution",
                    str(backend_execution),
                    "--runtime-check",
                    str(runtime_check),
                    "--runtime-candidates",
                    str(runtime_candidates),
                    "--goal-audit",
                    str(goal_audit),
                    "--readme",
                    str(readme),
                    "--runtime-bootstrap-doc",
                    str(bootstrap),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["suite"], "v13_codex_runtime_readiness")
            self.assertFalse(payload["answers"]["codex_backend_usable"]["answer"])
            self.assertFalse(payload["answers"]["local_runtime_proved"]["answer"])
            self.assertEqual(payload["answers"]["codex_backend_state"]["answer"], "fallback_only")
            self.assertIn("module_missing", payload["answers"]["runtime_remaining_blockers"]["answer"])
            observed = {case["case_id"]: case for case in payload["cases"]}
            self.assertTrue(observed["codex_backend_repair_contract"]["passed"])
            self.assertTrue(observed["runtime_remaining_blocker_contract"]["passed"])
            self.assertTrue(observed["docs_and_audit_consistent_with_reports"]["passed"])

    def test_main_accepts_usable_codex_without_repair_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            backend_execution = root / "backend_execution.json"
            runtime_check = root / "pyquda_runtime_check.json"
            runtime_candidates = root / "runtime_candidates.json"
            goal_audit = root / "goal_audit.json"
            readme = root / "README.md"
            bootstrap = root / "PYQUDA_RUNTIME_BOOTSTRAP.md"
            output = root / "v13_codex_runtime_readiness.json"

            backend_execution.write_text(
                json.dumps(
                    {
                        "backend_summary": {
                            "states": {"api": "usable", "auto": "usable", "codex": "usable"},
                            "usable_backends": ["api", "auto", "codex"],
                            "fallback_only_backends": [],
                        },
                        "backends": [
                            {
                                "backend": "codex",
                                "availability_state": "usable",
                                "repair_contract": None,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            runtime_check.write_text(
                json.dumps(
                    {
                        "status": "environment_missing",
                        "runtime_level": "environment_missing",
                        "blocker_categories": ["module_missing"],
                        "primary_blocker": {"category": "module_missing", "module": "cupy"},
                        "shortest_remaining_steps": ["Install CuPy into the target Python environment."],
                    }
                ),
                encoding="utf-8",
            )
            runtime_candidates.write_text(
                json.dumps(
                    {
                        "summary": {
                            "best_candidate_status": "blocked",
                            "best_candidate_python": "/tmp/python3.13",
                        },
                    }
                ),
                encoding="utf-8",
            )
            goal_audit.write_text(
                json.dumps(
                    {
                        "backend_availability": {"api": "usable", "auto": "usable", "codex": "usable"},
                    }
                ),
                encoding="utf-8",
            )
            readme.write_text("codex usable\nruntime_proved\n", encoding="utf-8")
            bootstrap.write_text("runtime_proved\nruntime\n", encoding="utf-8")

            exit_code = main(
                [
                    "--backend-execution",
                    str(backend_execution),
                    "--runtime-check",
                    str(runtime_check),
                    "--runtime-candidates",
                    str(runtime_candidates),
                    "--goal-audit",
                    str(goal_audit),
                    "--readme",
                    str(readme),
                    "--runtime-bootstrap-doc",
                    str(bootstrap),
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            observed = {case["case_id"]: case for case in payload["cases"]}
            self.assertTrue(observed["codex_backend_repair_contract"]["passed"])
            self.assertEqual(observed["codex_backend_repair_contract"]["observed"]["state"], "not_needed")
