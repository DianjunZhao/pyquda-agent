import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pyquda_agent.backends.base import BackendInvocationError
from pyquda_agent.app import run_command
from pyquda_agent.backends.factory import AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS
from pyquda_agent.backends.factory import EXPLICIT_CODEX_PREFLIGHT_TIMEOUT_SECONDS
from pyquda_agent.cli import main
from pyquda_agent.config import RunConfig
from pyquda_agent.intent.interpreter import interpret_request
from pyquda_agent.intent.resolver import INTENT_CODEX_NORMALIZATION_PRIMARY_TIMEOUT_SECONDS
from pyquda_agent.intent.resolver import INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS
from pyquda_agent.intent.resolver import INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS
from pyquda_agent.sessions.state import SessionState
from pyquda_agent.sessions.state import save_session
from pyquda_agent.tasks.parser import parse_task_description


class _InvokingBackend:
    name = "fake-llm"

    def __init__(self, response: str):
        self.response = response
        self.calls = 0
        self.last_system_prompt = None
        self.last_user_prompt = None

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response


class _SequenceBackend:
    name = "codex"

    def __init__(self, responses, *, timeout_seconds: float = 30.0):
        self.responses = list(responses)
        self.calls = 0
        self.timeout_seconds = timeout_seconds
        self.seen_timeouts = []

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        self.seen_timeouts.append(self.timeout_seconds)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class _FailingBackend:
    def __init__(self, message: str, category: str, *, name: str = "failing-llm", timeout_seconds: float | None = None):
        self.name = name
        self.message = message
        self.category = category
        self.timeout_seconds = timeout_seconds

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        raise BackendInvocationError(self.message, category=self.category)


