import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate_backend_execution import main


class ValidateBackendExecutionTests(unittest.TestCase):
    def test_main_writes_backend_execution_report(self):
        class Completed:
            def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
                self.stdout = stdout
                self.returncode = returncode
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None, timeout=None):
            output_path = Path(cmd[cmd.index("--output") + 1])
            output_path.with_suffix(".physics.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".task.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".plan.json").write_text(json.dumps({}), encoding="utf-8")
            request = cmd[4]
            rough_pion = "pi meson two-point" in request
            target_id = "meson_two_point_correlator_unspecified" if "meson correlator" in request else "pion_two_point_correlator"
            backend = cmd[cmd.index("--backend") + 1]
            if backend == "auto":
                backend_diagnostic = {
                    "status": "fallback",
                    "category": "timeout",
                    "failure_origin": "network",
                    "recovery_mode": "retry_or_switch_backend",
                    "retryable_now": True,
                }
                llm_assistance = {
                    "used": False,
                    "attempted": True,
                    "fallback": True,
                    "requested_backend": "auto",
                    "selected_backend": "codex",
                    "selection_reason": "Mocked auto backend selected codex before falling back to rules.",
                    "fallback_reason": "mock auto fallback",
                    "fallback_category": "timeout",
                    "codex_preflight_attempted": not rough_pion,
                    "codex_preflight_status": "skipped" if rough_pion else "failed",
                    "codex_preflight_category": None if rough_pion else "timeout",
                    "codex_preflight_reason": None if rough_pion else "mock timeout",
                    "codex_preflight_skipped": rough_pion,
                    "codex_preflight_skip_reason": (
                        "Skipped auto-mode codex preflight because the request is a rough normalization-only path and no configured API backend was available."
                        if rough_pion
                        else None
                    ),
                    "codex_preflight_soft_failed": not rough_pion,
                    "codex_preflight_soft_failure_reason": "mock timeout" if not rough_pion else None,
                    "session_backend_memory_considered": False,
                    "session_backend_memory_used": False,
                    "session_backend_memory_reason": None,
                    "session_backend_prior_category": None,
                    "intent_primary_timeout_seconds": 10.0 if rough_pion else 12.0,
                    "timeout_recovery_attempted": not rough_pion,
                    "timeout_recovery_skipped": rough_pion,
                    "timeout_recovery_skip_reason": (
                        "Skipped timeout recovery because the codex normalization-only intent path had already used the smallest low-value rough-request prompt."
                        if rough_pion
                        else None
                    ),
                    "timeout_recovery_used": False,
                    "timeout_recovery_failed": not rough_pion,
                    "timeout_recovery_trigger_category": "timeout" if not rough_pion else None,
                    "timeout_recovery_timeout_seconds": 10.0 if not rough_pion else None,
                    "timeout_recovery_failure_category": "timeout" if not rough_pion else None,
                }
            else:
                backend_diagnostic = {
                    "status": "fallback",
                    "category": "configuration_missing",
                    "failure_origin": "local_configuration",
                    "recovery_mode": "configure_backend",
                    "retryable_now": True,
                }
                llm_assistance = {
                    "used": False,
                    "attempted": False,
                    "fallback": True,
                    "requested_backend": backend,
                    "selected_backend": "rules",
                    "selection_reason": f"Mocked {backend} backend fell back to rules.",
                    "fallback_reason": "mock fallback",
                    "fallback_category": "configuration_missing",
                    "codex_preflight_attempted": backend == "codex",
                    "codex_preflight_status": "failed" if backend == "codex" else None,
                    "codex_preflight_category": "timeout" if backend == "codex" else None,
                    "codex_preflight_reason": "mock timeout" if backend == "codex" else None,
                    "codex_preflight_soft_failed": backend == "codex",
                    "codex_preflight_soft_failure_reason": "mock timeout" if backend == "codex" else None,
                    "session_backend_memory_considered": backend == "api",
                    "session_backend_memory_used": False,
                    "session_backend_memory_reason": "mock session memory reason" if backend == "api" else None,
                    "session_backend_prior_category": "timeout" if backend == "api" else None,
                    "intent_primary_timeout_seconds": 12.0 if backend == "codex" else None,
                    "timeout_recovery_attempted": backend == "codex" and not rough_pion,
                    "timeout_recovery_skipped": backend == "codex" and rough_pion,
                    "timeout_recovery_skip_reason": (
                        "Skipped timeout recovery because the codex normalization-only intent path had already used the smallest low-value rough-request prompt."
                        if backend == "codex" and rough_pion
                        else None
                    ),
                    "timeout_recovery_used": False,
                    "timeout_recovery_failed": backend == "codex" and not rough_pion,
                    "timeout_recovery_trigger_category": "timeout" if backend == "codex" and not rough_pion else None,
                    "timeout_recovery_timeout_seconds": 10.0 if backend == "codex" and not rough_pion else None,
                    "timeout_recovery_failure_category": "timeout" if backend == "codex" and not rough_pion else None,
                }
            payload = {
                "status": "needs_input",
                "product_status": "needs_input",
                "physics": {
                    "inferred_interpretation": {"target_id": target_id},
                    "formula_proposals": [{"proposal_id": "proposal"}],
                },
                "generation_result": {"phase": "blocked_on_input"},
                "execution_result": {"phase": "blocked_by_generation"},
                "delivery_status": {
                    "generation": {"phase": "blocked_on_input"},
                    "execution": {"phase": "blocked_by_generation"},
                },
                "llm_assistance": llm_assistance,
                "backend_diagnostic": backend_diagnostic,
            }
            return Completed(stdout=json.dumps(payload))

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "data" / "backend_execution.json"
            with patch("scripts.validate_backend_execution.subprocess.run", side_effect=fake_run):
                exit_code = main(["--pyquda-repo", "/tmp/PyQUDA", "--output", str(report_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["all_coherent"])
            self.assertEqual(len(payload["backends"]), 3)
            self.assertTrue(all(item["coherent"] for item in payload["backends"]))
            self.assertEqual(payload["backend_summary"]["states"]["auto"], "fallback_only")
            self.assertEqual(payload["backend_summary"]["states"]["api"], "fallback_only")
            self.assertEqual(payload["backend_summary"]["states"]["codex"], "fallback_only")
            self.assertEqual(sorted(payload["backend_summary"]["fallback_only_backends"]), ["api", "auto", "codex"])
            self.assertFalse(payload["payload_policy"]["raw_payloads_included"])
            for backend_entry in payload["backends"]:
                self.assertEqual(backend_entry["availability_state"], "fallback_only")
                self.assertEqual(backend_entry["used_case_count"], 0)
                self.assertEqual(backend_entry["fallback_case_count"], 2)
                self.assertEqual(len(backend_entry["case_summaries"]), 2)
                for case in backend_entry["cases"]:
                    self.assertNotIn("stdout", case)
                    self.assertNotIn("stderr", case)
                    self.assertNotIn("parsed", case)
                    self.assertIn("case_summary", case)
                    self.assertEqual(case["product_status"], "needs_input")
                    self.assertEqual(case["generation_result"]["phase"], "blocked_on_input")
                    self.assertEqual(case["execution_result"]["phase"], "blocked_by_generation")
                    self.assertEqual(case["backend_path"]["backend_mode"], "fallback")
                    self.assertTrue(case["backend_path"]["backend_retryable_now"])
                    if backend_entry["backend"] == "auto":
                        self.assertEqual(case["backend_path"]["selected_backend"], "codex")
                        self.assertEqual(case["backend_path"]["fallback_category"], "timeout")
                        self.assertEqual(case["backend_path"]["backend_failure_origin"], "network")
                        self.assertEqual(case["backend_path"]["backend_recovery_mode"], "retry_or_switch_backend")
                        if case["case"] == "rough_pion":
                            self.assertFalse(case["backend_path"]["codex_preflight_attempted"])
                            self.assertTrue(case["backend_path"]["codex_preflight_skipped"])
                            self.assertEqual(case["backend_path"]["codex_preflight_status"], "skipped")
                            self.assertEqual(case["backend_path"]["intent_primary_timeout_seconds"], 10.0)
                            self.assertTrue(case["backend_path"]["timeout_recovery_skipped"])
                            self.assertFalse(case["backend_path"]["timeout_recovery_attempted"])
                        else:
                            self.assertTrue(case["backend_path"]["codex_preflight_attempted"])
                            self.assertFalse(case["backend_path"]["codex_preflight_skipped"])
                            self.assertTrue(case["backend_path"]["codex_preflight_soft_failed"])
                            self.assertEqual(case["backend_path"]["intent_primary_timeout_seconds"], 12.0)
                            self.assertTrue(case["backend_path"]["timeout_recovery_attempted"])
                            self.assertEqual(case["backend_path"]["timeout_recovery_timeout_seconds"], 10.0)
                        self.assertEqual(case["case_summary"]["backend_failure_origin"], "network")
                        self.assertEqual(case["case_summary"]["backend_recovery_mode"], "retry_or_switch_backend")
                    elif backend_entry["backend"] == "codex":
                        self.assertEqual(case["backend_path"]["selected_backend"], "rules")
                        self.assertEqual(case["backend_path"]["fallback_category"], "configuration_missing")
                        self.assertEqual(case["backend_path"]["backend_failure_origin"], "local_configuration")
                        self.assertEqual(case["backend_path"]["backend_recovery_mode"], "configure_backend")
                        self.assertTrue(case["backend_path"]["codex_preflight_attempted"])
                        self.assertTrue(case["backend_path"]["codex_preflight_soft_failed"])
                        self.assertEqual(case["backend_path"]["codex_preflight_soft_failure_reason"], "mock timeout")
                        self.assertEqual(case["backend_path"]["intent_primary_timeout_seconds"], 12.0)
                        if case["case"] == "rough_pion":
                            self.assertFalse(case["backend_path"]["timeout_recovery_attempted"])
                            self.assertTrue(case["backend_path"]["timeout_recovery_skipped"])
                        else:
                            self.assertTrue(case["backend_path"]["timeout_recovery_attempted"])
                            self.assertEqual(case["backend_path"]["timeout_recovery_timeout_seconds"], 10.0)
                        self.assertEqual(case["case_summary"]["codex_preflight_status"], "failed")
                        if case["case"] == "rough_pion":
                            self.assertFalse(case["case_summary"]["timeout_recovery_failed"])
                            self.assertTrue(case["case_summary"]["timeout_recovery_skipped"])
                        else:
                            self.assertTrue(case["case_summary"]["timeout_recovery_failed"])
                    else:
                        self.assertEqual(case["backend_path"]["selected_backend"], "rules")
                        self.assertEqual(case["backend_path"]["fallback_category"], "configuration_missing")
                        self.assertEqual(case["backend_path"]["backend_failure_origin"], "local_configuration")
                        self.assertEqual(case["backend_path"]["backend_recovery_mode"], "configure_backend")
                        self.assertFalse(case["backend_path"]["codex_preflight_attempted"])
                        self.assertFalse(case["backend_path"]["codex_preflight_soft_failed"])
                        self.assertTrue(case["backend_path"]["session_backend_memory_considered"])
                        self.assertFalse(case["backend_path"]["session_backend_memory_used"])
                        self.assertEqual(case["backend_path"]["session_backend_prior_category"], "timeout")
                        self.assertEqual(case["case_summary"]["session_backend_memory_reason"], "mock session memory reason")
                    self.assertEqual(case["case_summary"]["product_status"], "needs_input")
                    self.assertEqual(case["case_summary"]["generation_phase"], "blocked_on_input")
                    self.assertEqual(case["case_summary"]["execution_phase"], "blocked_by_generation")
                    self.assertTrue(case["case_summary"]["backend_retryable_now"])
                    self.assertEqual(case["case_summary"]["runtime_category"], None)
            self.assertIn("repair_contract", backend_entry)
            if backend_entry["availability_state"] == "fallback_only":
                self.assertIsNotNone(backend_entry["repair_contract"])
                self.assertIn("recommended_fix", backend_entry["repair_contract"])
                self.assertIn("verification_command", backend_entry["repair_contract"])
            self.assertEqual(payload["backend_summary"]["failure_origin_counts"]["local_configuration"], 4)
            self.assertEqual(payload["backend_summary"]["failure_origin_counts"]["network"], 2)
            self.assertEqual(payload["backend_summary"]["recovery_mode_counts"]["configure_backend"], 4)
            self.assertEqual(payload["backend_summary"]["recovery_mode_counts"]["retry_or_switch_backend"], 2)

    def test_main_keeps_raw_payloads_when_requested(self):
        class Completed:
            def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
                self.stdout = stdout
                self.returncode = returncode
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None, timeout=None):
            output_path = Path(cmd[cmd.index("--output") + 1])
            output_path.with_suffix(".physics.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".task.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".plan.json").write_text(json.dumps({}), encoding="utf-8")
            request = cmd[4]
            rough_pion = "pi meson two-point" in request
            backend = cmd[cmd.index("--backend") + 1]
            target_id = "meson_two_point_correlator_unspecified" if "meson correlator" in request else "pion_two_point_correlator"
            if backend == "auto":
                llm_assistance = {
                    "used": False,
                    "attempted": True,
                    "fallback": True,
                    "requested_backend": "auto",
                    "selected_backend": "codex",
                    "selection_reason": "mock auto fallback for test",
                    "fallback_reason": "mock auto fallback",
                    "fallback_category": "timeout",
                    "codex_preflight_attempted": not rough_pion,
                    "codex_preflight_status": "skipped" if rough_pion else "failed",
                    "codex_preflight_category": None if rough_pion else "timeout",
                    "codex_preflight_reason": None if rough_pion else "mock timeout",
                    "codex_preflight_skipped": rough_pion,
                    "codex_preflight_skip_reason": "mock auto skip reason" if rough_pion else None,
                    "codex_preflight_soft_failed": not rough_pion,
                    "codex_preflight_soft_failure_reason": "mock timeout" if not rough_pion else None,
                    "session_backend_memory_considered": False,
                    "session_backend_memory_used": False,
                    "session_backend_memory_reason": None,
                    "session_backend_prior_category": None,
                    "intent_primary_timeout_seconds": 10.0 if rough_pion else 12.0,
                    "timeout_recovery_attempted": not rough_pion,
                    "timeout_recovery_skipped": rough_pion,
                    "timeout_recovery_skip_reason": (
                        "Skipped timeout recovery because the codex normalization-only intent path had already used the smallest low-value rough-request prompt."
                        if rough_pion
                        else None
                    ),
                    "timeout_recovery_used": False,
                    "timeout_recovery_failed": not rough_pion,
                    "timeout_recovery_trigger_category": "timeout" if not rough_pion else None,
                    "timeout_recovery_timeout_seconds": 10.0 if not rough_pion else None,
                    "timeout_recovery_failure_category": "timeout" if not rough_pion else None,
                }
                backend_diagnostic = {
                    "status": "fallback",
                    "category": "timeout",
                    "failure_origin": "network",
                    "recovery_mode": "retry_or_switch_backend",
                    "retryable_now": True,
                }
            else:
                llm_assistance = {
                    "used": False,
                    "attempted": True,
                    "fallback": True,
                    "requested_backend": backend,
                    "selected_backend": "rules",
                    "selection_reason": "fallback for test",
                    "fallback_reason": "mock fallback",
                    "fallback_category": "configuration_missing",
                    "codex_preflight_attempted": backend == "codex",
                    "codex_preflight_status": "failed" if backend == "codex" else None,
                    "codex_preflight_category": "timeout" if backend == "codex" else None,
                    "codex_preflight_reason": "mock timeout" if backend == "codex" else None,
                    "codex_preflight_soft_failed": backend == "codex",
                    "codex_preflight_soft_failure_reason": "mock timeout" if backend == "codex" else None,
                    "session_backend_memory_considered": backend == "api",
                    "session_backend_memory_used": False,
                    "session_backend_memory_reason": "mock session memory reason" if backend == "api" else None,
                    "session_backend_prior_category": "timeout" if backend == "api" else None,
                    "intent_primary_timeout_seconds": 12.0 if backend == "codex" else None,
                    "timeout_recovery_attempted": backend == "codex" and not rough_pion,
                    "timeout_recovery_skipped": backend == "codex" and rough_pion,
                    "timeout_recovery_skip_reason": (
                        "Skipped timeout recovery because the codex normalization-only intent path had already used the smallest low-value rough-request prompt."
                        if backend == "codex" and rough_pion
                        else None
                    ),
                    "timeout_recovery_used": False,
                    "timeout_recovery_failed": backend == "codex" and not rough_pion,
                    "timeout_recovery_trigger_category": "timeout" if backend == "codex" and not rough_pion else None,
                    "timeout_recovery_timeout_seconds": 10.0 if backend == "codex" and not rough_pion else None,
                    "timeout_recovery_failure_category": "timeout" if backend == "codex" and not rough_pion else None,
                }
                backend_diagnostic = {
                    "status": "fallback",
                    "category": "configuration_missing",
                    "failure_origin": "local_configuration",
                    "recovery_mode": "configure_backend",
                    "retryable_now": True,
                }
            payload = {
                "status": "needs_input",
                "product_status": "needs_input",
                "physics": {
                    "inferred_interpretation": {"target_id": target_id},
                    "formula_proposals": [{"proposal_id": "proposal"}],
                },
                "generation_result": {"phase": "blocked_on_input"},
                "execution_result": {"phase": "blocked_by_generation"},
                "delivery_status": {
                    "generation": {"phase": "blocked_on_input"},
                    "execution": {"phase": "blocked_by_generation"},
                },
                "llm_assistance": llm_assistance,
                "runtime_diagnostic": {
                    "status": "probe_available",
                    "category": "probe_available",
                },
                "backend_diagnostic": backend_diagnostic,
            }
            return Completed(stdout=json.dumps(payload), stderr="mock-stderr")

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "data" / "backend_execution.json"
            with patch("scripts.validate_backend_execution.subprocess.run", side_effect=fake_run):
                exit_code = main(
                    [
                        "--pyquda-repo",
                        "/tmp/PyQUDA",
                        "--output",
                        str(report_path),
                        "--include-raw-payloads",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["payload_policy"]["raw_payloads_included"])
            for backend_entry in payload["backends"]:
                for case in backend_entry["cases"]:
                    self.assertIn("stdout", case)
                    self.assertIn("stderr", case)
                    self.assertIn("parsed", case)
                    self.assertEqual(case["case_summary"]["product_status"], "needs_input")
                    self.assertEqual(case["case_summary"]["generation_phase"], "blocked_on_input")
                    self.assertEqual(case["case_summary"]["execution_phase"], "blocked_by_generation")
                    self.assertEqual(case["case_summary"]["runtime_category"], "probe_available")
                    if backend_entry["backend"] == "auto":
                        self.assertEqual(case["case_summary"]["backend_failure_origin"], "network")
                        if case["case"] == "rough_pion":
                            self.assertTrue(case["case_summary"]["codex_preflight_skipped"])
                            self.assertEqual(case["case_summary"]["intent_primary_timeout_seconds"], 10.0)
                            self.assertTrue(case["case_summary"]["timeout_recovery_skipped"])
                        else:
                            self.assertTrue(case["case_summary"]["codex_preflight_soft_failed"])
                            self.assertEqual(case["case_summary"]["timeout_recovery_timeout_seconds"], 10.0)
                    elif backend_entry["backend"] == "codex":
                        self.assertEqual(case["case_summary"]["backend_failure_origin"], "local_configuration")
                        self.assertTrue(case["case_summary"]["codex_preflight_soft_failed"])
                        self.assertEqual(case["case_summary"]["codex_preflight_soft_failure_reason"], "mock timeout")
                        self.assertEqual(case["case_summary"]["intent_primary_timeout_seconds"], 12.0)
                        if case["case"] == "rough_pion":
                            self.assertTrue(case["case_summary"]["timeout_recovery_skipped"])
                        else:
                            self.assertEqual(case["case_summary"]["timeout_recovery_timeout_seconds"], 10.0)
                    else:
                        self.assertEqual(case["case_summary"]["backend_failure_origin"], "local_configuration")
                        self.assertTrue(case["case_summary"]["session_backend_memory_considered"])
                        self.assertFalse(case["case_summary"]["session_backend_memory_used"])
                        self.assertEqual(case["case_summary"]["session_backend_prior_category"], "timeout")

    def test_main_records_case_timeout_as_validator_timeout(self):
        class Completed:
            def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
                self.stdout = stdout
                self.returncode = returncode
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None, env=None, timeout=None):
            output_path = Path(cmd[cmd.index("--output") + 1])
            backend = cmd[cmd.index("--backend") + 1]
            request = cmd[4]
            if backend == "codex" and "pi meson two-point" in request:
                raise subprocess.TimeoutExpired(
                    cmd=cmd,
                    timeout=timeout,
                    output='{"status":"partial"}',
                    stderr="validator case timeout",
                )
            output_path.with_suffix(".physics.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".task.json").write_text(json.dumps({}), encoding="utf-8")
            output_path.with_suffix(".plan.json").write_text(json.dumps({}), encoding="utf-8")
            target_id = "meson_two_point_correlator_unspecified" if "meson correlator" in request else "pion_two_point_correlator"
            payload = {
                "status": "needs_input",
                "product_status": "needs_input",
                "physics": {
                    "inferred_interpretation": {"target_id": target_id},
                    "formula_proposals": [{"proposal_id": "proposal"}],
                },
                "generation_result": {"phase": "blocked_on_input"},
                "execution_result": {"phase": "blocked_by_generation"},
                "delivery_status": {
                    "generation": {"phase": "blocked_on_input"},
                    "execution": {"phase": "blocked_by_generation"},
                },
                "llm_assistance": {
                    "used": True,
                    "attempted": True,
                    "fallback": False,
                    "requested_backend": backend,
                    "selected_backend": backend,
                    "selection_reason": "mock used",
                },
                "backend_diagnostic": {
                    "status": "used",
                    "category": None,
                    "failure_origin": None,
                    "recovery_mode": "continue",
                    "retryable_now": True,
                },
            }
            return Completed(stdout=json.dumps(payload))

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = Path(tmpdir) / "data" / "backend_execution.json"
            with patch("scripts.validate_backend_execution.subprocess.run", side_effect=fake_run):
                exit_code = main(
                    [
                        "--pyquda-repo",
                        "/tmp/PyQUDA",
                        "--output",
                        str(report_path),
                        "--case-timeout",
                        "7",
                    ]
                )

            self.assertEqual(exit_code, 1)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["case_timeout"], 7.0)
            codex_entry = next(item for item in payload["backends"] if item["backend"] == "codex")
            self.assertEqual(codex_entry["availability_state"], "incoherent")
            self.assertFalse(codex_entry["coherent"])
            timeout_case = next(case for case in codex_entry["cases"] if case["case"] == "rough_pion")
            self.assertEqual(timeout_case["status"], "validator_timeout")
            self.assertEqual(timeout_case["product_status"], "validator_timeout")
            self.assertEqual(timeout_case["backend_diagnostic"]["status"], "validator_timeout")
            self.assertEqual(timeout_case["backend_diagnostic"]["detail_category"], "validator_case_timeout")
            self.assertEqual(timeout_case["backend_diagnostic"]["failure_origin"], "local_validator")
            self.assertEqual(
                timeout_case["backend_diagnostic"]["recovery_mode"],
                "increase_validator_timeout_or_run_case_directly",
            )
            self.assertEqual(timeout_case["backend_path"]["backend_mode"], "attempted_without_result")
            self.assertEqual(timeout_case["backend_path"]["requested_backend"], "codex")
            self.assertEqual(timeout_case["backend_path"]["selected_backend"], "codex")
            self.assertEqual(timeout_case["case_timeout_seconds"], 7.0)
            self.assertEqual(timeout_case["case_summary"]["backend_category"], "timeout")
            self.assertEqual(timeout_case["case_summary"]["product_status"], "validator_timeout")
            self.assertEqual(timeout_case["case_summary"]["generation_phase"], "validator_timeout")
            self.assertEqual(timeout_case["case_summary"]["execution_phase"], "blocked_by_validator")
            self.assertIsNotNone(codex_entry["repair_contract"])
            self.assertEqual(codex_entry["repair_contract"]["detail_category"], "validator_case_timeout")
            verification_command = codex_entry["repair_contract"]["verification_command"]
            self.assertIn("scripts/validate_backend_execution.py", verification_command)
            self.assertIn("--pyquda-repo", verification_command)
            self.assertIn("--case-timeout 17", verification_command)


if __name__ == "__main__":
    unittest.main()
