import unittest

from pyquda_agent.backends.base import BackendInvocationError
from pyquda_agent.intent.prompts import build_intent_user_prompt
from pyquda_agent.intent.resolver import resolve_physics_target
from pyquda_agent.intent.interpreter import interpret_request


class _FakeBackend:
    name = "fake-backend"

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
        self.prompts = []
        self.timeout_seconds = timeout_seconds
        self.seen_timeouts = []

    def generate_text(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        self.prompts.append((system_prompt, user_prompt))
        self.seen_timeouts.append(self.timeout_seconds)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class IntentResolverTests(unittest.TestCase):
    def test_backend_is_invoked_when_configured(self):
        backend = _FakeBackend(
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
                  "convention": "Use a pseudoscalar pion operator.",
                  "provenance": "model_inference"
                }
              ],
              "notes": ["llm used"]
            }
            """
        )
        physics = resolve_physics_target(
            "write a simple PyQUDA script for pi meson two-point",
            backend=backend,
            backend_status={
                "requested_backend": "api",
                "configured": True,
                "backend_name": "api:test/model",
                "fallback": False,
                "fallback_reason": None,
            },
        )
        self.assertEqual(backend.calls, 1)
        self.assertTrue(physics.llm_assistance["used"])
        self.assertEqual(physics.normalized_request, "Compute the pion two-point correlator.")
        self.assertTrue(physics.knowledge_boundary["model_inference"]["used"])
        self.assertIsNotNone(backend.last_user_prompt)
        assert backend.last_user_prompt is not None
        self.assertIn('"external_citation_count": 2', backend.last_user_prompt)
        self.assertNotIn("bulava-2022-hadron-spectroscopy", backend.last_user_prompt)
        self.assertIsNone(physics.llm_assistance["intent_primary_timeout_seconds"])

    def test_fallback_is_marked_when_backend_is_unavailable(self):
        physics = resolve_physics_target(
            "please compute the pion two-point correlator",
            backend=None,
            backend_status={
                "requested_backend": "api",
                "configured": False,
                "backend_name": None,
                "fallback": True,
                "fallback_reason": "API backend requested but no --model was configured.",
            },
        )
        self.assertTrue(physics.llm_assistance["fallback"])
        self.assertIn("no --model", physics.llm_assistance["fallback_reason"])
        self.assertFalse(physics.llm_assistance["used"])
        self.assertFalse(physics.knowledge_boundary["true_online_lookup"]["implemented"])
        self.assertTrue(physics.knowledge_boundary["live_online_lookup"]["implemented"])

    def test_intent_prompt_uses_compact_rule_based_snapshot(self):
        physics = interpret_request("write a simple PyQUDA script for pi meson two-point")
        prompt = build_intent_user_prompt("write a simple PyQUDA script for pi meson two-point", physics)
        self.assertIn('"has_curated_local_citations": true', prompt)
        self.assertIn('"local_reference_count": 7', prompt)
        self.assertIn('"external_citation_count": 2', prompt)
        self.assertIn('"formula_proposal_count": 1', prompt)
        self.assertNotIn("howarth-giedt-2015-sigma", prompt)
        self.assertNotIn("examples/3_Pion_Proton_2pt.py", prompt)
        self.assertNotIn("tests/test_mesonspec.py", prompt)
        self.assertNotIn("pion_pseudoscalar_gamma5_twopt", prompt)
        self.assertNotIn("O_\\pi", prompt)
        self.assertLess(len(prompt), 3200)

    def test_ambiguous_intent_prompt_keeps_formula_detail(self):
        physics = interpret_request("I want a meson correlator script but I am not sure about the exact operator")
        prompt = build_intent_user_prompt("I want a meson correlator script but I am not sure about the exact operator", physics)
        self.assertIn("meson_operator_needs_channel_choice", prompt)
        self.assertIn("Because the request is ambiguous", prompt)

    def test_codex_concise_intent_prompt_is_smaller_for_unambiguous_rough_request(self):
        physics = interpret_request("write a simple PyQUDA script for pi meson two-point")
        normal_prompt = build_intent_user_prompt("write a simple PyQUDA script for pi meson two-point", physics)
        concise_prompt = build_intent_user_prompt(
            "write a simple PyQUDA script for pi meson two-point",
            physics,
            concise=True,
        )
        self.assertLess(len(concise_prompt), len(normal_prompt))
        self.assertNotIn('"formula_proposal_count": 1', concise_prompt)
        self.assertNotIn("Current supported targets include", concise_prompt)
        self.assertLess(len(concise_prompt), 2000)

    def test_codex_rough_single_target_uses_normalization_only_strategy(self):
        backend = _FakeBackend(
            """
            {
              "normalized_request": "Compute the pion two-point correlator.",
              "notes": ["normalization only path used"]
            }
            """
        )
        physics = resolve_physics_target(
            "write a simple PyQUDA script for pi meson two-point",
            backend=backend,
            backend_status={
                "requested_backend": "codex",
                "configured": True,
                "backend_name": "codex",
                "fallback": False,
                "fallback_reason": None,
            },
        )
        self.assertEqual(backend.calls, 1)
        self.assertTrue(physics.llm_assistance["used"])
        self.assertEqual(physics.llm_assistance["intent_strategy"], "normalization_only")
        self.assertEqual(physics.llm_assistance["intent_prompt_profile"], "normalization_only")
        self.assertEqual(physics.llm_assistance["stages_attempted"], ["rough_request_normalization"])
        self.assertEqual(physics.normalized_request, "Compute the pion two-point correlator.")
        self.assertEqual(physics.inferred_interpretation["target_id"], "pion_two_point_correlator")
        self.assertTrue(physics.knowledge_boundary["model_inference"]["used"])
        assert backend.last_user_prompt is not None
        self.assertIn("Keep the existing target guess", backend.last_user_prompt)
        self.assertIn('"candidate_target"', backend.last_user_prompt)
        self.assertLess(len(backend.last_user_prompt), 800)

    def test_codex_normalization_only_timeout_skips_recovery(self):
        backend = _SequenceBackend(
            [
                BackendInvocationError("initial timeout", category="timeout"),
            ]
        )
        physics = resolve_physics_target(
            "write a simple PyQUDA script for pi meson two-point",
            backend=backend,
            backend_status={
                "requested_backend": "codex",
                "configured": True,
                "backend_name": "codex",
                "fallback": False,
                "fallback_reason": None,
            },
        )
        self.assertEqual(backend.calls, 1)
        self.assertTrue(physics.llm_assistance["fallback"])
        self.assertEqual(physics.llm_assistance["fallback_category"], "timeout")
        self.assertEqual(physics.llm_assistance["intent_strategy"], "normalization_only")
        self.assertFalse(physics.llm_assistance["timeout_recovery_attempted"])
        self.assertTrue(physics.llm_assistance["timeout_recovery_skipped"])
        self.assertIn("smallest low-value rough-request prompt", physics.llm_assistance["timeout_recovery_skip_reason"])
        self.assertIn("Skipped timeout recovery", physics.llm_assistance["fallback_reason"])
        self.assertEqual(physics.llm_assistance["intent_primary_timeout_seconds"], 8.0)
        self.assertEqual(backend.seen_timeouts, [8.0])

    def test_timeout_recovery_uses_second_smaller_prompt_for_full_interpretation(self):
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
                  "notes": ["recovery succeeded"]
                }
                """,
            ]
        )
        physics = resolve_physics_target(
            "I want a meson correlator script but I am not sure about the exact operator",
            backend=backend,
            backend_status={
                "requested_backend": "codex",
                "configured": True,
                "backend_name": "codex",
                "fallback": False,
                "fallback_reason": None,
            },
        )
        self.assertEqual(backend.calls, 2)
        self.assertTrue(physics.llm_assistance["used"])
        self.assertFalse(physics.llm_assistance["fallback"])
        self.assertTrue(physics.llm_assistance["timeout_recovery_attempted"])
        self.assertTrue(physics.llm_assistance["timeout_recovery_used"])
        self.assertFalse(physics.llm_assistance["timeout_recovery_failed"])
        self.assertIn("timeout_recovery_interpretation", physics.llm_assistance["stages_attempted"])
        self.assertIn("recovery succeeded", physics.llm_assistance["notes"])
        self.assertIn("llm timeout recovery path used", physics.llm_assistance["notes"])
        self.assertEqual(physics.llm_assistance["intent_primary_timeout_seconds"], 12.0)
        self.assertEqual(physics.llm_assistance["timeout_recovery_timeout_seconds"], 10.0)
        first_prompt = backend.prompts[0][1]
        second_prompt = backend.prompts[1][1]
        self.assertEqual(backend.seen_timeouts, [12.0, 10.0])
        self.assertEqual(backend.timeout_seconds, 30.0)
        self.assertLess(len(second_prompt), len(first_prompt))
        self.assertEqual(physics.llm_assistance["intent_strategy"], "full_interpretation")
        self.assertEqual(physics.llm_assistance["intent_prompt_profile"], "full")
        self.assertFalse(physics.llm_assistance["timeout_recovery_skipped"])
        self.assertIn("The first LLM-assisted interpretation attempt timed out.", second_prompt)
        self.assertGreater(len(first_prompt), 2000)

    def test_timeout_recovery_failure_keeps_explicit_fallback_for_full_interpretation(self):
        backend = _SequenceBackend(
            [
                BackendInvocationError("initial timeout", category="timeout"),
                BackendInvocationError("second timeout", category="timeout"),
            ]
        )
        physics = resolve_physics_target(
            "I want a meson correlator script but I am not sure about the exact operator",
            backend=backend,
            backend_status={
                "requested_backend": "codex",
                "configured": True,
                "backend_name": "codex",
                "fallback": False,
                "fallback_reason": None,
            },
        )
        self.assertEqual(backend.calls, 2)
        self.assertTrue(physics.llm_assistance["fallback"])
        self.assertEqual(physics.llm_assistance["fallback_category"], "timeout")
        self.assertEqual(physics.llm_assistance["intent_primary_timeout_seconds"], 12.0)
        self.assertTrue(physics.llm_assistance["timeout_recovery_attempted"])
        self.assertFalse(physics.llm_assistance["timeout_recovery_skipped"])
        self.assertFalse(physics.llm_assistance["timeout_recovery_used"])
        self.assertTrue(physics.llm_assistance["timeout_recovery_failed"])
        self.assertEqual(physics.llm_assistance["timeout_recovery_failure_category"], "timeout")
        self.assertIn("Initial LLM attempt timed out", physics.llm_assistance["fallback_reason"])

    def test_api_backend_keeps_non_concise_prompt(self):
        backend = _FakeBackend(
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
              "notes": ["llm used"]
            }
            """
        )
        resolve_physics_target(
            "write a simple PyQUDA script for pi meson two-point",
            backend=backend,
            backend_status={
                "requested_backend": "api",
                "configured": True,
                "backend_name": "api:test/model",
                "fallback": False,
                "fallback_reason": None,
            },
        )
        assert backend.last_user_prompt is not None
        self.assertIn('"formula_proposal_count": 1', backend.last_user_prompt)


if __name__ == "__main__":
    unittest.main()
