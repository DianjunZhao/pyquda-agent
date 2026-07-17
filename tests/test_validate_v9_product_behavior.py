import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate_v9_product_behavior import TEST_GROUPS
from scripts.validate_v9_product_behavior import main


class ValidateV9ProductBehaviorTests(unittest.TestCase):
    def test_main_writes_grouped_behavior_report(self):
        class Completed:
            def __init__(self, returncode: int, stdout: str = "ok", stderr: str = ""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr

        def fake_run(cmd, cwd=None, text=None, capture_output=None, check=None):
            self.assertEqual(cmd[:3], [cmd[0], "-B", "-m"])
            self.assertEqual(cmd[3], "unittest")
            requested = cmd[4:]
            for group_tests in TEST_GROUPS.values():
                if requested == group_tests:
                    return Completed(0, stdout="OK")
            return Completed(1, stdout="", stderr="unexpected test selection")

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "data" / "v9_product_behavior.json"
            with patch("scripts.validate_v9_product_behavior.subprocess.run", side_effect=fake_run):
                exit_code = main(["--output", str(output)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["suite"], "v9_product_behavior")
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["summary"]["group_count"], len(TEST_GROUPS))
            self.assertEqual(payload["summary"]["passed_group_count"], len(TEST_GROUPS))
            self.assertTrue(payload["summary"]["unsupported_behavior"]["covered"])
            self.assertEqual(
                payload["summary"]["unsupported_behavior"]["primary_action_contract"]["copyable_retry_kind"],
                "retry_supported_workflow",
            )
            self.assertEqual(
                payload["summary"]["unsupported_behavior"]["primary_action_contract"]["choice_required_kind"],
                "choose_supported_variant",
            )
            self.assertTrue(
                payload["summary"]["unsupported_behavior"]["primary_action_contract"]["backend_fix_should_not_be_primary"]
            )
            self.assertIn(
                "test_cli_run_explicit_rho_request_reports_nearest_grounded_meson_fix",
                " ".join(payload["summary"]["unsupported_behavior"]["covered_tests"]["copyable_retry_paths"]),
            )
            self.assertIn(
                "choose_supported_variant",
                payload["summary"]["unsupported_behavior"]["note"],
            )
            self.assertEqual(
                [item["group"] for item in payload["groups"]],
                list(TEST_GROUPS.keys()),
            )
            self.assertTrue(all(item["passed"] for item in payload["groups"]))
            self.assertIn("clarification routing", payload["note"])
            self.assertIn("terminal execution-state rendering", payload["note"])
            self.assertIn("terminal repair guidance", payload["note"])
            self.assertIn("runtime recovery guidance", payload["note"])
            self.assertIn("explicit unsupported refusal", payload["note"])
            self.assertIn("HPC handoff quality", payload["note"])


if __name__ == "__main__":
    unittest.main()