class CliRunTests(unittest.TestCase):
    def _fallback_backend_patch(self):
        return patch(
            "pyquda_agent.app.build_llm_backend",
            return_value=(
                None,
                {
                    "requested_backend": "codex",
                    "configured": False,
                    "backend_name": None,
                    "fallback": True,
                    "fallback_reason": "mocked test fallback",
                },
            ),
        )

    def _prepare_repo_fixture(self, root: Path) -> tuple[Path, Path, Path]:
        pyquda = root / "PyQUDA"
        output = root / "outputs" / "run_pion.py"
        index_path = root / "data" / "pyquda_index.json"

        (root / "data").mkdir(parents=True)
        (root / "docs").mkdir(parents=True)
        (pyquda / "examples").mkdir(parents=True)
        (pyquda / "tests").mkdir(parents=True)
        (pyquda / "pyquda_utils").mkdir(parents=True)
        (pyquda / "pyquda_utils" / "io").mkdir(parents=True)

        (root / "docs" / "RUNNABLE_PION_2PT_SPEC.md").write_text("pion helper", encoding="utf-8")
        (root / "docs" / "RUNNABLE_QUARK_PROPAGATOR_SPEC.md").write_text("quark helper", encoding="utf-8")
        (root / "docs" / "RUNNABLE_MESON_SPEC_SPEC.md").write_text("meson spec helper", encoding="utf-8")
        (root / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
        (root / "docs" / "RUN_WORKFLOW.md").write_text("workflow", encoding="utf-8")

        (pyquda / "examples" / "2_Quark_Propagator.py").write_text("quark example", encoding="utf-8")
        (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion example", encoding="utf-8")
        (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion", encoding="utf-8")
        (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec", encoding="utf-8")
        (pyquda / "tests" / "test_io.py").write_text("io test", encoding="utf-8")
        (pyquda / "pyquda_utils" / "source.py").write_text("wall source", encoding="utf-8")
        (pyquda / "pyquda_utils" / "core.py").write_text("invert core", encoding="utf-8")
        (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma", encoding="utf-8")
        (pyquda / "pyquda_utils" / "phase.py").write_text("phase", encoding="utf-8")
        (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")

        index_path.write_text(
            json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 3}}),
            encoding="utf-8",
        )
        return pyquda, output, index_path

    def test_cli_run_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(payload["product_status"], "ready_to_generate")
            self.assertEqual(payload["pipeline"][0], "physics_interpretation")
            self.assertEqual(payload["llm_assistance"]["requested_backend"], "codex")
            self.assertEqual(payload["result_summary"]["status"], "dry_run")
            self.assertEqual(payload["result_summary"]["schema_family"], "pyquda_agent.result_summary")
            self.assertEqual(payload["result_summary"]["schema_version"], "2026-07-v1")
            self.assertEqual(payload["result_summary"]["product_status"], "ready_to_generate")
            self.assertEqual(payload["result_summary"]["workflow_lifecycle"]["stage"], "ready_to_generate")
            self.assertEqual(payload["result_summary"]["physics_target"], "pion_two_point_correlator")
            self.assertEqual(payload["result_summary"]["workflow_target"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertEqual(payload["result_summary"]["artifacts"]["task"], payload["task_artifact"])
            self.assertEqual(payload["result_summary"]["artifacts"]["session"], payload["session_artifact"])
            self.assertEqual(payload["workflow_outcome"]["phase"], "ready_to_generate")
            self.assertEqual(payload["workflow_outcome"]["generation_status"], "dry_run")
            self.assertFalse(payload["workflow_outcome"]["generation_succeeded"])
            self.assertFalse(payload["workflow_outcome"]["execution_attempted"])
            self.assertEqual(payload["workflow_outcome"]["runtime_probe_status"], "not_applicable")
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "ready_to_generate")
            self.assertFalse(payload["delivery_status"]["generation"]["succeeded"])
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["workflow_lifecycle"]["stage"], "ready_to_generate")
            self.assertEqual(payload["workflow_lifecycle"]["generation"]["phase"], "ready_to_generate")
            self.assertEqual(payload["workflow_lifecycle"]["runtime"]["phase"], "blocked_by_generation")
            self.assertEqual(payload["capability_summary"]["backend"]["state"], "fallback")
            self.assertFalse(payload["capability_summary"]["backend"]["ready"])
            self.assertEqual(payload["capability_summary"]["generation"]["state"], "ready_to_generate")
            self.assertTrue(payload["capability_summary"]["generation"]["ready"])
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "blocked_by_generation")
            self.assertFalse(payload["capability_summary"]["runtime"]["proved"])
            self.assertEqual(payload["capability_summary"]["next_step"]["kind"], "generate_script")
            self.assertIn("re-run without --dry-run", payload["terminal_message"]["headline"].lower())
            self.assertEqual(payload["terminal_message"]["recommended_command"], payload["primary_action"]["command"])
            self.assertNotIn("--dry-run", payload["workflow_outcome"]["recommended_command"])
            self.assertEqual(payload["result_summary"]["review_order"][0], "physics")
            self.assertIn("--resume-session", payload["resume_hint"])
            self.assertIn("--dry-run", payload["resume_hint"])
            self.assertEqual(payload["action_queue"][0]["kind"], "generate_script")
            self.assertNotIn("--dry-run", payload["action_queue"][0]["command"])
            self.assertEqual(payload["primary_action"]["kind"], "generate_script")
            self.assertNotIn("--dry-run", payload["primary_action"]["command"])
            self.assertEqual(payload["task"]["script_output_path"], str(output.resolve()))
            self.assertEqual(payload["task"]["correlator_output_format"], "npy")
            self.assertEqual(payload["task"]["cluster_launch"], "local")
            self.assertTrue(payload["llm_assistance"]["fallback"])
            self.assertTrue(payload["task_artifact"].endswith(".task.json"))
            self.assertTrue(payload["physics_artifact"].endswith(".physics.json"))
            self.assertTrue(payload["plan_artifact"].endswith(".plan.json"))
            self.assertTrue(payload["session_artifact"].endswith(".session.json"))
            self.assertTrue(Path(payload["task_artifact"]).exists())
            self.assertTrue(Path(payload["physics_artifact"]).exists())
            self.assertTrue(Path(payload["plan_artifact"]).exists())
            self.assertTrue(Path(payload["session_artifact"]).exists())
            self.assertEqual(payload["context"]["index_summary"]["file_count"], 3)
            self.assertEqual(payload["context"]["index_provenance"]["status"], "matched")
            self.assertEqual(payload["result_summary"]["index_provenance"]["status"], "matched")
            self.assertTrue(any(ref["path"].endswith("pyquda_utils/io/__init__.py") for ref in payload["implementation_plan"]["references"]))
            self.assertTrue(payload["implementation_plan"]["external_citations"])
            self.assertTrue(payload["implementation_plan"]["convention_decisions"])
            self.assertTrue(any(item["category"] == "physics" for item in payload["implementation_plan"]["convention_decisions"]))
            self.assertIn("runtime_readiness", payload["implementation_plan"])
            self.assertFalse(payload["implementation_plan"]["runtime_readiness"]["ready"])
            self.assertEqual(
                payload["implementation_plan"]["runtime_readiness"]["evidence_levels"]["current_level"],
                "structurally_grounded",
            )
            self.assertEqual(payload["runtime_evidence"]["generated_script_probe"]["status"], "not_run")
            self.assertTrue(payload["runtime_evidence"]["generated_script_probe"]["command"].startswith("python3 scripts/probe_generated_workflow.py"))
            self.assertFalse(payload["runtime_evidence"]["generated_script_exists"])
            self.assertTrue(any("arxiv.org" in citation["url"] for citation in payload["implementation_plan"]["external_citations"]))
            task_artifact = json.loads(Path(payload["task_artifact"]).read_text(encoding="utf-8"))
            physics_artifact = json.loads(Path(payload["physics_artifact"]).read_text(encoding="utf-8"))
            plan_artifact = json.loads(Path(payload["plan_artifact"]).read_text(encoding="utf-8"))
            self.assertEqual(task_artifact["workflow_id"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertEqual(physics_artifact["confirmed_interpretation"]["target_id"], "pion_two_point_correlator")
            self.assertEqual(plan_artifact["workflow_id"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertIn("runtime_readiness", plan_artifact)
            self.assertIn("_resolution_buckets", plan_artifact["field_resolution"])

    def test_cli_run_auto_backend_records_selected_backend(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            backend = _InvokingBackend(
                """
                {
                  "normalized_request": "Compute the pion two-point correlator.",
                  "physics_status": "needs_confirmation",
                  "candidate_targets": [
                    {
                      "target_id": "pion_two_point_correlator",
                      "label": "pion two-point correlator",
                      "summary": "Likely pion two-point target.",
                      "confidence": "medium",
                      "status": "inferred",
                      "task_type_hint": "pion_2pt"
                    }
                  ]
                }
                """
            )
            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        backend,
                        {
                            "requested_backend": "auto",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["llm_assistance"]["requested_backend"], "auto")
            self.assertEqual(payload["llm_assistance"]["selected_backend"], "codex")
            self.assertEqual(payload["result_summary"]["selected_backend"], "codex")
            self.assertFalse(payload["result_summary"]["llm_fallback"])
            self.assertIsNone(payload["result_summary"]["llm_fallback_reason"])
            self.assertEqual(payload["capability_summary"]["backend"]["state"], "used")
            self.assertTrue(payload["capability_summary"]["backend"]["ready"])

    def test_cli_run_auto_backend_passes_normalization_hint_for_rough_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            captured_kwargs: dict = {}

            def fake_build_llm_backend(*args, **kwargs):
                captured_kwargs.update(kwargs)
                return (
                    None,
                    {
                        "requested_backend": "auto",
                        "selected_backend": "rules",
                        "configured": False,
                        "backend_name": None,
                        "fallback": True,
                        "fallback_reason": "mock fallback for hint capture",
                    },
                )

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("pyquda_agent.app.build_llm_backend", side_effect=fake_build_llm_backend):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["llm_assistance"]["requested_backend"], "auto")
            request_profile_hint = captured_kwargs.get("request_profile_hint")
            self.assertIsInstance(request_profile_hint, dict)
            self.assertEqual(request_profile_hint.get("intent_strategy_hint"), "normalization_only")
            self.assertEqual(request_profile_hint.get("auto_codex_preflight_policy"), "skip")
            self.assertIn("rough normalization-only path", request_profile_hint.get("auto_codex_preflight_skip_reason", ""))

    def test_cli_run_passes_backend_skip_hint_for_explicit_direct_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            captured_kwargs: dict = {}

            def fake_build_llm_backend(*args, **kwargs):
                captured_kwargs.update(kwargs)
                return (
                    None,
                    {
                        "requested_backend": "auto",
                        "selected_backend": "rules",
                        "configured": False,
                        "backend_name": None,
                        "fallback": False,
                        "fallback_reason": None,
                        "selection_reason": "mock explicit direct request skip",
                    },
                )

            stdout = io.StringIO()
            argv = [
                "run",
                (
                    "please compute the pion two-point correlator from gauge "
                    f"{pyquda / 'tests' / 'weak_field.lime'} lattice size 4 4 4 8 grid 1 1 1 1 "
                    "mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 coeff_r=2.32582045 "
                    "tol=1e-12 maxiter=1000 gauge fixed source timeslice 0 outputs/pion.npy outputs/pion.py "
                    "resource_path=.cache/quda cluster_launch=local"
                ),
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("pyquda_agent.app.build_llm_backend", side_effect=fake_build_llm_backend):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["llm_assistance"]["selected_backend"], "rules")
            request_profile_hint = captured_kwargs.get("request_profile_hint")
            self.assertIsInstance(request_profile_hint, dict)
            self.assertEqual(request_profile_hint.get("backend_policy"), "skip")
            self.assertIn("confirmed physics target", request_profile_hint.get("backend_skip_reason", ""))

    def test_cli_run_records_soft_codex_preflight_timeout_when_llm_still_succeeds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            backend = _InvokingBackend(
                """
                {
                  "normalized_request": "Compute the pion two-point correlator.",
                  "physics_status": "needs_confirmation",
                  "candidate_targets": [
                    {
                      "target_id": "pion_two_point_correlator",
                      "label": "pion two-point correlator",
                      "summary": "Likely pion two-point target.",
                      "confidence": "medium",
                      "status": "inferred",
                      "task_type_hint": "pion_2pt"
                    }
                  ]
                }
                """
            )
            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        backend,
                        {
                            "requested_backend": "auto",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                            "selection_reason": "Auto mode kept the local codex backend after a short preflight timeout because no configured API backend was available; the real codex call will decide whether fallback is still necessary.",
                            "codex_preflight_attempted": True,
                            "codex_preflight_timeout_seconds": AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS,
                            "codex_preflight_status": "failed",
                            "codex_preflight_category": "timeout",
                            "codex_preflight_reason": f"Codex auto-preflight timed out after {AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS:g} seconds.",
                            "codex_preflight_soft_failed": True,
                            "codex_preflight_soft_failure_reason": f"Codex auto-preflight timed out after {AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS:g} seconds.",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["llm_used"])
            self.assertFalse(payload["llm_fallback"])
            self.assertTrue(payload["llm_codex_preflight_soft_failed"])
            self.assertEqual(
                payload["llm_codex_preflight_soft_failure_reason"],
                f"Codex auto-preflight timed out after {AUTO_CODEX_PREFLIGHT_TIMEOUT_SECONDS:g} seconds.",
            )
            self.assertTrue(payload["backend_diagnostic"]["codex_preflight_soft_failed"])
            self.assertIn("preflight timeout", payload["backend_diagnostic"]["message"].lower())

    def test_cli_run_resume_session_uses_backend_memory_to_skip_degraded_codex_in_auto_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "outputs" / "saved.session.json"
            saved_draft = parse_task_description("please compute pion 2pt outputs/run.py")
            saved_physics = interpret_request("please compute the pion two-point correlator")
            save_session(
                session_path,
                SessionState(
                    task_description="old request",
                    draft=saved_draft,
                    asked_questions=[],
                    physics_target=saved_physics,
                    backend_assistance={
                        "selected_backend": "codex",
                        "fallback": True,
                        "fallback_category": "timeout",
                        "fallback_reason": "Initial LLM attempt timed out and recovery also timed out.",
                    },
                    confirmed_fields={"source_timeslices": [0]},
                ),
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--backend",
                "auto",
                "--model",
                "openai/gpt-5-mini",
                "--resume-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            response_text = """
                {
                  "normalized_request": "Compute the pion two-point correlator.",
                  "physics_status": "needs_confirmation",
                  "candidate_targets": [
                    {
                      "target_id": "pion_two_point_correlator",
                      "label": "pion two-point correlator",
                      "summary": "Likely pion two-point target.",
                      "confidence": "medium",
                      "status": "inferred",
                      "task_type_hint": "pion_2pt"
                    }
                  ],
                  "notes": ["session backend memory path used in cli test"]
                }
            """
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                    with patch(
                        "pyquda_agent.backends.codex.CodexBackend.preflight",
                        side_effect=AssertionError("codex preflight should be skipped"),
                    ):
                        with patch("pyquda_agent.backends.api.OpenAICompatibleBackend.generate_text", return_value=response_text):
                            with redirect_stdout(stdout):
                                exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["llm_assistance"]["requested_backend"], "auto")
            self.assertEqual(payload["llm_assistance"]["selected_backend"], "api")
            self.assertTrue(payload["llm_assistance"]["used"])
            self.assertFalse(payload["llm_assistance"]["fallback"])
            self.assertTrue(payload["llm_assistance"]["session_backend_memory_considered"])
            self.assertTrue(payload["llm_assistance"]["session_backend_memory_used"])
            self.assertEqual(payload["llm_assistance"]["session_backend_prior_category"], "timeout")
            self.assertIn("resumed session", payload["llm_assistance"]["selection_reason"])
            self.assertTrue(payload["result_summary"]["llm_session_backend_memory_considered"])
            self.assertTrue(payload["result_summary"]["llm_session_backend_memory_used"])
            self.assertEqual(payload["result_summary"]["llm_session_backend_prior_category"], "timeout")
            self.assertTrue(payload["backend_diagnostic"]["session_backend_memory_considered"])
            self.assertTrue(payload["backend_diagnostic"]["session_backend_memory_used"])
            self.assertEqual(payload["backend_diagnostic"]["selected_backend"], "api")
            self.assertIn("resumed session", payload["backend_diagnostic"]["message"].lower())

    def test_cli_run_resume_session_uses_backend_memory_after_explicit_codex_failed_to_rules(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "outputs" / "saved.session.json"
            saved_draft = parse_task_description("please compute pion 2pt outputs/run.py")
            saved_physics = interpret_request("please compute the pion two-point correlator")
            save_session(
                session_path,
                SessionState(
                    task_description="old request",
                    draft=saved_draft,
                    asked_questions=[],
                    physics_target=saved_physics,
                    backend_assistance={
                        "requested_backend": "codex",
                        "selected_backend": "rules",
                        "fallback": True,
                        "fallback_category": "authentication_error",
                        "fallback_reason": "Explicit codex backend failed preflight because local authentication was unavailable.",
                    },
                    confirmed_fields={"source_timeslices": [0]},
                ),
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--backend",
                "auto",
                "--model",
                "openai/gpt-5-mini",
                "--resume-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            response_text = """
                {
                  "normalized_request": "Compute the pion two-point correlator.",
                  "physics_status": "needs_confirmation",
                  "candidate_targets": [
                    {
                      "target_id": "pion_two_point_correlator",
                      "label": "pion two-point correlator",
                      "summary": "Likely pion two-point target.",
                      "confidence": "medium",
                      "status": "inferred",
                      "task_type_hint": "pion_2pt"
                    }
                  ],
                  "notes": ["explicit-codex failure backend memory path used in cli test"]
                }
            """
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("pyquda_agent.backends.factory.resolve_api_key", return_value="secret"):
                    with patch(
                        "pyquda_agent.backends.codex.CodexBackend.preflight",
                        side_effect=AssertionError("codex preflight should be skipped"),
                    ):
                        with patch("pyquda_agent.backends.api.OpenAICompatibleBackend.generate_text", return_value=response_text):
                            with redirect_stdout(stdout):
                                exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["llm_assistance"]["requested_backend"], "auto")
            self.assertEqual(payload["llm_assistance"]["selected_backend"], "api")
            self.assertTrue(payload["llm_assistance"]["used"])
            self.assertFalse(payload["llm_assistance"]["fallback"])
            self.assertTrue(payload["llm_assistance"]["session_backend_memory_considered"])
            self.assertTrue(payload["llm_assistance"]["session_backend_memory_used"])
            self.assertEqual(payload["llm_assistance"]["session_backend_prior_category"], "authentication_error")
            self.assertEqual(payload["llm_assistance"]["session_backend_prior_selected_backend"], "rules")
            self.assertIn("codex-targeting attempt", payload["llm_assistance"]["selection_reason"])
            self.assertTrue(payload["backend_diagnostic"]["session_backend_memory_considered"])
            self.assertTrue(payload["backend_diagnostic"]["session_backend_memory_used"])
            self.assertEqual(payload["backend_diagnostic"]["selected_backend"], "api")
            self.assertIn("codex-targeting attempt", payload["backend_diagnostic"]["message"])

    def test_cli_run_can_print_summary_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["schema_family"], "pyquda_agent.result_summary")
            self.assertEqual(payload["schema_version"], "2026-07-v1")
            self.assertEqual(payload["product_status"], "needs_input")
            self.assertEqual(payload["physics_target"], "pion_two_point_correlator")
            self.assertEqual(payload["workflow_outcome"]["phase"], "clarification")
            self.assertEqual(payload["workflow_outcome"]["generation_status"], "blocked_on_input")
            self.assertFalse(payload["workflow_outcome"]["generation_succeeded"])
            self.assertTrue(payload["workflow_outcome"]["blockers"])
            self.assertEqual(payload["workflow_outcome"]["blockers"][0], "source_timeslices")
            self.assertEqual(
                payload["workflow_outcome"]["clarification_gap_summary"]["sentence"],
                "Current missing conditions by scope: Physics: source_timeslices, gauge_fixed; Implementation: mass, xi_0, nu, coeff_t, coeff_r, solver_tol, solver_maxiter. Additional fields remain after this batch.",
            )
            self.assertEqual(
                payload["clarification_batch_card"]["current_batch_fields"],
                ["source_timeslices", "gauge_fixed", "mass", "xi_0", "nu", "coeff_t", "coeff_r"],
            )
            self.assertEqual(
                payload["clarification_batch_card"]["current_batch_display_fields"],
                [
                    "source_timeslices",
                    "gauge_fixed",
                    "mass",
                    "xi_0",
                    "nu",
                    "coeff_t",
                    "coeff_r",
                    "solver_tol",
                    "solver_maxiter",
                ],
            )
            self.assertEqual(payload["clarification_batch_card"]["remaining_after_batch_count"], 3)
            self.assertEqual(
                payload["clarification_batch_card"]["remaining_after_batch_preview"],
                ["gauge_path", "lattice_size", "grid_size"],
            )
            self.assertEqual(payload["clarification_batch_card"]["recommended_answer_mode"], "set")
            self.assertTrue(payload["clarification_batch_card"]["grouped_set_available"])
            self.assertEqual(payload["clarification_batch_card"]["field_group_ids"], ["clover_solver_parameters"])
            self.assertEqual(payload["clarification_batch_card"]["next_milestone"], "further_clarification")
            self.assertEqual(
                payload["workflow_outcome"]["clarification_batch_card"]["remaining_after_batch_count"],
                3,
            )
            self.assertEqual(payload["capability_summary"]["backend"]["state"], "fallback")
            self.assertEqual(payload["capability_summary"]["generation"]["state"], "blocked_on_clarification")
            self.assertFalse(payload["capability_summary"]["generation"]["ready"])
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "blocked_by_clarification")
            self.assertEqual(payload["capability_summary"]["next_step"]["kind"], "continue_by_set")
            self.assertEqual(payload["workflow_outcome"]["recommended_command"], payload["primary_action"]["command"])
            self.assertEqual(payload["primary_action"]["priority"], "primary")
            self.assertEqual(payload["action_queue"][1]["priority"], "secondary")
            self.assertIn("more input is required", payload["terminal_message"]["headline"].lower())
            self.assertIn(
                "Current missing conditions by scope: Physics: source_timeslices, gauge_fixed; Implementation: mass, xi_0, nu, coeff_t, coeff_r, solver_tol, solver_maxiter.",
                payload["terminal_message"]["detail"],
            )
            self.assertEqual(payload["terminal_message"]["recommended_command"], payload["primary_action"]["command"])
            self.assertEqual(len(payload["terminal_message"]["alternative_commands"]), 1)
            self.assertIn("--reply 0", payload["terminal_message"]["alternative_commands"][0]["command"])
            self.assertIn("missing_fields_preview", payload)
            self.assertIn("pending_question_prompts", payload)
            self.assertIn("source timeslice", payload["pending_question_prompts"][0])
            self.assertIn("pending_question_preview", payload)
            self.assertEqual(payload["pending_question_preview"][0]["field_name"], "source_timeslices")
            self.assertEqual(payload["pending_question_preview"][0]["answer_kind"], "integer_list")
            self.assertEqual(payload["pending_question_preview"][0]["answer_example"], "0")
            self.assertIn("pending_set_examples", payload)
            self.assertIn("pending_reply_examples", payload)
            self.assertIn("--reply 0", payload["pending_reply_examples"][0])
            self.assertIn("--set source_timeslices=0", payload["pending_set_examples"][0])
            self.assertIn("resume_hint", payload)
            self.assertIn("reply_hint", payload)
            self.assertIn("set_hint", payload)
            self.assertIn("--backend auto", payload["resume_hint"])
            self.assertIn("--result-format summary", payload["resume_hint"])
            self.assertIn("--dry-run", payload["resume_hint"])
            self.assertIn("--no-interactive", payload["resume_hint"])
            self.assertTrue(payload["llm_fallback"])
            self.assertEqual(payload["llm_fallback_reason"], "mocked test fallback")
            self.assertIn("--reply 0", payload["reply_hint"])
            self.assertIn("source_timeslices=0", payload["set_hint"])
            self.assertTrue(payload["clarification_status"]["active"])
            self.assertEqual(payload["clarification_status"]["mode"], "task_fields")
            self.assertEqual(payload["clarification_status"]["question_batch_fields"][:3], ["source_timeslices", "gauge_fixed", "mass"])
            self.assertTrue(payload["clarification_status"]["preview_truncated"])
            self.assertEqual(payload["clarification_status"]["recommended_answer_mode"], "set")
            self.assertIn("Current batch: source_timeslices, gauge_fixed, mass.", payload["next_action"])
            self.assertNotIn("Next question:", payload["next_action"])
            self.assertNotIn("Example answer:", payload["next_action"])
            self.assertTrue(payload["artifacts"]["session"].endswith(".session.json"))
            self.assertEqual(payload["backend_diagnostic"]["status"], "fallback")
            self.assertEqual(payload["action_queue"][0]["kind"], "continue_by_set")
            self.assertIn("source_timeslices, gauge_fixed, mass", payload["action_queue"][0]["title"])
            self.assertIn("Current batch: source_timeslices, gauge_fixed, mass.", payload["action_queue"][1]["guidance"])
            self.assertIn("--set clover_solver_parameters=", payload["action_queue"][0]["command"])
            self.assertIn("--set source_timeslices=0", payload["action_queue"][0]["command"])
            self.assertIn("--set gauge_fixed=yes", payload["action_queue"][0]["command"])
            self.assertTrue(payload["action_queue"][0]["actionable"])
            self.assertEqual(payload["action_queue"][1]["kind"], "continue_by_reply")
            self.assertIn("source_timeslices, gauge_fixed, mass", payload["action_queue"][1]["title"])
            self.assertIn("current batch: source_timeslices, gauge_fixed, mass", payload["action_queue"][1]["guidance"].lower())
            self.assertEqual(payload["primary_action"]["kind"], "continue_by_set")
            self.assertIn("source_timeslices, gauge_fixed, mass", payload["primary_action"]["title"])
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")
            self.assertEqual(payload["run_overview"]["primary_action_kind"], "continue_by_set")
            self.assertTrue(payload["run_overview"]["can_continue_now"])
            self.assertEqual(payload["blocking_reason"], "mocked test fallback")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_fallback")
            self.assertEqual(payload["blocking_reason_detail"]["source"], "backend")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "fallback")
            self.assertEqual(payload["inspection_hint"]["artifact_key"], "task")
            self.assertTrue(payload["inspection_hint"]["path"].endswith(".task.json"))
            self.assertEqual(payload["workflow_outcome"]["action_queue"][0]["kind"], "continue_by_set")
            self.assertEqual(payload["workflow_outcome"]["primary_action"]["kind"], "continue_by_set")
            self.assertNotIn("task", payload)
            self.assertNotIn("implementation_plan", payload)

    def test_cli_run_summary_reports_api_configuration_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL.",
                            "fallback_category": "configuration_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "configuration_missing")
            self.assertEqual(payload["backend_diagnostic"]["failure_origin"], "local_configuration")
            self.assertEqual(payload["backend_diagnostic"]["recovery_mode"], "configure_backend")
            self.assertTrue(payload["backend_diagnostic"]["retryable_now"])
            self.assertIn("--backend api --model", payload["backend_diagnostic"]["recommended_fix"])
            self.assertEqual(payload["workflow_outcome"]["backend_diagnostic"]["category"], "configuration_missing")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_configuration_missing")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "configuration_missing")
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertIn("--backend api", backend_fix["command"])
            self.assertIn("--model openai/gpt-5-mini", backend_fix["command"])
            self.assertEqual(backend_fix["action_state"], "conditional")
            self.assertFalse(backend_fix["actionable"])
            self.assertIn("credentials", backend_fix["actionability_reason"].lower())
            self.assertEqual(payload["run_overview"]["backend_state"], "fallback")

    def test_cli_run_summary_marks_credentials_fix_as_non_actionable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested for openai/gpt-5-mini, but no API key was configured.",
                            "fallback_category": "credentials_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_credentials_missing")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "credentials_missing")
            self.assertFalse(backend_fix["actionable"])
            self.assertEqual(backend_fix["action_state"], "blocked")
            self.assertIsNone(backend_fix["command"])
            self.assertIn("credentials", backend_fix["actionability_reason"].lower())

    def test_cli_run_dry_run_backend_diagnostic_is_phase_aware(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested for openai/gpt-5-mini, but no API key was configured.",
                            "fallback_category": "credentials_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "dry_run")
            self.assertIn("current grounded dry-run plan", payload["backend_diagnostic"]["next_step"])
            self.assertNotIn("clarification result", payload["backend_diagnostic"]["next_step"])

    def test_cli_run_summary_reports_codex_timeout_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--llm-timeout",
                "5",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("Codex backend timed out after 5 seconds.", "timeout"),
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["llm_attempted"])
            self.assertEqual(payload["backend_diagnostic"]["category"], "timeout")
            self.assertEqual(payload["backend_diagnostic"]["failure_origin"], "network")
            self.assertEqual(payload["backend_diagnostic"]["recovery_mode"], "retry_or_switch_backend")
            self.assertTrue(payload["backend_diagnostic"]["retryable_now"])
            self.assertIn("--llm-timeout", payload["backend_diagnostic"]["recommended_fix"])
            self.assertIn("did not answer in time", payload["backend_diagnostic"]["next_step"])
            self.assertEqual(payload["workflow_outcome"]["backend_diagnostic"]["category"], "timeout")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_timeout")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "timeout")
            self.assertEqual(payload["action_queue"][0]["kind"], "continue_by_set")
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["title"], "Increase backend timeout and retry")
            self.assertIn("--llm-timeout 10.0", backend_fix["command"])
            self.assertEqual(backend_fix["action_state"], "ready")
            self.assertTrue(backend_fix["actionable"])
            self.assertTrue(payload["primary_action"]["actionable"])
            self.assertEqual(payload["run_overview"]["blocking_kind"], "backend_fallback")

    def test_cli_run_summary_reports_api_endpoint_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("API request failed with status 404", "endpoint_not_found"),
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "endpoint_not_found")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_endpoint_not_found")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "endpoint_not_found")
            self.assertIn("base-url", payload["backend_diagnostic"]["recommended_fix"].lower())
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["action_state"], "conditional")
            self.assertFalse(backend_fix["actionable"])
            self.assertIn("--backend api", backend_fix["command"])
            self.assertIn("endpoint or request configuration", backend_fix["actionability_reason"].lower())

    def test_cli_run_summary_prefers_backend_switch_for_capped_codex_intent_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend(
                            f"Codex backend timed out after {INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS:g} seconds.",
                            "timeout",
                            name="codex",
                            timeout_seconds=60.0,
                        ),
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "timeout")
            self.assertEqual(payload["backend_diagnostic"]["intent_primary_timeout_seconds"], INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS)
            self.assertTrue(payload["backend_diagnostic"]["intent_timeout_capped"])
            self.assertIn("switching backend is more likely to help", payload["backend_diagnostic"]["next_step"].lower())
            self.assertIn("--backend api", payload["backend_diagnostic"]["recommended_fix"])
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["title"], "Switch to an API backend for this request")
            self.assertEqual(backend_fix["action_state"], "conditional")
            self.assertFalse(backend_fix["actionable"])
            self.assertIn("--backend api", backend_fix["command"])
            self.assertIn("capped first-attempt timeout", backend_fix["actionability_reason"].lower())

    def test_cli_run_summary_reports_response_parse_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--llm-timeout",
                "7",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("API response did not contain choices[0].message.content", "response_parse_error"),
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "response_parse_error")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_response_parse_error")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "response_parse_error")
            self.assertIn("could not parse", payload["backend_diagnostic"]["next_step"].lower())
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["action_state"], "conditional")
            self.assertFalse(backend_fix["actionable"])
            self.assertIn("--llm-timeout 14.0", backend_fix["command"])
            self.assertIn("switching backend may be necessary", backend_fix["actionability_reason"].lower())

    def test_cli_run_summary_reports_api_network_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("API request failed: temporary DNS failure", "network_error"),
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "network_error")
            self.assertEqual(payload["backend_diagnostic"]["detail_category"], "dns_resolution_failure")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_network_error")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "network_error")
            self.assertEqual(payload["blocking_reason_detail"]["backend_detail_category"], "dns_resolution_failure")
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["title"], "Restore DNS/network access before retrying backend assistance")
            self.assertEqual(backend_fix["action_state"], "blocked")
            self.assertFalse(backend_fix["actionable"])

    def test_cli_run_summary_reports_api_request_error_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("API request failed with status 400", "request_error"),
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "request_error")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_request_error")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "request_error")

    def test_cli_run_summary_reports_api_empty_response_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("API backend returned an empty response.", "empty_response"),
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "empty_response")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_empty_response")
            self.assertEqual(payload["blocking_reason_detail"]["backend_category"], "empty_response")

    def test_cli_run_summary_reports_codex_local_environment_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("Codex backend failed during local app-client initialization.", "local_environment_error"),
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "local_environment_error")
            self.assertEqual(payload["backend_diagnostic"]["detail_category"], "codex_app_client_init_failed")
            self.assertEqual(payload["backend_diagnostic"]["failure_origin"], "local_backend")
            self.assertEqual(payload["backend_diagnostic"]["recovery_mode"], "repair_or_switch_backend")
            self.assertFalse(payload["backend_diagnostic"]["retryable_now"])
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_local_environment_error")
            self.assertEqual(payload["blocking_reason_detail"]["backend_detail_category"], "codex_app_client_init_failed")
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["title"], "Verify local codex exec in a normal shell")
            self.assertEqual(backend_fix["action_state"], "conditional")
            self.assertFalse(backend_fix["actionable"])
            self.assertEqual(backend_fix["command"], "codex exec 'Reply with exactly: OK'")
            self.assertIn("codex exec", backend_fix["actionability_reason"].lower())

    def test_cli_run_summary_reports_backend_service_unavailable_guidance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("API upstream service unavailable.", "upstream_service_error"),
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": True,
                            "backend_name": "api:openai/gpt-5-mini",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "upstream_service_error")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "backend_service_unavailable")
            backend_fix = next(item for item in payload["action_queue"] if item["kind"] == "backend_fix")
            self.assertEqual(backend_fix["action_state"], "conditional")
            self.assertFalse(backend_fix["actionable"])
            self.assertIn("--backend api", backend_fix["command"])
            self.assertIn("retry later or switch backend", backend_fix["actionability_reason"].lower())

    def test_cli_run_summary_exposes_explicit_codex_preflight_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "selected_backend": "rules",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "Explicit codex backend failed preflight (mock timeout), so the run will use the rule-based path.",
                            "fallback_category": "timeout",
                            "selection_reason": "Explicit codex backend failed short preflight and fell back to rules.",
                            "codex_preflight_attempted": True,
                            "codex_preflight_timeout_seconds": EXPLICIT_CODEX_PREFLIGHT_TIMEOUT_SECONDS,
                            "codex_preflight_status": "failed",
                            "codex_preflight_category": "timeout",
                            "codex_preflight_reason": "mock timeout",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["selected_backend"], "rules")
            self.assertTrue(payload["llm_codex_preflight_attempted"])
            self.assertEqual(payload["llm_codex_preflight_status"], "failed")
            self.assertEqual(payload["llm_codex_preflight_category"], "timeout")
            self.assertEqual(payload["backend_selection_reason"], "Explicit codex backend failed short preflight and fell back to rules.")

    def test_cli_run_summary_exposes_skipped_codex_preflight_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--backend",
                "codex",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": True,
                            "fallback_reason": "mock fallback after real codex call",
                            "fallback_category": "timeout",
                            "selection_reason": "Explicit codex backend skipped preflight for a rough normalization-only request; the real codex call will decide whether fallback is necessary.",
                            "codex_preflight_attempted": False,
                            "codex_preflight_status": "skipped",
                            "codex_preflight_skipped": True,
                            "codex_preflight_skip_reason": "mock skip reason",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertFalse(payload["llm_codex_preflight_attempted"])
            self.assertTrue(payload["llm_codex_preflight_skipped"])
            self.assertEqual(payload["llm_codex_preflight_skip_reason"], "mock skip reason")
            self.assertEqual(payload["backend_selection_reason"], "Explicit codex backend skipped preflight for a rough normalization-only request; the real codex call will decide whether fallback is necessary.")

    def test_cli_run_full_payload_mirrors_backend_diagnostic_top_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL.",
                            "fallback_category": "configuration_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["backend_diagnostic"]["category"], "configuration_missing")
            self.assertEqual(payload["backend_diagnostic"], payload["result_summary"]["backend_diagnostic"])
            self.assertEqual(payload["run_overview"], payload["result_summary"]["run_overview"])
            self.assertEqual(payload["capability_summary"], payload["result_summary"]["capability_summary"])
            self.assertEqual(payload["generation_result"], payload["result_summary"]["generation_result"])
            self.assertEqual(payload["execution_result"], payload["result_summary"]["execution_result"])
            self.assertEqual(payload["blocking_reason"], payload["result_summary"]["blocking_reason"])
            self.assertEqual(payload["blocking_reason_detail"], payload["result_summary"]["blocking_reason_detail"])
            self.assertEqual(payload["inspection_hint"], payload["result_summary"]["inspection_hint"])
            self.assertEqual(payload["frontend_profile"], payload["result_summary"]["frontend_profile"])
            self.assertEqual(
                payload["result_summary"]["frontend_profile"]["status_card"]["product_status"],
                payload["result_summary"]["product_status"],
            )
            self.assertEqual(
                payload["result_summary"]["frontend_profile"]["status_card"]["blocking_kind"],
                payload["result_summary"]["run_overview"]["blocking_kind"],
            )
            self.assertEqual(
                payload["result_summary"]["frontend_profile"]["next"]["action_kind"],
                (payload["result_summary"]["primary_action"] or {}).get("kind"),
            )

    def test_continuation_hints_preserve_mode_flags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "api",
                "--model",
                "openai/gpt-5-mini",
                "--result-format",
                "summary",
                "--dry-run",
                "--no-interactive",
                "--enable-external-lookup",
                "--llm-timeout",
                "12",
                "--runtime-probe",
                "--probe-timeout",
                "5",
                "--probe-use-repo-pythonpath",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            for key in ("resume_hint", "reply_hint", "set_hint"):
                self.assertIn("--backend api", payload[key])
                self.assertIn("--model openai/gpt-5-mini", payload[key])
                self.assertIn("--result-format summary", payload[key])
                self.assertIn("--dry-run", payload[key])
                self.assertIn("--no-interactive", payload[key])
                self.assertIn("--enable-external-lookup", payload[key])
                self.assertIn("--llm-timeout 12.0", payload[key])
                self.assertIn("--runtime-probe", payload[key])
                self.assertIn("--probe-timeout 5.0", payload[key])
                self.assertIn("--probe-use-repo-pythonpath", payload[key])

    def test_cli_run_can_print_summary_via_result_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--result-format",
                "summary",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["workflow_target"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertIn("artifacts", payload)

    def test_cli_run_can_print_terminal_message_via_result_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--result-format",
                "terminal",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome:", rendered)
            self.assertIn("More input is required before code generation.", rendered)
            self.assertIn("Reason:", rendered)
            self.assertIn("mocked test fallback", rendered)
            self.assertIn("Category: backend_fallback", rendered)
            self.assertIn("Status:", rendered)
            self.assertIn("Backend: fallback", rendered)
            self.assertIn("Generation: blocked_on_clarification", rendered)
            self.assertIn("Runtime: blocked_by_clarification", rendered)
            self.assertIn("External lookup: disabled", rendered)
            self.assertIn("Execution: needs_clarification | inspect=task | next=continue_by_set", rendered)
            self.assertIn("Execution detail: Clarification is still required before grounded code generation.", rendered)
            self.assertIn("Backend class: backend_fallback", rendered)
            self.assertIn("Physics: confirmed=pion_two_point_correlator", rendered)
            self.assertIn("Clarification: task_fields | missing=source_timeslices, gauge_fixed, mass", rendered)
            self.assertIn("Next prompt: 请提供 source timeslice，例如 0。", rendered)
            self.assertIn("Example answer: 0", rendered)
            self.assertIn("Workflow: pion_2pt_chroma_wall_local_zero_momentum_npy_v1", rendered)
            self.assertIn("Actionability: ready | kind=continue_by_set | copyable=yes", rendered)
            self.assertIn("Continuation: now=yes | gate=backend_fallback | action=continue_by_set", rendered)
            self.assertIn("Backend retry: no | category=configuration_missing", rendered)
            self.assertIn("Lifecycle: needs_input | gate=backend_fallback | next=continue_by_set", rendered)
            self.assertIn("Results:", rendered)
            self.assertIn("Generation result: blocked_on_input", rendered)
            self.assertIn("Execution result: blocked_by_generation", rendered)
            self.assertIn("Artifacts:", rendered)
            self.assertIn("Session:", rendered)
            self.assertIn("Physics:", rendered)
            self.assertIn("Task:", rendered)
            self.assertIn("Plan:", rendered)
            self.assertIn("Inspect first: Task:", rendered)
            self.assertIn("Command:\n  PYTHONPATH=src python3 -m pyquda_agent.cli run", rendered)
            self.assertIn("Options:", rendered)
            self.assertIn("--reply 0", rendered)
            self.assertNotIn("\"status\":", rendered)

    def test_run_command_preserves_terminal_mode_in_continuation_hints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            config = RunConfig(
                task_description="please compute the pion two-point correlator",
                backend="codex",
                model=None,
                api_key_file=root / "api.key",
                base_url=None,
                pyquda_repo=pyquda,
                output=output,
                output_explicit=True,
                interactive=False,
                max_questions=7,
                save_session=None,
                resume_session=None,
                print_context=False,
                dry_run=True,
                verbose=False,
                result_format="terminal",
                set_fields=[],
                reply_answers=[],
                enable_external_lookup=False,
                llm_timeout=30.0,
                runtime_probe=False,
                probe_timeout=30.0,
                probe_use_repo_pythonpath=False,
                workspace_root=root,
            )
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    payload = run_command(config)

            self.assertEqual(payload["status"], "needs_input")
            for key in ("resume_hint", "reply_hint", "set_hint"):
                self.assertIn("--result-format terminal", payload[key])
            self.assertIn("--result-format terminal", payload["primary_action"]["command"])
            self.assertIn(
                "--result-format terminal",
                payload["terminal_message"]["alternative_commands"][0]["command"],
            )

    def test_cli_run_terminal_mode_prints_unsupported_retry_options(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete pion 2pt from existing propagator /tmp/prop_a.npy volume source "
                "local sink zero momentum gauge fixed lattice size 4 4 4 8 grid 1 1 1 1 "
                "resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "api",
                "--dry-run",
                "--no-interactive",
                "--result-format",
                "terminal",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL.",
                            "fallback_category": "configuration_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome:", rendered)
            self.assertIn("Detail:", rendered)
            self.assertIn("outside the current grounded workflow scope", rendered.lower())
            self.assertIn(
                "Nearest grounded: workflow=pion_2pt_existing_propagator_local_zero_momentum_npy_v1 | scope=physics | changes=1 | repair=choice_required",
                rendered,
            )
            self.assertIn("Fix by scope: Missing conditions by scope: Physics: source_type in {wall, point}.", rendered)
            self.assertIn(
                "Repair hint: Fastest grounded retry needs one explicit choice first: choose source_type from {wall, point}.",
                rendered,
            )
            self.assertIn("Options:", rendered)
            self.assertIn("source_type=wall", rendered)
            self.assertIn("source_type=point", rendered)

    def test_cli_run_terminal_mode_surfaces_physics_candidates_for_ambiguous_meson_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I want a meson correlator script but I am not sure about the exact operator",
                "--result-format",
                "terminal",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Physics: inferred=meson_two_point_correlator_unspecified", rendered)
            self.assertIn("Candidates:", rendered)
            self.assertIn("meson_two_point_correlator_unspecified", rendered)
            self.assertIn("pion_two_point_correlator", rendered)
            self.assertIn("pion_dispersion_correlator", rendered)
            self.assertIn("Formula candidates:", rendered)
            self.assertIn("Workflow hints:", rendered)
            self.assertIn("meson_two_point_correlator_unspecified", rendered)
            self.assertIn("pion_2pt_chroma_wall_local_zero_momentum_npy_v1", rendered)
            self.assertIn("Meson two-point correlator requires channel/operator choice", rendered)
            self.assertIn("Pion pseudoscalar two-point correlator", rendered)
            self.assertIn("operator=Underspecified", rendered)
            self.assertIn("provenance=model_inference", rendered)
            self.assertIn("Clarification: physics_confirmation | missing=confirmed_target_id", rendered)
            self.assertIn("Next prompt:", rendered)
            self.assertIn("候选公式/operator/假设包括：", rendered)
            self.assertIn("operator=O_\\pi(x) = \\bar d(x) \\gamma_5 u(x)", rendered)
            self.assertIn("Example answer: pion", rendered)

    def test_cli_run_terminal_mode_surfaces_baryon_channel_confirmation_for_nucleon_request(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for the nucleon correlator",
                "--result-format",
                "terminal",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Physics: inferred=baryon_two_point_correlator_unspecified", rendered)
            self.assertIn("Candidates:", rendered)
            self.assertIn("baryon_two_point_correlator_unspecified", rendered)
            self.assertIn("proton_two_point_correlator", rendered)
            self.assertIn("neutron_two_point_correlator", rendered)
            self.assertIn("Formula candidates:", rendered)
            self.assertIn("Workflow hints:", rendered)
            self.assertIn("baryon_two_point_correlator_unspecified", rendered)
            self.assertIn("proton_2pt_chroma_wall_local_zero_momentum_npy_v1", rendered)
            self.assertIn("Baryon two-point correlator requires flavor/interpolator choice", rendered)
            self.assertIn("Proton two-point correlator", rendered)
            self.assertIn("Neutron two-point correlator", rendered)
            self.assertIn("provenance=model_inference", rendered)
            self.assertIn("Clarification: physics_confirmation | missing=confirmed_target_id", rendered)
            self.assertIn("当前本地可运行 baryon workflow 只有 proton two-point correlator", rendered)
            self.assertIn("如果你指的是 neutron，请回答 neutron", rendered)
            self.assertIn("Example answer: proton", rendered)

    def test_cli_run_terminal_mode_surfaces_runtime_execution_closure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--runtime-probe",
                "--result-format",
                "terminal",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            probe_payload = {
                "status": "runtime_missing",
                "runtime_level": "environment_missing",
                "evidence_levels": {
                    "runtime_ready": False,
                    "runtime_proved": False,
                    "current_level": "environment_missing",
                    "blockers": ["Missing runtime dependency 'cupy'"],
                },
            }
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload):
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome:", rendered)
            self.assertIn("Execution: runtime_environment_missing | inspect=probe | next=retry_probe", rendered)
            self.assertIn("Checkpoint: runtime_environment_missing | runtime=environment_missing | probe=runtime_missing | handoff=ready", rendered)
            self.assertIn("Execution detail: The grounded script exists, but the runtime environment is incomplete.", rendered)
            self.assertIn("Runtime class: environment_missing", rendered)
            self.assertIn("Workflow: pion_2pt_chroma_wall_local_zero_momentum_npy_v1", rendered)
            self.assertIn("Handoff: | start_from=gauge | input_dirs=1 | output_dirs=1 | writer=rank0_only", rendered)
            self.assertIn("Input policy: treat_gauge_input_directories_as_shared_read_only_storage_when_possible", rendered)
            self.assertIn("Output policy: write_new_outputs_to_explicit_writable_results_directory", rendered)
            self.assertIn("Input dirs: /private/tmp", rendered)
            self.assertIn("Runtime evidence: level=environment_missing", rendered)
            self.assertIn("Actionability: ready | kind=retry_probe | copyable=yes", rendered)
            self.assertIn("Continuation: now=yes | gate=runtime_environment | action=retry_probe", rendered)
            self.assertIn("Runtime retry: yes | category=environment_missing", rendered)
            self.assertIn(
                "Runtime fix: conditional | title=Repair the runtime environment before retrying the probe | copyable=no",
                rendered,
            )
            self.assertIn("Runtime fix detail:", rendered)
            self.assertIn("Runtime fix blocker: Requires a PyQUDA runtime", rendered)
            self.assertIn("Artifacts:", rendered)
            self.assertIn("Probe:", rendered)
            self.assertIn("Command:", rendered)

    def test_cli_run_terminal_mode_surfaces_propagator_entry_handoff_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete pion 2pt from existing propagator /tmp/pt_prop_0.npy /tmp/pt_prop_8.npy "
                "wall source local sink zero momentum timeslice 0 timeslice 8 lattice size 24 24 24 72 "
                "grid 1 1 1 2 gauge fixed outputs/pion_prop.npy outputs/run_pion_prop.py "
                "resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "api",
                "--no-interactive",
                "--result-format",
                "terminal",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Workflow: pion_2pt_existing_propagator_local_zero_momentum_npy_v1", rendered)
            self.assertIn("Handoff: | start_from=propagator | input_dirs=1 | output_dirs=1 | writer=rank0_only", rendered)
            self.assertIn("Input policy: treat_input_directories_as_read_only_handoff_storage", rendered)
            self.assertIn("Output policy: prefer_dedicated_writable_results_directory", rendered)
            self.assertIn("Input dirs: /private/tmp", rendered)
            self.assertIn("Output dirs:", rendered)

    def test_cli_run_terminal_mode_surfaces_runtime_proved_without_repair_noise(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--runtime-probe",
                "--result-format",
                "terminal",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            probe_payload = {
                "status": "ok",
                "runtime_level": "runtime_proved",
                "evidence_levels": {
                    "runtime_ready": True,
                    "runtime_proved": True,
                    "current_level": "runtime_proved",
                    "blockers": [],
                },
            }
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload):
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Outcome:", rendered)
            self.assertIn("runtime proof succeeded", rendered.lower())
            self.assertIn("Execution: runtime_proved | inspect=probe", rendered)
            self.assertIn("Execution detail: Grounded script generation and runtime proof both succeeded.", rendered)
            self.assertIn("Runtime class: runtime_proved", rendered)
            self.assertIn("Runtime evidence: level=runtime_proved", rendered)
            self.assertIn("Results:", rendered)
            self.assertIn("Execution result: runtime_proved", rendered)
            self.assertIn("Lifecycle: runtime_proved", rendered)
            self.assertIn("Inspect first: Probe:", rendered)
            self.assertNotIn("Backend fix:", rendered)
            self.assertNotIn("Runtime fix:", rendered)
            self.assertNotIn("Continuation:", rendered)
            self.assertNotIn("Backend retry:", rendered)
            self.assertNotIn("gate=none", rendered)
            self.assertNotIn("Command:\n", rendered)

    def test_cli_run_terminal_mode_surfaces_backend_fix_for_timeout(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--result-format",
                "terminal",
                "--dry-run",
                "--no-interactive",
                "--llm-timeout",
                "5",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("Codex backend timed out after 5 seconds.", "timeout"),
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Backend retry: yes | category=timeout", rendered)
            self.assertIn("Backend fix: ready | title=Increase backend timeout and retry | copyable=yes", rendered)
            self.assertIn("Backend fix detail:", rendered)
            self.assertIn("--llm-timeout", rendered)
            self.assertIn("Backend fix command: PYTHONPATH=src python3 -m pyquda_agent.cli run", rendered)

    def test_cli_run_terminal_mode_surfaces_conditional_backend_fix_for_local_codex_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--result-format",
                "terminal",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        _FailingBackend("Codex backend failed during local app-client initialization.", "local_environment_error"),
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "fallback_category": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            rendered = stdout.getvalue().strip()
            self.assertEqual(exit_code, 0)
            self.assertIn("Backend retry: no | category=local_environment_error", rendered)
            self.assertIn(
                "Backend fix: conditional | title=Verify local codex exec in a normal shell | copyable=not_now",
                rendered,
            )
            self.assertIn("Backend fix blocker: Requires checking whether bare `codex exec` works", rendered)
            self.assertIn("Backend fix command: codex exec 'Reply with exactly: OK'", rendered)

    def test_cli_run_invokes_configured_api_backend_in_real_run_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            backend = _InvokingBackend(
                """
                {
                  "normalized_request": "Compute the pion two-point correlator.",
                  "physics_status": "needs_confirmation",
                  "candidate_targets": [
                    {
                      "target_id": "pion_two_point_correlator",
                      "label": "pion two-point correlator",
                      "summary": "Likely pion two-point target.",
                      "confidence": "medium",
                      "status": "inferred",
                      "task_type_hint": "pion_2pt"
                    }
                  ],
                  "formula_proposals": [
                    {
                      "proposal_id": "pion_prop",
                      "target_id": "pion_two_point_correlator",
                      "label": "Pion 2pt",
                      "operator": "O_pi = dbar gamma5 u",
                      "correlator": "C(t) = sum_x <O(t) O^dagger(0)>",
                      "convention": "Use a pseudoscalar pion operator."
                    }
                  ],
                  "notes": ["llm used in cli test"]
                }
                """
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--backend",
                "api",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        backend,
                        {
                            "requested_backend": "api",
                            "configured": True,
                            "backend_name": "api:test/model",
                            "fallback": False,
                            "fallback_reason": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(backend.calls, 1)
            self.assertEqual(payload["status"], "needs_input")
            self.assertTrue(payload["llm_assistance"]["used"])
            self.assertFalse(payload["llm_assistance"]["fallback"])
            self.assertEqual(payload["physics"]["normalized_request"], "Compute the pion two-point correlator.")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "pion_two_point_correlator")

    def test_cli_run_invokes_configured_codex_backend_in_real_run_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            backend = _InvokingBackend(
                """
                {
                  "normalized_request": "Compute the pion two-point correlator.",
                  "physics_status": "needs_confirmation",
                  "candidate_targets": [
                    {
                      "target_id": "pion_two_point_correlator",
                      "label": "pion two-point correlator",
                      "summary": "Likely pion two-point target.",
                      "confidence": "medium",
                      "status": "inferred",
                      "task_type_hint": "pion_2pt"
                    }
                  ],
                  "formula_proposals": [
                    {
                      "proposal_id": "pion_prop",
                      "target_id": "pion_two_point_correlator",
                      "label": "Pion 2pt",
                      "operator": "O_pi = dbar gamma5 u",
                      "correlator": "C(t) = sum_x <O(t) O^dagger(0)>",
                      "convention": "Use a pseudoscalar pion operator."
                    }
                  ],
                  "notes": ["codex backend used in cli test"]
                }
                """
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        backend,
                        {
                            "requested_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(backend.calls, 1)
            self.assertEqual(payload["status"], "needs_input")
            self.assertTrue(payload["llm_assistance"]["used"])
            self.assertEqual(payload["llm_assistance"]["configured_backend"], "codex")
            self.assertEqual(payload["llm_assistance"]["intent_strategy"], "normalization_only")
            self.assertEqual(payload["llm_assistance"]["intent_prompt_profile"], "normalization_only")
            self.assertEqual(payload["result_summary"]["llm_intent_strategy"], "normalization_only")
            assert backend.last_user_prompt is not None
            self.assertIn("Keep the existing target guess", backend.last_user_prompt)
            self.assertIn("formula_proposals", payload["physics"])

    def test_cli_run_records_timeout_recovery_when_second_attempt_succeeds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            backend = _SequenceBackend(
                [
                    BackendInvocationError("initial timeout", category="timeout"),
                    """
                    {
                      "normalized_request": "Compute a meson two-point correlator after choosing the channel/operator.",
                      "physics_status": "needs_confirmation",
                      "candidate_targets": [
                        {
                          "target_id": "meson_two_point_correlator_unspecified",
                          "label": "meson two-point correlator with unspecified channel/operator",
                          "summary": "Meson channel still needs confirmation.",
                          "confidence": "medium",
                          "status": "needs_confirmation",
                          "task_type_hint": null
                        }
                      ],
                      "formula_proposals": [],
                      "notes": ["recovery used in cli test"]
                    }
                    """,
                ],
                timeout_seconds=60.0,
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "I want a meson correlator script but I am not sure about the exact operator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        backend,
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "selection_reason": "mocked explicit codex backend",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(backend.calls, 2)
            self.assertTrue(payload["llm_assistance"]["used"])
            self.assertTrue(payload["llm_assistance"]["timeout_recovery_attempted"])
            self.assertFalse(payload["llm_assistance"]["timeout_recovery_skipped"])
            self.assertTrue(payload["llm_assistance"]["timeout_recovery_used"])
            self.assertEqual(payload["llm_assistance"]["intent_primary_timeout_seconds"], INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS)
            self.assertFalse(payload["llm_assistance"]["fallback"])
            self.assertEqual(backend.seen_timeouts, [INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS, INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS])
            self.assertTrue(payload["result_summary"]["llm_timeout_recovery_attempted"])
            self.assertTrue(payload["result_summary"]["llm_timeout_recovery_used"])
            self.assertFalse(payload["result_summary"]["llm_timeout_recovery_failed"])
            self.assertEqual(payload["result_summary"]["llm_intent_primary_timeout_seconds"], INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS)
            self.assertEqual(payload["result_summary"]["llm_timeout_recovery_timeout_seconds"], INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS)
            self.assertEqual(payload["backend_diagnostic"]["status"], "used")
            self.assertEqual(payload["backend_diagnostic"]["intent_primary_timeout_seconds"], INTENT_CODEX_PRIMARY_TIMEOUT_SECONDS)
            self.assertTrue(payload["backend_diagnostic"]["intent_timeout_capped"])
            self.assertTrue(payload["backend_diagnostic"]["timeout_recovery_used"])
            self.assertEqual(payload["backend_diagnostic"]["timeout_recovery_timeout_seconds"], INTENT_TIMEOUT_RECOVERY_TIMEOUT_SECONDS)

    def test_cli_run_skips_timeout_recovery_for_codex_normalization_only_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            backend = _SequenceBackend([BackendInvocationError("initial timeout", category="timeout")])

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        backend,
                        {
                            "requested_backend": "codex",
                            "selected_backend": "codex",
                            "configured": True,
                            "backend_name": "codex",
                            "fallback": False,
                            "fallback_reason": None,
                            "selection_reason": "mocked explicit codex backend",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(backend.calls, 1)
            self.assertTrue(payload["llm_assistance"]["fallback"])
            self.assertEqual(payload["llm_assistance"]["intent_strategy"], "normalization_only")
            self.assertEqual(payload["llm_assistance"]["intent_primary_timeout_seconds"], INTENT_CODEX_NORMALIZATION_PRIMARY_TIMEOUT_SECONDS)
            self.assertFalse(payload["llm_assistance"]["timeout_recovery_attempted"])
            self.assertTrue(payload["llm_assistance"]["timeout_recovery_skipped"])
            self.assertIn("normalization-only intent path", payload["llm_assistance"]["timeout_recovery_skip_reason"])
            self.assertTrue(payload["result_summary"]["llm_timeout_recovery_skipped"])
            self.assertEqual(payload["backend_diagnostic"]["category"], "timeout")
            self.assertTrue(payload["backend_diagnostic"]["timeout_recovery_skipped"])

    def test_cli_run_rejects_unsupported_existing_propagator_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete pion 2pt from existing propagator /tmp/pion_prop.npy outputs/run_pion.py",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["workflow_match"]["workflow_target"], "pion_2pt_existing_propagator_local_zero_momentum_npy_v1")
            self.assertIn("lattice_size", payload["missing_fields"])

    def test_cli_run_explicit_unsupported_request_does_not_suggest_backend_fix_as_primary_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete pion 2pt from existing propagator /tmp/prop_a.npy volume source "
                "local sink zero momentum gauge fixed lattice size 4 4 4 8 grid 1 1 1 1 "
                "resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "api",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL.",
                            "fallback_category": "configuration_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "unsupported")
            self.assertEqual(payload["product_status"], "unsupported")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "unsupported")
            self.assertEqual(payload["blocking_reason_detail"]["category"], "unsupported_request")
            self.assertEqual(payload["blocking_reason_detail"]["source"], "workflow_match")
            self.assertEqual(payload["capability_summary"]["generation"]["state"], "unsupported")
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "unsupported")
            self.assertEqual(payload["capability_summary"]["next_step"]["kind"], "choose_supported_variant")
            self.assertIn("outside the current grounded workflow scope", payload["terminal_message"]["headline"].lower())
            self.assertIn("nearby grounded workflows", payload["terminal_message"]["detail"].lower())
            self.assertIn("source_type=wall", payload["terminal_message"]["recommended_command"])
            self.assertEqual(payload["primary_action"]["kind"], "choose_supported_variant")
            self.assertFalse(payload["primary_action"]["actionable"])
            self.assertIsNone(payload["primary_action"]["command"])
            self.assertIn("Choose source_type", payload["primary_action"]["title"])
            self.assertEqual(len(payload["terminal_message"]["alternative_commands"]), 3)
            self.assertEqual(len(payload["supported_workflows"]), 17)
            self.assertEqual(
                [item["workflow_target"] for item in payload["nearby_supported_workflows"]],
                [
                    "pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
                    "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
                ],
            )
            self.assertIn("source_type", payload["unsupported_guidance"]["primary_reason"])
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_targets"],
                [
                    "pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
                    "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
                ],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            )
            self.assertEqual(payload["unsupported_guidance"]["shortest_fix"]["required_change_count"], 1)
            self.assertEqual(payload["unsupported_guidance"]["primary_scope"], "physics")
            self.assertEqual(payload["unsupported_guidance"]["shortest_fix"]["primary_scope"], "physics")
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix_gap_summary"]["sentence"],
                "Missing conditions by scope: Physics: source_type in {wall, point}.",
            )
            self.assertEqual(payload["unsupported_guidance"]["repair_readiness"], "choice_required")
            self.assertEqual(payload["unsupported_guidance"]["repair_hint"]["choice_field"], "source_type")
            self.assertEqual(payload["unsupported_guidance"]["repair_hint"]["choice_values"], ["wall", "point"])
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["repair_mode"],
                "choice_required",
            )
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["primary_scope"],
                "physics",
            )
            self.assertEqual(
                payload["unsupported_guidance"]["nearest_workflow_card"]["workflow_target"],
                "pion_2pt_existing_propagator_local_zero_momentum_npy_v1",
            )
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["conflict_breakdown"]["physics"]["changes"],
                ["source_type in {wall, point}"],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["scope_breakdown"]["physics"]["changes"],
                ["source_type in {wall, point}"],
            )
            self.assertIn(
                "source_type in {wall, point}",
                payload["unsupported_guidance"]["shortest_fix"]["summary"],
            )
            self.assertIn("Primary mismatch category: physics.", payload["unsupported_guidance"]["shortest_fix"]["summary"])
            self.assertIn("wall or point", payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["adjustments"][1])
            self.assertIsNone(payload["unsupported_guidance"]["retry_suggestions"][0]["retry_command"])
            self.assertEqual(
                payload["unsupported_guidance"]["retry_suggestions"][0]["variant_fields"][0]["scope"],
                "physics",
            )
            self.assertEqual(
                [item["accepted_value"] for item in payload["unsupported_guidance"]["retry_suggestions"][0]["variant_retry_commands"]],
                ["wall", "point"],
            )
            self.assertTrue(all(item["scope"] == "physics" for item in payload["unsupported_guidance"]["retry_suggestions"][0]["variant_retry_commands"]))
            self.assertEqual(
                payload["unsupported_guidance"]["retry_suggestions"][0]["required_change_count"],
                1,
            )
            self.assertIn("--set source_type=wall", payload["unsupported_guidance"]["retry_suggestions"][0]["variant_retry_commands"][0]["command"])
            self.assertIn("--resume-session", payload["unsupported_guidance"]["retry_suggestions"][0]["variant_retry_commands"][0]["command"])
            self.assertIn("source_type=wall", payload["terminal_message"]["alternative_commands"][0]["command"])
            self.assertIn("source_type=point", payload["terminal_message"]["alternative_commands"][1]["command"])
            self.assertIn("start_from=gauge", payload["terminal_message"]["alternative_commands"][2]["command"])
            self.assertIn("confirm the physics-side choices first", payload["unsupported_guidance"]["next_step"])
            self.assertIn("Fastest grounded retry needs one explicit choice first", payload["unsupported_guidance"]["next_step"])
            self.assertIn("Nearest grounded path", payload["terminal_message"]["detail"])
            self.assertIn("Missing conditions by scope: Physics: source_type in {wall, point}.", payload["terminal_message"]["detail"])
            self.assertIn("Fastest grounded retry needs one explicit choice first", payload["terminal_message"]["detail"])
            self.assertIn("nearby_supported_workflows", payload["refusal_reason"])
            self.assertIn("current grounded unsupported assessment", payload["backend_diagnostic"]["next_step"])
            self.assertNotEqual(payload["primary_action"]["kind"], "backend_fix")

    def test_cli_run_quark_unsupported_request_reports_shortest_fix_against_quark_family(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate a quark propagator from gauge /tmp/cfg_0001.lime wall source "
                "lattice size 24 24 24 72 grid 1 1 1 2 mass=-0.2770 xi_0=1.0 nu=1.0 "
                "coeff_t=1.160920226 coeff_r=1.160920226 tol=1e-12 maxiter=1000 "
                "source timeslice 0 outputs/pt_prop.h5 outputs/run_quark.py resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "api",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "selected_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "API backend requested but no model was configured via --model or PYQUDA_AGENT_API_MODEL/OPENAI_MODEL.",
                            "fallback_category": "configuration_missing",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "unsupported")
            self.assertEqual(payload["product_status"], "unsupported")
            self.assertEqual(
                [item["workflow_target"] for item in payload["nearby_supported_workflows"]],
                [
                    "quark_propagator_chroma_point_hdf5_v1",
                    "quark_propagator_gaussian_shell_chroma_hdf5_v1",
                ],
            )
            self.assertIn("source_type='point'", payload["unsupported_guidance"]["primary_reason"])
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "quark_propagator_chroma_point_hdf5_v1",
            )
            self.assertEqual(payload["unsupported_guidance"]["shortest_fix"]["required_change_count"], 1)
            self.assertEqual(payload["unsupported_guidance"]["primary_scope"], "physics")
            self.assertEqual(payload["unsupported_guidance"]["repair_readiness"], "copyable_now")
            self.assertTrue(payload["unsupported_guidance"]["repair_hint"]["copyable_now"])
            self.assertIn("Change source_type=point.", payload["unsupported_guidance"]["shortest_fix"]["summary"])
            self.assertIn("Primary mismatch category: physics.", payload["unsupported_guidance"]["shortest_fix"]["summary"])
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix_gap_summary"]["sentence"],
                "Missing conditions by scope: Physics: source_type=point.",
            )
            self.assertIn("Fastest grounded retry: use the copyable command", payload["unsupported_guidance"]["next_step"])
            self.assertIn("workflow-fixed fields automatically", payload["unsupported_guidance"]["shortest_fix"]["summary"])
            self.assertEqual(
                [item["field_name"] for item in payload["unsupported_guidance"]["shortest_fix"]["workflow_fixed_assignments"]],
                ["sink_type", "momentum_projection", "gauge_fixed"],
            )
            self.assertIn("--set source_type=point", payload["unsupported_guidance"]["shortest_fix"]["retry_command"])
            self.assertIn("--set sink_type=propagator", payload["unsupported_guidance"]["shortest_fix"]["retry_command"])
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["repair_mode"],
                "copyable_now",
            )
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["conflict_breakdown"]["physics"]["changes"],
                ["source_type=point"],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][1]["workflow_target"],
                "quark_propagator_gaussian_shell_chroma_hdf5_v1",
            )
            self.assertIn(
                "gaussianSmear(2.0, 5)",
                payload["unsupported_guidance"]["nearby_workflow_guidance"][1]["summary"],
            )
            self.assertEqual(payload["primary_action"]["kind"], "retry_supported_workflow")
            self.assertEqual(payload["workflow_outcome"]["recommended_command"], payload["primary_action"]["command"])
            self.assertIn("source_type=point", payload["terminal_message"]["recommended_command"])
            self.assertIn("Closest grounded workflow", payload["unsupported_guidance"]["next_step"])
            self.assertIn("Missing conditions by scope: Physics: source_type=point.", payload["terminal_message"]["detail"])
            self.assertIn("Fastest grounded retry: use the copyable command", payload["terminal_message"]["detail"])
            self.assertEqual(len(payload["terminal_message"]["alternative_commands"]), 2)
            self.assertNotIn("clarification result", payload["backend_diagnostic"]["next_step"])

    def test_cli_run_explicit_rho_request_reports_nearest_grounded_meson_fix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the rho meson two-point correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "rho_vector_meson_correlator")
            self.assertTrue(any(item["proposal_id"] == "rho_vector_gammai_twopt" for item in payload["physics"]["formula_proposals"]))
            self.assertEqual(
                [item["workflow_target"] for item in payload["nearby_supported_workflows"]],
                [
                    "rho_vector_chroma_wall_local_zero_momentum_npy_v1",
                    "rho_vector_existing_propagator_local_zero_momentum_npy_v1",
                    "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
                    "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
                    "pion_dispersion_chroma_point_momentum_npy_v1",
                ],
            )
            self.assertIsNone(payload["unsupported_guidance"])
            self.assertEqual(payload["primary_action"]["kind"], "continue_by_set")
            self.assertIn("Resolve missing implementation/runtime fields", payload["terminal_message"]["detail"])
            self.assertTrue(payload["action_queue"])

    def test_cli_run_explicit_neutron_request_reports_nearest_grounded_baryon_fix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the neutron two-point correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "unsupported")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "neutron_two_point_correlator")
            self.assertTrue(any(item["proposal_id"] == "neutron_nucleon_gamma5_twopt" for item in payload["physics"]["formula_proposals"]))
            self.assertEqual(
                [item["workflow_target"] for item in payload["nearby_supported_workflows"]],
                [
                    "proton_2pt_chroma_wall_local_zero_momentum_npy_v1",
                    "proton_2pt_existing_propagator_local_zero_momentum_npy_v1",
                ],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "proton_2pt_chroma_wall_local_zero_momentum_npy_v1",
            )
            self.assertEqual(payload["unsupported_guidance"]["shortest_fix"]["required_change_count"], 1)
            self.assertEqual(payload["unsupported_guidance"]["primary_scope"], "physics")
            self.assertIn(
                "confirmed_target_id=proton",
                payload["unsupported_guidance"]["shortest_fix"]["summary"],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["nearby_workflow_guidance"][0]["conflict_breakdown"]["physics"]["changes"],
                ["confirmed_target_id=proton"],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix_gap_summary"]["sentence"],
                "Missing conditions by scope: Physics: confirmed_target_id=proton.",
            )
            self.assertIn("Closest grounded workflow", payload["unsupported_guidance"]["next_step"])
            self.assertEqual(payload["primary_action"]["kind"], "retry_supported_workflow")
            self.assertEqual(payload["workflow_outcome"]["recommended_command"], payload["primary_action"]["command"])

    def test_cli_run_rho_point_source_unsupported_prefers_rho_family_nearest_fix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the rho meson correlator with point source",
                "--backend",
                "codex",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "unsupported")
            self.assertEqual(payload["product_status"], "unsupported")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "rho_vector_meson_correlator")
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "rho_vector_chroma_wall_local_zero_momentum_npy_v1",
            )
            self.assertEqual(payload["unsupported_guidance"]["primary_scope"], "physics")
            self.assertEqual(payload["primary_action"]["kind"], "retry_supported_workflow")
            self.assertIn(
                "source_type=wall",
                payload["unsupported_guidance"]["shortest_fix"]["summary"],
            )
            self.assertIn(
                "Primary mismatch category: physics.",
                payload["unsupported_guidance"]["shortest_fix"]["summary"],
            )
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix_gap_summary"]["sentence"],
                "Missing conditions by scope: Physics: source_type=wall.",
            )
            self.assertNotEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "pion_dispersion_chroma_point_momentum_npy_v1",
            )

    def test_cli_run_explicit_stout_smear_request_with_existing_propagator_wording_stays_in_smear_family(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate a stout-smeared gauge from existing propagator /tmp/q.npy lattice size 24 24 24 72 grid 1 1 1 2 outputs/s.npy outputs/s.py resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "stout_smeared_gauge_configuration")
            self.assertEqual(payload["product_status"], "unsupported")
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "stout_smear_chroma_qio_npy_v1",
            )
            self.assertEqual(payload["unsupported_guidance"]["primary_scope"], "implementation")
            self.assertEqual(payload["primary_action"]["kind"], "retry_supported_workflow")
            self.assertIn(
                "start_from=gauge",
                payload["unsupported_guidance"]["shortest_fix_gap_summary"]["sentence"],
            )

    def test_cli_run_explicit_wilson_flow_request_with_existing_propagator_wording_stays_in_flow_family(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please run wilson flow from existing propagator /tmp/q.npy lattice size 24 24 24 72 grid 1 1 1 2 flow_steps=100 flow_epsilon=1.0 outputs/f.npy outputs/f.py resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "wilson_flow_energy_observable")
            self.assertEqual(payload["product_status"], "unsupported")
            self.assertEqual(
                payload["unsupported_guidance"]["shortest_fix"]["workflow_target"],
                "wilson_flow_chroma_qio_energy_npy_v1",
            )
            self.assertEqual(payload["unsupported_guidance"]["primary_scope"], "implementation")
            self.assertEqual(payload["primary_action"]["kind"], "retry_supported_workflow")
            self.assertIn(
                "start_from=gauge",
                payload["unsupported_guidance"]["shortest_fix_gap_summary"]["sentence"],
            )

    def test_cli_run_explicit_ape_smear_request_routes_to_supported_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate an APE-smeared gauge configuration",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "ape_smeared_gauge_configuration")
            self.assertTrue(any(item["proposal_id"] == "ape_smear_one_step_alpha25_dirignore4" for item in payload["physics"]["formula_proposals"]))
            self.assertEqual(
                [item["workflow_target"] for item in payload["nearby_supported_workflows"]],
                ["ape_smear_chroma_qio_npy_v1"],
            )
            self.assertEqual(payload["workflow_match"]["workflow_target"], "ape_smear_chroma_qio_npy_v1")
            self.assertEqual(payload["task"]["workflow_id"], "ape_smear_chroma_qio_npy_v1")
            self.assertEqual(payload["task"]["source_type"], "none")
            self.assertEqual(payload["task"]["sink_type"], "gauge")
            self.assertIn("gauge_path", payload["missing_fields"])
            self.assertIsNone(payload["unsupported_guidance"])

    def test_cli_run_explicit_hyp_smear_request_routes_to_supported_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate a HYP-smeared gauge configuration",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "hyp_smeared_gauge_configuration")
            self.assertTrue(any(item["proposal_id"] == "hyp_smear_one_step_075_06_03_dirignore4" for item in payload["physics"]["formula_proposals"]))
            self.assertEqual(
                [item["workflow_target"] for item in payload["nearby_supported_workflows"]],
                ["hyp_smear_chroma_qio_npy_v1"],
            )
            self.assertEqual(payload["workflow_match"]["workflow_target"], "hyp_smear_chroma_qio_npy_v1")
            self.assertEqual(payload["task"]["workflow_id"], "hyp_smear_chroma_qio_npy_v1")
            self.assertEqual(payload["task"]["source_type"], "none")
            self.assertEqual(payload["task"]["sink_type"], "gauge")
            self.assertIn("gauge_path", payload["missing_fields"])
            self.assertIsNone(payload["unsupported_guidance"])

    def test_cli_run_external_lookup_is_recorded_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I want a meson correlator script but I am not sure about the exact operator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--enable-external-lookup",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with patch(
                        "pyquda_agent.app.maybe_lookup_external_knowledge",
                        side_effect=lambda physics, enabled: (
                            setattr(
                                physics,
                                "external_lookup",
                                {
                                    "enabled": enabled,
                                    "attempted": True,
                                    "used": False,
                                    "status": "failed",
                                    "reason": "Live online lookup failed: URLError: mock network failure",
                                    "queries": [{"provider": "arxiv_api", "query": "mock"}],
                                    "results": [],
                                    "source_kind": "live_online_lookup",
                                    "effect_on_interpretation": "none",
                                },
                            )
                            or physics
                        ),
                    ) as lookup_mock:
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(lookup_mock.called)
            self.assertEqual(payload["physics"]["external_lookup"]["status"], "failed")
            self.assertEqual(payload["result_summary"]["external_lookup_status"], "failed")
            self.assertTrue(payload["result_summary"]["external_lookup_attempted"])
            self.assertFalse(payload["result_summary"]["external_lookup_used"])
            self.assertIn("mock network failure", payload["result_summary"]["external_lookup_reason"])

    def test_cli_run_complete_generation_supports_api_backend_without_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["product_status"], "generated_probe_available")
            self.assertEqual(payload["generation"]["used_backend"], "api")
            self.assertEqual(payload["workflow_outcome"]["phase"], "generated")
            self.assertTrue(payload["workflow_outcome"]["generation_succeeded"])
            self.assertFalse(payload["workflow_outcome"]["execution_attempted"])
            self.assertEqual(payload["workflow_outcome"]["runtime_probe_status"], "not_requested")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertTrue(payload["generation_result"]["emitted"])
            self.assertEqual(payload["execution_result"]["phase"], "probe_available")
            self.assertTrue(payload["execution_result"]["probe_available"])
            self.assertEqual(payload["workflow_outcome"]["recommended_command"], payload["probe_hint"])
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "generated")
            self.assertTrue(payload["delivery_status"]["generation"]["succeeded"])
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "probe_available")
            self.assertFalse(payload["delivery_status"]["execution"]["attempted"])
            self.assertEqual(payload["capability_summary"]["backend"]["state"], "fallback")
            self.assertEqual(payload["capability_summary"]["generation"]["state"], "generated")
            self.assertTrue(payload["capability_summary"]["generation"]["succeeded"])
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "probe_available")
            self.assertTrue(payload["capability_summary"]["runtime"]["ready"])
            self.assertFalse(payload["capability_summary"]["runtime"]["proved"])
            self.assertEqual(payload["capability_summary"]["next_step"]["kind"], "run_probe")
            self.assertIn("script was generated successfully", payload["terminal_message"]["headline"].lower())
            self.assertIn("runtime proof has not been attempted yet", payload["terminal_message"]["detail"].lower())
            self.assertEqual(payload["terminal_message"]["recommended_command"], payload["probe_hint"])
            self.assertEqual(payload["delivery_status"]["next_step"]["kind"], "run_probe")
            self.assertEqual(payload["action_queue"][0]["kind"], "run_probe")
            self.assertEqual(payload["action_queue"][0]["command"], payload["probe_hint"])
            self.assertEqual(payload["primary_action"]["kind"], "run_probe")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "runtime_probe_optional")
            self.assertIn("runtime proof has not been attempted yet", payload["result_summary"]["blocking_reason"].lower())
            self.assertEqual(payload["result_summary"]["blocking_reason_detail"]["category"], "runtime_probe_not_run")
            self.assertEqual(payload["result_summary"]["blocking_reason_detail"]["source"], "runtime")
            self.assertEqual(payload["result_summary"]["inspection_hint"]["artifact_key"], "probe")
            self.assertTrue(payload["runtime_evidence"]["generated_script_exists"])
            self.assertEqual(payload["runtime_evidence"]["generated_script_probe"]["status"], "not_run")
            self.assertFalse(payload["runtime_evidence"]["probe_policy"]["auto_run"])
            self.assertEqual(payload["next_action"], "Run the probe command to collect runtime evidence for the generated script.")
            self.assertTrue(payload["probe_hint"].startswith("python3 scripts/probe_generated_workflow.py"))
            self.assertEqual(payload["result_summary"]["probe_hint"], payload["probe_hint"])
            self.assertEqual(payload["result_summary"]["product_status"], "generated_probe_available")
            self.assertEqual(payload["result_summary"]["workflow_outcome"]["phase"], "generated")
            self.assertTrue(Path(payload["generation"]["output_path"]).exists())

    def test_cli_run_complete_generation_supports_quark_propagator_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, _output, index_path = self._prepare_repo_fixture(root)
            output = root / "outputs" / "run_quark.py"

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate a quark propagator from gauge /tmp/cfg_0001.lime "
                "lattice size 24 24 24 72 grid 1 1 1 2 mass=-0.2770 xi_0=1.0 nu=1.0 "
                "coeff_t=1.160920226 coeff_r=1.160920226 tol=1e-12 maxiter=1000 "
                "source timeslice 0 outputs/pt_prop.h5 outputs/run_quark.py resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "api",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["product_status"], "generated_probe_available")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "quark_propagator")
            self.assertEqual(payload["workflow_match"]["workflow_target"], "quark_propagator_chroma_point_hdf5_v1")
            self.assertEqual(payload["result_summary"]["physics_target"], "quark_propagator")
            self.assertEqual(payload["result_summary"]["workflow_target"], "quark_propagator_chroma_point_hdf5_v1")
            self.assertEqual(payload["task"]["task_type"], "quark_propagator")
            self.assertEqual(payload["task"]["source_type"], "point")
            self.assertEqual(payload["task"]["sink_type"], "propagator")
            self.assertEqual(payload["task"]["momentum_projection"], "none")
            self.assertEqual(payload["task"]["correlator_output_format"], "hdf5")
            self.assertTrue(payload["task"]["correlator_output_path"].endswith(".h5"))
            self.assertEqual(payload["hpc_handoff"]["output_paths"]["propagator"], payload["task"]["correlator_output_path"])
            self.assertEqual(payload["capability_summary"]["generation"]["state"], "generated")
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "probe_available")
            self.assertEqual(payload["primary_action"]["kind"], "run_probe")
            self.assertTrue(Path(payload["generation"]["output_path"]).exists())
            self.assertTrue(Path(payload["task_artifact"]).exists())
            self.assertTrue(Path(payload["physics_artifact"]).exists())
            self.assertTrue(Path(payload["plan_artifact"]).exists())
            code = Path(payload["generation"]["output_path"]).read_text(encoding="utf-8")
            self.assertIn("propagator.saveH5", code)
            self.assertIn("source.point(", code)
            self.assertNotIn("TODO", code)

    def test_cli_run_can_optionally_probe_after_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--runtime-probe",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            probe_payload = {
                "status": "runtime_missing",
                "runtime_level": "environment_missing",
                "evidence_levels": {
                    "runtime_ready": False,
                    "runtime_proved": False,
                    "current_level": "environment_missing",
                    "blockers": ["Missing runtime dependency 'cupy'"],
                },
            }
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload):
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["product_status"], "generated_runtime_blocked")
            self.assertEqual(payload["execution_status"], "runtime_missing")
            self.assertEqual(payload["generation"]["execution_status"], "runtime_missing")
            self.assertEqual(payload["workflow_outcome"]["phase"], "generated_and_probed")
            self.assertTrue(payload["workflow_outcome"]["generation_succeeded"])
            self.assertTrue(payload["workflow_outcome"]["execution_attempted"])
            self.assertFalse(payload["workflow_outcome"]["execution_succeeded"])
            self.assertEqual(payload["workflow_outcome"]["runtime_probe_status"], "runtime_missing")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertEqual(payload["execution_result"]["phase"], "runtime_missing")
            self.assertTrue(payload["execution_result"]["attempted"])
            self.assertTrue(payload["execution_result"]["blocked"])
            self.assertIn("Missing runtime dependency 'cupy'", payload["workflow_outcome"]["blockers"][0])
            self.assertEqual(payload["delivery_status"]["generation"]["phase"], "generated")
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "runtime_missing")
            self.assertTrue(payload["delivery_status"]["execution"]["attempted"])
            self.assertFalse(payload["delivery_status"]["execution"]["succeeded"])
            self.assertIn("missing required runtime pieces", payload["delivery_status"]["execution"]["headline"].lower())
            self.assertEqual(payload["runtime_diagnostic"]["status"], "runtime_missing")
            self.assertEqual(payload["runtime_diagnostic"]["category"], "environment_missing")
            self.assertIn("provides `cupy`", payload["runtime_diagnostic"]["next_step"])
            self.assertIn("rerun the probe command", payload["runtime_diagnostic"]["next_step"])
            self.assertEqual(payload["runtime_diagnostic"]["recommended_fix"], payload["runtime_diagnostic"]["next_step"])
            self.assertEqual(payload["runtime_diagnostic"]["retry_command"], payload["probe_hint"])
            self.assertIn("cupy", payload["runtime_diagnostic"]["blockers"][0])
            self.assertEqual(payload["capability_summary"]["generation"]["state"], "generated")
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "runtime_blocked")
            self.assertFalse(payload["capability_summary"]["runtime"]["ready"])
            self.assertFalse(payload["capability_summary"]["runtime"]["proved"])
            self.assertIn("Missing runtime dependency 'cupy'", payload["capability_summary"]["runtime"]["blockers"][0])
            self.assertEqual(payload["capability_summary"]["next_step"]["kind"], "retry_probe")
            self.assertIn("runtime environment is incomplete", payload["terminal_message"]["headline"].lower())
            self.assertIn("provides `cupy`", payload["terminal_message"]["detail"])
            self.assertEqual(payload["terminal_message"]["recommended_command"], payload["probe_hint"])
            self.assertEqual(payload["delivery_status"]["next_step"]["kind"], "retry_probe")
            self.assertEqual(payload["action_queue"][0]["kind"], "retry_probe")
            self.assertIn("runtime environment", payload["action_queue"][0]["title"].lower())
            self.assertEqual(payload["action_queue"][1]["kind"], "runtime_fix")
            self.assertEqual(
                payload["action_queue"][1]["title"],
                "Repair the runtime environment before retrying the probe",
            )
            self.assertEqual(payload["action_queue"][1]["action_state"], "conditional")
            self.assertFalse(payload["action_queue"][1]["actionable"])
            self.assertIsNone(payload["action_queue"][1]["command"])
            self.assertIn("missing dependencies", payload["action_queue"][1]["actionability_reason"].lower())
            self.assertIn("provides `cupy`", payload["action_queue"][1]["guidance"])
            self.assertEqual(payload["primary_action"]["kind"], "retry_probe")
            self.assertEqual(payload["run_overview"]["blocking_kind"], "runtime_environment")
            self.assertIn("missing runtime dependencies", payload["result_summary"]["blocking_reason"].lower())
            self.assertEqual(payload["result_summary"]["blocking_reason_detail"]["category"], "runtime_dependencies_missing")
            self.assertEqual(payload["result_summary"]["blocking_reason_detail"]["runtime_category"], "environment_missing")
            self.assertEqual(payload["result_summary"]["inspection_hint"]["artifact_key"], "probe")
            self.assertEqual(payload["probe"]["status"], "runtime_missing")
            self.assertEqual(payload["runtime_evidence"]["generated_script_probe"]["status"], "runtime_missing")
            self.assertTrue(payload["runtime_evidence"]["probe_policy"]["auto_run"])
            self.assertEqual(payload["runtime_evidence"]["probe_policy"]["current_run_status"], "runtime_missing")
            self.assertIn("provides `cupy`", payload["next_action"])
            self.assertIn("rerun the probe command", payload["next_action"])
            self.assertEqual(payload["result_summary"]["execution_status"], "runtime_missing")
            self.assertEqual(payload["result_summary"]["product_status"], "generated_runtime_blocked")
            self.assertEqual(payload["result_summary"]["workflow_outcome"]["phase"], "generated_and_probed")
            self.assertEqual(payload["result_summary"]["runtime_diagnostic"]["category"], "environment_missing")
            self.assertEqual(
                Path(payload["result_summary"]["artifacts"]["probe"]).resolve(),
                output.with_suffix(".probe.json").resolve(),
            )
            self.assertIn("current generated script and runtime probe result", payload["backend_diagnostic"]["next_step"])
            self.assertNotIn("clarification result", payload["backend_diagnostic"]["next_step"])
            probe_artifact = output.with_suffix(".probe.json")
            self.assertTrue(probe_artifact.exists())
            persisted_probe = json.loads(probe_artifact.read_text(encoding="utf-8"))
            self.assertEqual(persisted_probe["status"], "runtime_missing")

    def test_cli_run_can_report_runtime_proved_after_probe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--runtime-probe",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            probe_payload = {
                "status": "ok",
                "runtime_level": "runtime_proved",
                "evidence_levels": {
                    "runtime_ready": True,
                    "runtime_proved": True,
                    "current_level": "runtime_proved",
                    "blockers": [],
                },
            }
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with patch("pyquda_agent.app.build_generated_probe", return_value=probe_payload):
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["product_status"], "runtime_proved")
            self.assertEqual(payload["execution_status"], "runtime_proved")
            self.assertEqual(payload["workflow_outcome"]["phase"], "generated_and_probed")
            self.assertTrue(payload["workflow_outcome"]["generation_succeeded"])
            self.assertTrue(payload["workflow_outcome"]["execution_attempted"])
            self.assertTrue(payload["workflow_outcome"]["execution_succeeded"])
            self.assertEqual(payload["workflow_outcome"]["runtime_probe_status"], "ok")
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertEqual(payload["execution_result"]["phase"], "runtime_proved")
            self.assertTrue(payload["execution_result"]["attempted"])
            self.assertTrue(payload["execution_result"]["succeeded"])
            self.assertFalse(payload["execution_result"]["blocked"])
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "runtime_proved")
            self.assertEqual(payload["runtime_diagnostic"]["status"], "runtime_proved")
            self.assertEqual(payload["runtime_diagnostic"]["category"], "runtime_proved")
            self.assertIsNone(payload["primary_action"])
            self.assertEqual(payload["action_queue"], [])
            self.assertEqual(payload["run_overview"]["blocking_kind"], "none")
            self.assertIsNone(payload["run_overview"]["primary_action_kind"])
            self.assertIsNone(payload["blocking_reason"])
            self.assertIsNone(payload["blocking_reason_detail"])
            self.assertIn("runtime proof succeeded", payload["terminal_message"]["headline"].lower())
            self.assertIsNone(payload["terminal_message"]["recommended_command"])
            self.assertEqual(payload["result_summary"]["product_status"], "runtime_proved")
            self.assertEqual(payload["result_summary"]["execution_status"], "runtime_proved")
            self.assertEqual(payload["result_summary"]["runtime_diagnostic"]["category"], "runtime_proved")
            self.assertTrue(payload["runtime_evidence"]["probe_policy"]["auto_run"])
            self.assertEqual(payload["runtime_evidence"]["probe_policy"]["current_run_status"], "ok")
            self.assertEqual(payload["probe"]["status"], "ok")
            probe_artifact = output.with_suffix(".probe.json")
            self.assertTrue(probe_artifact.exists())
            persisted_probe = json.loads(probe_artifact.read_text(encoding="utf-8"))
            self.assertEqual(persisted_probe["status"], "ok")

    def test_cli_run_records_probe_driver_failure_without_losing_generated_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--backend",
                "api",
                "--no-interactive",
                "--runtime-probe",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch(
                    "pyquda_agent.app.build_llm_backend",
                    return_value=(
                        None,
                        {
                            "requested_backend": "api",
                            "configured": False,
                            "backend_name": None,
                            "fallback": True,
                            "fallback_reason": "mocked api fallback",
                        },
                    ),
                ):
                    with patch("pyquda_agent.app.build_generated_probe", side_effect=RuntimeError("mock probe harness failure")):
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["product_status"], "generated_runtime_blocked")
            self.assertEqual(payload["execution_status"], "probe_driver_failed")
            self.assertEqual(payload["workflow_outcome"]["runtime_probe_status"], "probe_driver_failed")
            self.assertTrue(payload["workflow_outcome"]["execution_attempted"])
            self.assertFalse(payload["workflow_outcome"]["execution_succeeded"])
            self.assertEqual(payload["generation_result"]["phase"], "generated")
            self.assertEqual(payload["execution_result"]["phase"], "probe_driver_failed")
            self.assertTrue(payload["execution_result"]["attempted"])
            self.assertTrue(payload["execution_result"]["blocked"])
            self.assertEqual(payload["delivery_status"]["execution"]["phase"], "probe_driver_failed")
            self.assertIn("probe harness failed", payload["delivery_status"]["execution"]["headline"].lower())
            self.assertEqual(payload["runtime_diagnostic"]["status"], "probe_driver_failed")
            self.assertEqual(payload["runtime_diagnostic"]["category"], "probe_driver_failed")
            self.assertIn("probe artifact", payload["runtime_diagnostic"]["next_step"].lower())
            self.assertIn("rerun the probe command", payload["runtime_diagnostic"]["next_step"].lower())
            self.assertEqual(payload["runtime_diagnostic"]["recommended_fix"], payload["runtime_diagnostic"]["next_step"])
            self.assertEqual(payload["runtime_diagnostic"]["retry_command"], payload["probe_hint"])
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "runtime_blocked")
            self.assertIn("mock probe harness failure", payload["capability_summary"]["runtime"]["blockers"][0])
            self.assertEqual(payload["primary_action"]["kind"], "retry_probe")
            self.assertIn("probe harness failed", payload["terminal_message"]["headline"].lower())
            self.assertIn("probe artifact", payload["terminal_message"]["detail"].lower())
            self.assertIn("harness-side failure", payload["action_queue"][0]["title"].lower())
            self.assertEqual(payload["action_queue"][1]["kind"], "runtime_fix")
            self.assertEqual(
                payload["action_queue"][1]["title"],
                "Inspect the probe artifact and repair the harness-side failure",
            )
            self.assertEqual(payload["action_queue"][1]["action_state"], "conditional")
            self.assertFalse(payload["action_queue"][1]["actionable"])
            self.assertIsNone(payload["action_queue"][1]["command"])
            self.assertIn("probe artifact", payload["action_queue"][1]["guidance"].lower())
            self.assertIn("harness-side failure", payload["action_queue"][1]["actionability_reason"].lower())
            self.assertEqual(payload["run_overview"]["blocking_kind"], "probe_driver")
            self.assertIn("probe harness failed", payload["result_summary"]["blocking_reason"].lower())
            self.assertEqual(payload["result_summary"]["blocking_reason_detail"]["category"], "runtime_probe_harness_failed")
            self.assertEqual(payload["result_summary"]["blocking_reason_detail"]["runtime_category"], "probe_driver_failed")
            self.assertEqual(payload["result_summary"]["inspection_hint"]["artifact_key"], "probe")
            self.assertTrue(Path(payload["generation"]["output_path"]).exists())
            self.assertEqual(payload["runtime_evidence"]["generated_script_probe"]["status"], "probe_driver_failed")
            self.assertTrue(payload["runtime_evidence"]["probe_policy"]["current_run_attempted"])
            self.assertEqual(payload["probe"]["probe_driver_error"]["type"], "RuntimeError")
            self.assertEqual(payload["probe"]["status"], "probe_driver_failed")
            self.assertIn("probe artifact", payload["next_action"].lower())
            probe_artifact = output.with_suffix(".probe.json")
            self.assertTrue(probe_artifact.exists())
            persisted_probe = json.loads(probe_artifact.read_text(encoding="utf-8"))
            self.assertEqual(persisted_probe["status"], "probe_driver_failed")

    def test_cli_run_complete_mode_stops_for_missing_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertIn("mass", payload["missing_fields"])

    def test_cli_run_explicit_meson_spec_request_routes_to_supported_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute meson spectroscopy correlators",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(
                payload["physics"]["confirmed_interpretation"]["target_id"],
                "meson_spectrum_correlator",
            )
            self.assertEqual(payload["workflow_match"]["workflow_target"], "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1")
            self.assertEqual(payload["task"]["workflow_id"], "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1")
            self.assertEqual(payload["task"]["source_type"], "wall")
            self.assertEqual(payload["task"]["sink_type"], "local")
            self.assertEqual(payload["task"]["gamma_insertions"], ["gamma5_gamma5", "gamma4gamma5_gamma4gamma5"])
            self.assertEqual(payload["task"]["momentum_projection"], "explicit")
            self.assertEqual(len(payload["task"]["momenta"]), 123)
            self.assertIn("mass", payload["missing_fields"])
            self.assertNotIn("generation", payload)
            self.assertEqual(payload["result_summary"]["status"], "needs_input")
            self.assertEqual(payload["result_summary"]["missing_fields_count"], len(payload["missing_fields"]))
            self.assertEqual(payload["result_summary"]["missing_fields_preview"][0], "mass")
            self.assertIn("mass=0.09253", payload["set_hint"])
            self.assertIn("xi_0=4.8965", payload["set_hint"])
            self.assertIn("Resolve missing implementation/runtime fields", payload["next_action"])
            self.assertEqual(payload["workflow_outcome"]["blockers"][0], "mass")
            self.assertIn("Current batch: mass, xi_0, nu", payload["next_action"])
            self.assertNotIn("Next question:", payload["next_action"])
            self.assertNotIn("Example answer:", payload["next_action"])

    def test_cli_run_relative_output_paths_stay_under_runtime_output_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda = root / "PyQUDA"
            explicit_output = root / "generated.py"
            index_path = root / "data" / "pyquda_index.json"

            (root / "data").mkdir(parents=True)
            (root / "docs").mkdir(parents=True)
            (pyquda / "examples").mkdir(parents=True)
            (pyquda / "tests").mkdir(parents=True)
            (pyquda / "pyquda_utils").mkdir(parents=True)
            (pyquda / "pyquda_utils" / "io").mkdir(parents=True)
            (root / "docs" / "RUNNABLE_PION_2PT_SPEC.md").write_text("pion helper", encoding="utf-8")
            (root / "docs" / "TASK_SCHEMAS.md").write_text("task schema", encoding="utf-8")
            (root / "docs" / "RUN_WORKFLOW.md").write_text("workflow", encoding="utf-8")
            (pyquda / "examples" / "3_Pion_Proton_2pt.py").write_text("pion example", encoding="utf-8")
            (pyquda / "examples" / "5_Pion_Dispersion.py").write_text("dispersion", encoding="utf-8")
            (pyquda / "tests" / "test_mesonspec.py").write_text("mesonspec", encoding="utf-8")
            (pyquda / "tests" / "test_io.py").write_text("io test", encoding="utf-8")
            (pyquda / "pyquda_utils" / "source.py").write_text("wall source", encoding="utf-8")
            (pyquda / "pyquda_utils" / "core.py").write_text("invert core", encoding="utf-8")
            (pyquda / "pyquda_utils" / "gamma.py").write_text("gamma", encoding="utf-8")
            (pyquda / "pyquda_utils" / "io" / "__init__.py").write_text("readQIOGauge", encoding="utf-8")
            index_path.write_text(
                json.dumps({"repo_root": str(pyquda.resolve()), "summary": {"file_count": 3}}),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(explicit_output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(payload["task"]["script_output_path"], str((root / "outputs" / "run_pion.py").resolve()))
            self.assertEqual(payload["task"]["correlator_output_path"], str((root / "outputs" / "pion.npy").resolve()))
            self.assertIn(str((root / "outputs" / "run_pion.py").resolve()), payload["resume_hint"])
            self.assertTrue(Path(payload["task_artifact"]).exists())

    def test_cli_run_exposes_index_repo_mismatch_in_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            other_repo = root / "OtherPyQUDA"
            other_repo.mkdir(parents=True)
            index_path.write_text(
                json.dumps({"repo_root": str(other_repo.resolve()), "summary": {"file_count": 88}}),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["context"]["index_summary"]["file_count"], 88)
            self.assertEqual(payload["context"]["index_provenance"]["status"], "repo_mismatch")
            self.assertEqual(payload["result_summary"]["index_provenance"]["status"], "repo_mismatch")
            self.assertEqual(payload["context"]["index_provenance"]["requested_repo_root"], str(pyquda.resolve()))
            self.assertEqual(payload["context"]["index_provenance"]["indexed_repo_root"], str(other_repo.resolve()))

    def test_cli_run_summary_output_keeps_index_repo_mismatch_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            other_repo = root / "OtherPyQUDA"
            other_repo.mkdir(parents=True)
            index_path.write_text(
                json.dumps({"repo_root": str(other_repo.resolve()), "summary": {"file_count": 88}}),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=0.09253 xi_0=4.8965 nu=0.86679 coeff_t=0.8549165664 "
                "coeff_r=2.32582045 tol=1e-12 maxiter=1000 gauge fixed cluster_launch=local outputs/pion.npy "
                "outputs/run_pion.py resource_path=.cache/quda",
                "--dry-run",
                "--no-interactive",
                "--result-format",
                "summary",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["index_provenance"]["status"], "repo_mismatch")
            self.assertEqual(payload["index_provenance"]["requested_repo_root"], str(pyquda.resolve()))
            self.assertEqual(payload["index_provenance"]["indexed_repo_root"], str(other_repo.resolve()))

    def test_cli_run_set_field_applies_noninteractive_answer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--set",
                "mass=0.09253",
                "--set",
                "source_timeslices=0",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task"]["mass"], 0.09253)
            self.assertEqual(payload["task"]["source_timeslices"], [0])
            self.assertNotIn("mass", payload["missing_fields"])
            self.assertNotIn("source_timeslices", payload["missing_fields"])

    def test_cli_run_reply_applies_answers_in_pending_question_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "pion",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "pion_two_point_correlator")
            self.assertEqual(payload["workflow_match"]["workflow_target"], "pion_2pt_chroma_wall_local_zero_momentum_npy_v1")

    def test_cli_run_reply_can_fill_first_task_questions_after_physics_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "pion",
                "--reply",
                "0",
                "--reply",
                "yes",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task"]["source_timeslices"], [0])
            self.assertTrue(payload["task"]["gauge_fixed"])
            self.assertNotIn("source_timeslices", payload["missing_fields"])
            self.assertNotIn("gauge_fixed", payload["missing_fields"])

    def test_summary_preview_examples_are_capped_at_three_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "pion",
                "--reply",
                "0",
                "--reply",
                "yes",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            summary = payload["result_summary"]
            self.assertEqual(len(summary["pending_question_preview"]), 3)
            self.assertEqual(len(summary["pending_set_examples"]), 3)
            self.assertEqual(len(summary["pending_reply_examples"]), 3)
            self.assertEqual(
                [item["field_name"] for item in summary["pending_question_preview"]],
                ["mass", "xi_0", "nu"],
            )
            self.assertEqual(summary["clarification_status"]["mode"], "task_fields")
            self.assertEqual(summary["clarification_status"]["question_batch_total"], 7)
            self.assertTrue(summary["clarification_status"]["preview_truncated"])
            self.assertEqual(summary["clarification_status"]["preview_fields"], ["mass", "xi_0", "nu"])
            self.assertEqual(summary["clarification_status"]["question_batch_fields"][:4], ["mass", "xi_0", "nu", "coeff_t"])
            self.assertEqual(summary["clarification_status"]["field_groups"][0]["group_id"], "clover_solver_parameters")
            self.assertTrue(summary["clarification_status"]["field_groups"][0]["complete_in_batch"])
            self.assertEqual(summary["clarification_status"]["recommended_answer_mode"], "set")
            self.assertIn("--set clover_solver_parameters=", summary["clarification_status"]["field_groups"][0]["set_example"])
            self.assertEqual(len(summary["pending_group_set_examples"]), 1)
            self.assertIn("--set clover_solver_parameters=", summary["pending_group_set_examples"][0])
            self.assertIn("--set clover_solver_parameters=", summary["group_set_hint"])
            self.assertIn("mass=0.09253", summary["set_hint"])
            self.assertIn("xi_0=4.8965", summary["set_hint"])
            self.assertIn("nu=0.86679", summary["set_hint"])
            self.assertIn("coeff_t=0.8549165664", summary["set_hint"])
            self.assertIn("coeff_r=2.32582045", summary["set_hint"])
            self.assertIn("solver_tol=1e-12", summary["set_hint"])
            self.assertIn("solver_maxiter=1000", summary["set_hint"])
            self.assertIn("--reply 0.09253", summary["reply_hint"])
            self.assertIn("--reply 4.8965", summary["reply_hint"])
            self.assertIn("--reply 0.86679", summary["reply_hint"])
            self.assertIn("--reply 0.8549165664", summary["reply_hint"])
            self.assertIn("--reply 2.32582045", summary["reply_hint"])
            self.assertIn("--reply 1e-12", summary["reply_hint"])
            self.assertIn("--reply 1000", summary["reply_hint"])
            self.assertEqual(summary["action_queue"][0]["kind"], "continue_by_set")
            self.assertIn("[clover solver parameters]", summary["action_queue"][0]["title"])
            self.assertIn("--set clover_solver_parameters=", summary["action_queue"][0]["command"])
            self.assertEqual(summary["action_queue"][1]["kind"], "continue_by_reply")

    def test_cli_run_summary_exposes_lattice_geometry_grouped_set_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "pion",
                "--reply",
                "0",
                "--reply",
                "yes",
                "--set",
                "clover_solver_parameters=0.09253,4.8965,0.86679,0.8549165664,2.32582045,1e-12,1000",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            summary = payload
            self.assertEqual(summary["clarification_status"]["field_groups"][0]["group_id"], "lattice_geometry")
            self.assertTrue(summary["clarification_status"]["field_groups"][0]["complete_in_batch"])
            self.assertEqual(summary["clarification_status"]["recommended_answer_mode"], "set")
            self.assertIn("lattice_geometry=", summary["clarification_status"]["field_groups"][0]["set_example"])
            self.assertIn("lattice_geometry=", summary["pending_group_set_examples"][0])
            self.assertIn("lattice_geometry=", summary["group_set_hint"])
            self.assertEqual(summary["action_queue"][0]["kind"], "continue_by_set")
            self.assertIn("[lattice geometry]", summary["action_queue"][0]["title"])
            self.assertIn("lattice_geometry=", summary["action_queue"][0]["command"])

    def test_cli_run_reply_rejects_answer_that_does_not_fit_pending_question(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            stderr = io.StringIO()

            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "pion",
                "--reply",
                "gauge",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as exc:
                            main(argv)
            self.assertEqual(exc.exception.code, 2)
            error_text = stderr.getvalue()
            self.assertIn("请提供 source timeslice，例如 0。", error_text)
            self.assertIn("Example reply: '0'", error_text)

    def test_cli_run_save_session_persists_questions_and_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt from gauge /tmp/cfg_0001.lime with clover "
                "wall source local sink zero momentum timeslice 0 lattice size 24 24 24 72 "
                "grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--save-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            saved = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertIn("implementation_plan", saved)
            self.assertIn("physics_target", saved)
            self.assertIn("field_resolution", saved["implementation_plan"])
            self.assertIn("clarification_trace", saved["implementation_plan"])
            self.assertEqual(saved["draft"]["field_sources"]["fermion_action"], "parsed")
            self.assertIn(str(session_path), payload["set_hint"])

    def test_cli_run_set_hint_uses_explicit_session_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "custom-session.json"

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--save-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertIn(str(session_path), payload["resume_hint"])
            self.assertIn(str(session_path), payload["set_hint"])

    def test_cli_run_physics_confirmation_set_hint_uses_natural_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pi meson two-point",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertEqual(payload["result_summary"]["missing_fields_count"], 1)
            self.assertEqual(payload["result_summary"]["missing_fields_preview"], ["confirmed_target_id"])
            self.assertEqual(payload["result_summary"]["clarification_status"]["mode"], "physics_confirmation")
            self.assertEqual(payload["result_summary"]["clarification_status"]["question_batch_fields"], ["confirmed_target_id"])
            self.assertFalse(payload["result_summary"]["clarification_status"]["preview_truncated"])
            self.assertIn("confirmed_target_id=pion", payload["set_hint"])
            self.assertIn("--set confirmed_target_id=pion", payload["result_summary"]["pending_set_examples"][0])
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "pion")
            self.assertIn("--reply pion", payload["result_summary"]["pending_reply_examples"][0])
            self.assertIn("Confirm the physics target", payload["next_action"])
            self.assertIn("Candidates: pion_two_point_correlator", payload["next_action"])
            self.assertNotIn("候选公式/operator/假设包括", payload["next_action"])

    def test_clarification_trace_is_persisted_when_answers_are_applied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"

            stdout = io.StringIO()
            argv = [
                "run",
                "generate complete runnable pion 2pt outputs/pion.npy outputs/run_pion.py",
                "--backend",
                "codex",
                "--dry-run",
                "--interactive",
                "--max-questions",
                "1",
                "--save-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with patch("builtins.input", side_effect=["0.09253"]):
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            saved = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertTrue(saved["implementation_plan"]["clarification_trace"])
            self.assertEqual(saved["implementation_plan"]["clarification_trace"][0]["field_name"], "source_timeslices")

    def test_rough_pion_request_needs_input_instead_of_unsupported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertNotEqual(payload["status"], "unsupported")
            self.assertEqual(payload["task"]["source_type"], "wall")
            self.assertEqual(payload["task"]["field_sources"]["source_type"], "fixed")
            self.assertNotIn("source_type", payload["task"]["user_confirmed_fields"])
            self.assertNotIn("source_type", payload["task"]["parser_guesses"])
            self.assertIn("mass", payload["missing_fields"])

    def test_generic_pyquda_request_enters_capability_chooser_instead_of_meson_only_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertNotEqual(payload["status"], "unsupported")
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertEqual(payload["result_summary"]["clarification_status"]["mode"], "physics_confirmation")
            self.assertIn("grounded workflow family 分为两类", payload["questions"][0]["prompt"])
            self.assertIn("Gauge/solver utilities:", payload["questions"][0]["prompt"])
            self.assertIn("quark propagator", payload["questions"][0]["prompt"])
            self.assertIn("wilson flow", payload["questions"][0]["prompt"].lower())
            self.assertIn("stout smear、ape smear 或 hyp smear", payload["questions"][0]["prompt"])
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["field_name"], "confirmed_target_id")
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "pion")

    def test_hadron_request_enters_hadron_channel_clarification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute a hadron correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "hadron_two_point_correlator_unspecified")
            self.assertEqual(payload["result_summary"]["clarification_status"]["mode"], "physics_confirmation")
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "meson")
            self.assertIn("还没有说明是 meson 还是 baryon", payload["questions"][0]["prompt"])
            self.assertIn("如果你要先走 meson 侧澄清，请回答 meson", payload["questions"][0]["prompt"])
            self.assertIn("如果你要先走 baryon / nucleon 侧澄清，请回答 baryon", payload["questions"][0]["prompt"])
            self.assertEqual(
                [item["target_id"] for item in payload["physics"]["candidate_targets"]],
                [
                    "hadron_two_point_correlator_unspecified",
                    "meson_two_point_correlator_unspecified",
                    "baryon_two_point_correlator_unspecified",
                    "pion_two_point_correlator",
                    "proton_two_point_correlator",
                ],
            )
            self.assertTrue(
                any(item["proposal_id"] == "hadron_operator_needs_channel_choice" for item in payload["physics"]["formula_proposals"])
            )
            self.assertEqual(
                payload["physics_workflow_preview"][0]["grounded_workflow_targets"],
                [
                    "pion_2pt_chroma_wall_local_zero_momentum_npy_v1",
                    "pion_dispersion_chroma_point_momentum_npy_v1",
                    "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
                    "rho_vector_chroma_wall_local_zero_momentum_npy_v1",
                    "proton_2pt_chroma_wall_local_zero_momentum_npy_v1",
                ],
            )

    def test_mixed_meson_baryon_request_stays_at_hadron_level(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I need a nucleon or meson correlator but I am not sure which one",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "hadron_two_point_correlator_unspecified")
            self.assertEqual(
                [item["target_id"] for item in payload["physics"]["candidate_targets"]],
                [
                    "hadron_two_point_correlator_unspecified",
                    "meson_two_point_correlator_unspecified",
                    "baryon_two_point_correlator_unspecified",
                ],
            )
            self.assertIn("multiple hadron-channel families", payload["physics"]["candidate_targets"][0]["summary"])
            self.assertIn("如果你要先走 meson 侧澄清，请回答 meson", payload["questions"][0]["prompt"])
            self.assertIn("如果你要先走 baryon / nucleon 侧澄清，请回答 baryon", payload["questions"][0]["prompt"])
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "meson")

    def test_mixed_specific_meson_spectrum_or_proton_request_surfaces_specific_branch_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I am not sure if I need a meson spectrum or proton correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "hadron_two_point_correlator_unspecified")
            self.assertEqual(
                [item["target_id"] for item in payload["physics"]["candidate_targets"]],
                [
                    "hadron_two_point_correlator_unspecified",
                    "meson_spectrum_correlator",
                    "proton_two_point_correlator",
                ],
            )
            self.assertTrue(
                any(item["proposal_id"] == "meson_spec_gamma5_wall_momentum_family" for item in payload["physics"]["formula_proposals"])
            )
            self.assertTrue(
                any(item["proposal_id"] == "proton_nucleon_gamma5_twopt" for item in payload["physics"]["formula_proposals"])
            )
            self.assertEqual(
                [item["proposal_id"] for item in payload["result_summary"]["physics_formula_preview"]],
                [
                    "hadron_operator_needs_channel_choice",
                    "meson_spec_gamma5_wall_momentum_family",
                    "meson_spec_gamma4gamma5_wall_momentum_family",
                    "proton_nucleon_gamma5_twopt",
                ],
            )
            self.assertIn("请先确认更具体的 hadron target", payload["questions"][0]["prompt"])
            self.assertIn("请直接回答 meson spectrum / proton", payload["questions"][0]["prompt"])
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "meson spectrum")

    def test_mixed_pion_or_proton_request_surfaces_proton_formula_in_preview(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I am not sure if I need pion or proton correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "hadron_two_point_correlator_unspecified")
            self.assertEqual(
                [item["proposal_id"] for item in payload["result_summary"]["physics_formula_preview"]],
                [
                    "hadron_operator_needs_channel_choice",
                    "pion_pseudoscalar_gamma5_twopt",
                    "proton_nucleon_gamma5_twopt",
                    "meson_operator_needs_channel_choice",
                ],
            )
            self.assertIn("请先确认更具体的 hadron target", payload["questions"][0]["prompt"])
            self.assertIn("请直接回答 pion / proton", payload["questions"][0]["prompt"])
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "pion")

    def test_hadron_level_reply_mesons_advances_to_meson_clarification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I need a nucleon or meson correlator but I am not sure which one",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "meson",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "meson_two_point_correlator_unspecified")
            self.assertIsNone(payload["physics"]["confirmed_interpretation"])
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertIn("当前支持 pion two-point correlator", payload["questions"][0]["prompt"])
            self.assertNotIn("还没有说明是 meson 还是 baryon", payload["questions"][0]["prompt"])

    def test_hadron_level_reply_baryon_advances_to_baryon_clarification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I need a nucleon or meson correlator but I am not sure which one",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "baryon",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "baryon_two_point_correlator_unspecified")
            self.assertIsNone(payload["physics"]["confirmed_interpretation"])
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertIn("当前本地可运行 baryon workflow 只有 proton two-point correlator", payload["questions"][0]["prompt"])
            self.assertNotIn("还没有说明是 meson 还是 baryon", payload["questions"][0]["prompt"])

    def test_hadron_level_reply_mesonspectrum_branch_keeps_specific_candidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "I am not sure if I need a meson spectrum or proton correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "meson",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "meson_spectrum_correlator")
            self.assertIn("当前推断目标是 meson spectrum correlator", payload["questions"][0]["prompt"])

    def test_bare_propagator_request_enters_quark_family_clarification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate a propagator script",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "quark_propagator")
            self.assertEqual(payload["result_summary"]["clarification_status"]["mode"], "physics_confirmation")
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "quark propagator")
            self.assertIn("当前本地有两条可运行分支", payload["questions"][0]["prompt"])
            self.assertIn("gaussianSmear(rho=2.0, n_steps=5)", payload["questions"][0]["prompt"])
            self.assertTrue(
                any(item["proposal_id"] == "quark_propagator_point_source_clover" for item in payload["physics"]["formula_proposals"])
            )
            self.assertTrue(
                any(item["proposal_id"] == "quark_propagator_gaussian_shell_source_clover" for item in payload["physics"]["formula_proposals"])
            )
            self.assertEqual(
                payload["physics_workflow_preview"][0]["grounded_workflow_targets"],
                [
                    "quark_propagator_chroma_point_hdf5_v1",
                    "quark_propagator_gaussian_shell_chroma_hdf5_v1",
                ],
            )

    def test_bare_propagator_request_can_select_gaussian_shell_branch_via_reply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please generate a propagator script from gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 "
                "grid 1 1 1 2 mass=-0.2770 xi_0=1.0 nu=1.0 coeff_t=1.160920226 coeff_r=1.160920226 "
                "tol=1e-12 maxiter=1000 source timeslice 0 outputs/gaussian_prop.h5 outputs/run_gaussian_prop.py "
                "resource_path=.cache/quda cluster_launch=local",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--reply",
                "gaussian shell propagator",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "dry_run")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "quark_propagator")
            self.assertEqual(payload["physics"]["clarified_fields"]["source_smearing_kind"], "gaussian_shell")
            self.assertEqual(payload["workflow_match"]["workflow_target"], "quark_propagator_gaussian_shell_chroma_hdf5_v1")
            self.assertEqual(payload["result_summary"]["workflow_target"], "quark_propagator_gaussian_shell_chroma_hdf5_v1")
            self.assertEqual(payload["task"]["source_smearing_kind"], "gaussian_shell")
            self.assertIn("source_smearing_kind", payload["task"]["field_sources"])
            self.assertEqual(payload["result_summary"]["physics_target"], "quark_propagator")
            self.assertEqual(payload["missing_fields"], [])

    def test_uncertain_quark_branch_request_stays_in_physics_confirmation_until_branch_confirmed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute a quark propagator but I am not sure whether I need point or gaussian shell",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "quark_propagator")
            self.assertIsNone(payload["physics"]["confirmed_interpretation"])
            self.assertEqual(payload["result_summary"]["clarification_status"]["mode"], "physics_confirmation")
            self.assertEqual(payload["result_summary"]["pending_question_preview"][0]["answer_example"], "quark propagator")
            self.assertIn("当前本地有两条可运行分支", payload["questions"][0]["prompt"])
            self.assertIn("gaussian shell propagator", payload["questions"][0]["prompt"])
            self.assertNotIn("source timeslice", payload["questions"][0]["prompt"])

    def test_uncertain_meson_spec_request_stays_in_physics_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for meson spectrum but I am not sure which gamma insertion to use",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["missing_fields"], ["confirmed_target_id"])
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "meson_spectrum_correlator")
            self.assertIsNone(payload["physics"]["confirmed_interpretation"])
            self.assertEqual(payload["result_summary"]["clarification_status"]["mode"], "physics_confirmation")
            self.assertIn("gamma5 / gamma4gamma5 插入族", payload["questions"][0]["prompt"])
            self.assertTrue(
                any(item["proposal_id"] == "meson_spec_gamma5_wall_momentum_family" for item in payload["physics"]["formula_proposals"])
            )
            self.assertTrue(
                any(item["proposal_id"] == "meson_spec_gamma4gamma5_wall_momentum_family" for item in payload["physics"]["formula_proposals"])
            )

    def test_axial_meson_request_prefers_meson_spec_clarification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for axial meson correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "meson_spectrum_correlator")
            self.assertNotEqual(payload["status"], "unsupported")
            self.assertIn("meson_spectrum_correlator", [item["target_id"] for item in payload["physics"]["candidate_targets"]])
            self.assertTrue(any(item["proposal_id"].startswith("meson_spec_") for item in payload["physics"]["formula_proposals"]))
            self.assertTrue(payload["physics_workflow_preview"])
            meson_spec_preview = next(
                item
                for item in payload["physics_workflow_preview"]
                if item["target_id"] == "meson_spectrum_correlator"
            )
            self.assertIn(
                "meson_spec_chroma_wall_gamma5_axial_mom2max9_npy_v1",
                meson_spec_preview["grounded_workflow_targets"],
            )
            self.assertIn("meson spectrum", payload["terminal_message"]["recommended_command"])

    def test_pseudoscalar_meson_request_prefers_pion_clarification(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "write a simple PyQUDA script for pseudoscalar meson correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["inferred_interpretation"]["target_id"], "pion_two_point_correlator")
            self.assertNotEqual(payload["status"], "unsupported")
            self.assertIn("meson_spectrum_correlator", [item["target_id"] for item in payload["physics"]["candidate_targets"]])
            self.assertIn("pion", payload["terminal_message"]["recommended_command"])

    def test_rough_proton_existing_propagator_request_needs_input_instead_of_unsupported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the proton two-point correlator from existing propagator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertNotEqual(payload["status"], "unsupported")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "proton_two_point_correlator")
            self.assertEqual(payload["workflow_match"]["workflow_target"], "proton_2pt_existing_propagator_local_zero_momentum_npy_v1")
            self.assertIn("propagator_paths", payload["missing_fields"])
            self.assertIn("source_timeslices", payload["missing_fields"])
            self.assertEqual(payload["runtime_diagnostic"]["category"], "generation_incomplete")
            self.assertEqual(payload["runtime_diagnostic"]["runtime_level"], "structurally_grounded")
            self.assertEqual(payload["capability_summary"]["runtime"]["state"], "blocked_by_clarification")
            self.assertEqual(payload["capability_summary"]["runtime"]["level"], "structurally_grounded")

    def test_rough_meson_spec_existing_propagator_request_routes_to_grounded_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute meson spectroscopy correlators from existing propagator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "meson_spectrum_correlator")
            self.assertEqual(
                payload["workflow_match"]["workflow_target"],
                "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1",
            )
            self.assertIn("propagator_paths", payload["missing_fields"])
            self.assertIn("source_timeslices", payload["missing_fields"])
            self.assertEqual(payload["task"]["workflow_id"], "meson_spec_existing_propagator_local_gamma5_axial_mom2max9_npy_v1")
            self.assertEqual(payload["task"]["source_type"], "wall")
            self.assertEqual(payload["task"]["sink_type"], "local")
            self.assertEqual(payload["task"]["momentum_projection"], "explicit")
            self.assertEqual(payload["task"]["gauge_fixed"], False)

    def test_rough_rho_existing_propagator_request_routes_to_grounded_branch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the rho meson two-point correlator from existing propagator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertNotEqual(payload["status"], "unsupported")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "rho_vector_meson_correlator")
            self.assertEqual(
                payload["workflow_match"]["workflow_target"],
                "rho_vector_existing_propagator_local_zero_momentum_npy_v1",
            )
            self.assertIn("propagator_paths", payload["missing_fields"])
            self.assertIn("source_timeslices", payload["missing_fields"])
            self.assertEqual(payload["task"]["workflow_id"], "rho_vector_existing_propagator_local_zero_momentum_npy_v1")
            self.assertEqual(payload["task"]["source_type"], "wall")
            self.assertEqual(payload["task"]["sink_type"], "local")
            self.assertEqual(payload["task"]["momentum_projection"], "zero")
            self.assertEqual(payload["task"]["gauge_fixed"], False)
            self.assertEqual(payload["task"]["gamma_insertions"], ["gamma1_gamma1", "gamma2_gamma2", "gamma3_gamma3"])

    def test_rough_pion_dispersion_request_routes_to_second_supported_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute pion dispersion with nonzero momentum",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(payload["physics"]["confirmed_interpretation"]["target_id"], "pion_dispersion_correlator")
            self.assertEqual(payload["workflow_match"]["workflow_target"], "pion_dispersion_chroma_point_momentum_npy_v1")
            self.assertEqual(payload["task"]["source_type"], "point")
            self.assertEqual(payload["task"]["workflow_id"], "pion_dispersion_chroma_point_momentum_npy_v1")
            self.assertEqual(len(payload["task"]["momenta"]), 9)

    def test_cli_run_explicit_proton_request_routes_to_supported_third_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the proton two-point correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "needs_input")
            self.assertEqual(
                payload["physics"]["confirmed_interpretation"]["target_id"],
                "proton_two_point_correlator",
            )
            self.assertEqual(payload["workflow_match"]["workflow_target"], "proton_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertEqual(payload["task"]["workflow_id"], "proton_2pt_chroma_wall_local_zero_momentum_npy_v1")
            self.assertEqual(payload["task"]["stout_smear_steps"], 1)
            self.assertEqual(payload["task"]["multigrid_blocks"], [[6, 6, 6, 4], [4, 4, 4, 9]])
            self.assertIn("mass", payload["missing_fields"])

    def test_cli_run_uses_dynamic_default_output_for_dispersion_when_output_is_not_explicit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, _output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute pion dispersion with nonzero momentum",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("pyquda_agent.cli.DEFAULT_OUTPUT_PATH", root / "outputs" / "pion_2pt.py"):
                    with self._fallback_backend_patch():
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            expected_script = (root / "outputs" / "pion_dispersion.py").resolve()
            self.assertEqual(Path(payload["task"]["script_output_path"]).resolve(), expected_script)
            self.assertEqual(Path(payload["session_artifact"]).resolve(), expected_script.with_suffix(".session.json"))
            self.assertEqual(Path(payload["task_artifact"]).resolve(), expected_script.with_suffix(".task.json"))

    def test_cli_run_uses_dynamic_default_output_for_proton_when_output_is_not_explicit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, _output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the proton two-point correlator",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with patch("pyquda_agent.cli.DEFAULT_OUTPUT_PATH", root / "outputs" / "pion_2pt.py"):
                    with self._fallback_backend_patch():
                        with redirect_stdout(stdout):
                            exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            expected_script = (root / "outputs" / "proton_2pt.py").resolve()
            self.assertEqual(Path(payload["task"]["script_output_path"]).resolve(), expected_script)
            self.assertEqual(Path(payload["session_artifact"]).resolve(), expected_script.with_suffix(".session.json"))

    def test_cli_run_preserves_explicit_output_path_over_dynamic_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)

            stdout = io.StringIO()
            argv = [
                "run",
                "please compute pion dispersion with nonzero momentum",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(Path(payload["task"]["script_output_path"]).resolve(), output.resolve())

    def test_cli_run_resume_session_reuses_confirmed_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"
            session_payload = {
                "task_description": "old",
                "draft": {
                    "user_request": "old",
                    "task_type": "pion_2pt",
                    "workflow_id": None,
                    "start_from": None,
                    "has_existing_propagators": None,
                    "gauge_format": None,
                    "gauge_path": None,
                    "propagator_format": None,
                    "propagator_paths": [],
                    "lattice_size": [],
                    "grid_size": [],
                    "fermion_action": None,
                    "mass": None,
                    "xi_0": None,
                    "nu": None,
                    "coeff_t": None,
                    "coeff_r": None,
                    "solver_tol": None,
                    "solver_maxiter": None,
                    "multigrid_blocks": [],
                    "stout_smear_steps": None,
                    "stout_smear_rho": None,
                    "stout_smear_ndim": None,
                    "source_type": None,
                    "sink_type": None,
                    "momentum_projection": None,
                    "momenta": [],
                    "source_timeslices": [],
                    "gauge_fixed": None,
                    "correlator_output_format": None,
                    "correlator_output_path": None,
                    "resource_path": None,
                    "cluster_launch": None,
                    "script_output_path": None,
                    "script_style": None,
                    "notes": None,
                    "missing_fields": [],
                    "unsupported_reasons": [],
                    "field_sources": {},
                    "inherited_fields": {},
                    "user_confirmed_fields": {},
                    "inferred_fields": {},
                    "clarified_fields": {},
                    "parser_guesses": {},
                    "fixed_fields": {},
                    "unsupported_fields": {},
                    "chosen_workflow_target": None,
                    "pyquda_references": [],
                    "external_citations": [],
                },
                "asked_questions": [],
                "physics_target": interpret_request("please compute the pion two-point correlator").to_dict(),
                "confirmed_fields": {"resource_path": ".cache/quda", "cluster_launch": "slurm"},
                "rejected_options": {},
                "minimal_missing_fields": [],
                "workflow_match": None,
                "context_bundle": None,
                "implementation_plan": None,
            }
            session_path.write_text(json.dumps(session_payload), encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator from gauge /tmp/cfg_0001.lime lattice size 24 24 24 72 grid 1 1 1 2 outputs/pion.npy outputs/run_pion.py",
                "--backend",
                "codex",
                "--dry-run",
                "--no-interactive",
                "--resume-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task"]["resource_path"], ".cache/quda")
            self.assertEqual(payload["task"]["cluster_launch"], "slurm")
            self.assertEqual(payload["task"]["field_sources"]["resource_path"], "inherited")
            self.assertEqual(payload["implementation_plan"]["inherited_session_fields"]["resource_path"], ".cache/quda")

    def test_cli_run_resume_session_with_set_fields_updates_draft(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"
            session_payload = {
                "task_description": "old",
                "draft": parse_task_description("please compute the pion two-point correlator outputs/run.py").to_dict(),
                "asked_questions": [],
                "physics_target": interpret_request("please compute the pion two-point correlator").to_dict(),
                "confirmed_fields": {"resource_path": ".cache/quda"},
                "rejected_options": {},
                "minimal_missing_fields": [],
                "workflow_match": None,
                "context_bundle": None,
                "implementation_plan": None,
            }
            session_path.write_text(json.dumps(session_payload), encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--resume-session",
                str(session_path),
                "--set",
                "mass=0.09253",
                "--set",
                "source_timeslices=0",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task"]["mass"], 0.09253)
            self.assertEqual(payload["task"]["source_timeslices"], [0])
            self.assertEqual(payload["task"]["resource_path"], ".cache/quda")

    def test_cli_run_resume_session_with_grouped_set_fields_updates_draft(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"
            session_payload = {
                "task_description": "old",
                "draft": parse_task_description("please compute the pion two-point correlator outputs/run.py").to_dict(),
                "asked_questions": [],
                "physics_target": interpret_request("please compute the pion two-point correlator").to_dict(),
                "confirmed_fields": {"resource_path": ".cache/quda"},
                "rejected_options": {},
                "minimal_missing_fields": [],
                "workflow_match": None,
                "context_bundle": None,
                "implementation_plan": None,
            }
            session_path.write_text(json.dumps(session_payload), encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--resume-session",
                str(session_path),
                "--set",
                "clover_solver_parameters=0.09253,4.8965,0.86679,0.8549165664,2.32582045,1e-12,1000",
                "--set",
                "source_timeslices=0",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task"]["mass"], 0.09253)
            self.assertEqual(payload["task"]["xi_0"], 4.8965)
            self.assertEqual(payload["task"]["nu"], 0.86679)
            self.assertEqual(payload["task"]["coeff_t"], 0.8549165664)
            self.assertEqual(payload["task"]["coeff_r"], 2.32582045)
            self.assertEqual(payload["task"]["solver_tol"], 1e-12)
            self.assertEqual(payload["task"]["solver_maxiter"], 1000)
            self.assertEqual(payload["task"]["source_timeslices"], [0])
            self.assertEqual(payload["task"]["resource_path"], ".cache/quda")

    def test_cli_run_resume_session_with_grouped_lattice_geometry_updates_draft(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"
            session_payload = {
                "task_description": "old",
                "draft": parse_task_description("please compute the pion two-point correlator outputs/run.py").to_dict(),
                "asked_questions": [],
                "physics_target": interpret_request("please compute the pion two-point correlator").to_dict(),
                "confirmed_fields": {"resource_path": ".cache/quda"},
                "rejected_options": {},
                "minimal_missing_fields": [],
                "workflow_match": None,
                "context_bundle": None,
                "implementation_plan": None,
            }
            session_path.write_text(json.dumps(session_payload), encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--resume-session",
                str(session_path),
                "--set",
                "lattice_geometry=24,24,24,72;1,1,1,2",
                "--set",
                "source_timeslices=0",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["task"]["lattice_size"], [24, 24, 24, 72])
            self.assertEqual(payload["task"]["grid_size"], [1, 1, 1, 2])
            self.assertEqual(payload["task"]["source_timeslices"], [0])
            self.assertEqual(payload["task"]["resource_path"], ".cache/quda")

    def test_cli_run_resume_session_reuses_previous_pending_batch_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            session_path = root / "state.json"
            session_payload = {
                "task_description": "old",
                "draft": parse_task_description("please compute the pion two-point correlator outputs/run.py").to_dict(),
                "asked_questions": [],
                "physics_target": interpret_request("please compute the pion two-point correlator").to_dict(),
                "confirmed_fields": {"gauge_path": "/tmp/cfg_0001.lime"},
                "rejected_options": {},
                "minimal_missing_fields": ["gauge_fixed", "mass"],
                "workflow_match": None,
                "context_bundle": None,
                "implementation_plan": None,
            }
            session_path.write_text(json.dumps(session_payload), encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--summary-only",
                "--dry-run",
                "--no-interactive",
                "--resume-session",
                str(session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(stdout):
                        exit_code = main(argv)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(
                payload["clarification_status"]["question_batch_fields"][:2],
                ["gauge_fixed", "mass"],
            )
            self.assertEqual(
                [item["field_name"] for item in payload["pending_question_preview"][:2]],
                ["gauge_fixed", "mass"],
            )

    def test_cli_run_grouped_lattice_geometry_rejects_bad_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            stderr = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--set",
                "lattice_geometry=24,24,24;1,1,1,2",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as exc:
                            main(argv)
            self.assertEqual(exc.exception.code, 2)
            self.assertIn("expects exactly 4 lattice_size integers and 4 grid_size integers", stderr.getvalue())

    def test_cli_run_grouped_set_fields_reject_wrong_arity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            stderr = io.StringIO()
            argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--set",
                "clover_solver_parameters=0.09253,4.8965,0.86679",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as exc:
                            main(argv)
            self.assertEqual(exc.exception.code, 2)
            self.assertIn("expects 7 comma- or space-separated values", stderr.getvalue())

    def test_cli_run_resume_session_keeps_writing_to_explicit_session_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            pyquda, output, index_path = self._prepare_repo_fixture(root)
            custom_session_path = root / "custom" / "saved-state.json"

            first_stdout = io.StringIO()
            first_argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--save-session",
                str(custom_session_path),
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(first_stdout):
                        first_exit_code = main(first_argv)
            first_payload = json.loads(first_stdout.getvalue())
            resolved_session_path = str(custom_session_path.resolve())
            self.assertEqual(first_exit_code, 0)
            self.assertEqual(first_payload["session_artifact"], resolved_session_path)
            self.assertTrue(custom_session_path.exists())

            initial_saved = json.loads(custom_session_path.read_text(encoding="utf-8"))
            self.assertNotIn("source_timeslices", initial_saved["confirmed_fields"])

            second_stdout = io.StringIO()
            second_argv = [
                "run",
                "please compute the pion two-point correlator",
                "--dry-run",
                "--no-interactive",
                "--resume-session",
                str(custom_session_path),
                "--reply",
                "0",
                "--pyquda-repo",
                str(pyquda),
                "--output",
                str(output),
            ]
            with patch("pyquda_agent.app.DEFAULT_INDEX_PATH", index_path):
                with self._fallback_backend_patch():
                    with redirect_stdout(second_stdout):
                        second_exit_code = main(second_argv)
            second_payload = json.loads(second_stdout.getvalue())
            self.assertEqual(second_exit_code, 0)
            self.assertEqual(second_payload["session_artifact"], resolved_session_path)
            self.assertIn(resolved_session_path, second_payload["resume_hint"])
            self.assertIn(resolved_session_path, second_payload["reply_hint"])
            self.assertIn(resolved_session_path, second_payload["set_hint"])
            self.assertFalse((output.with_suffix(".session.json")).exists())

            updated_saved = json.loads(custom_session_path.read_text(encoding="utf-8"))
            self.assertEqual(updated_saved["confirmed_fields"]["source_timeslices"], [0])
            self.assertTrue(
                any(
                    item["field_name"] == "source_timeslices" and item.get("source") == "cli_reply"
                    for item in updated_saved["asked_questions"]
                )
            )


if __name__ == "__main__":
    unittest.main()
