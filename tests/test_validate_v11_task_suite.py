import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_v11_task_suite import main
from pyquda_agent.v11_task_suite import V11_TASK_SUITE


class ValidateV11TaskSuiteTests(unittest.TestCase):
    def test_task_suite_covers_requested_request_classes(self):
        case_ids = {item["case_id"] for item in V11_TASK_SUITE}
        self.assertIn("ambiguous_meson_operator", case_ids)
        self.assertIn("explicit_pion_2pt", case_ids)
        self.assertIn("explicit_pion_pcac", case_ids)
        self.assertIn("explicit_meson_spec", case_ids)
        self.assertIn("explicit_rho", case_ids)
        self.assertIn("explicit_proton", case_ids)
        self.assertIn("explicit_quark_propagator", case_ids)
        self.assertIn("explicit_gaussian_shell_propagator", case_ids)
        self.assertIn("rough_gauge_smear_family", case_ids)
        self.assertIn("explicit_wilson_flow", case_ids)
        self.assertIn("unsupported_neutron", case_ids)
        self.assertIn("unsupported_quark_wall_source", case_ids)
        self.assertIn("unsupported_stout_existing_propagator", case_ids)
        self.assertIn("unsupported_wilson_flow_existing_propagator", case_ids)
        self.assertIn("unsupported_meson_spec_gauge_fixed", case_ids)

    def test_main_writes_v11_task_suite_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "data" / "v11_task_suite.json"
            exit_code = main(["--output", str(output)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["suite"], "v11_task_suite")
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["summary"]["case_count"], len(V11_TASK_SUITE))
            self.assertEqual(payload["summary"]["passed_case_count"], len(V11_TASK_SUITE))
            self.assertEqual(payload["summary"]["contract"], "summary_only_dry_run")
            self.assertIn("ambiguous meson", payload["summary"]["coverage"])
            self.assertIn("unsupported propagator / smear / flow boundary variants", payload["summary"]["coverage"])
            self.assertIn("unsupported non-grounded meson-like variants", payload["summary"]["coverage"])
            observed_by_case = {item["case_id"]: item["observed"] for item in payload["cases"]}
            self.assertEqual(
                observed_by_case["ambiguous_meson_operator"]["clarification_mode"],
                "physics_confirmation",
            )
            self.assertEqual(
                observed_by_case["unsupported_neutron"]["shortest_fix_target"],
                "proton_2pt_chroma_wall_local_zero_momentum_npy_v1",
            )
            self.assertEqual(
                observed_by_case["explicit_gaussian_shell_propagator"]["workflow_target"],
                "quark_propagator_gaussian_shell_chroma_hdf5_v1",
            )
            self.assertEqual(
                observed_by_case["explicit_wilson_flow"]["workflow_target"],
                "wilson_flow_chroma_qio_energy_npy_v1",
            )
            self.assertEqual(
                observed_by_case["unsupported_quark_wall_source"]["shortest_fix_target"],
                "quark_propagator_chroma_point_hdf5_v1",
            )
            self.assertEqual(
                observed_by_case["unsupported_quark_wall_source"]["unsupported_scope"],
                "physics",
            )
            self.assertEqual(
                observed_by_case["unsupported_stout_existing_propagator"]["unsupported_scope"],
                "implementation",
            )
            self.assertEqual(
                observed_by_case["unsupported_wilson_flow_existing_propagator"]["shortest_fix_target"],
                "wilson_flow_chroma_qio_energy_npy_v1",
            )


if __name__ == "__main__":
    unittest.main()
