import json
import unittest
from pathlib import Path


class GoalAuditTests(unittest.TestCase):
    def test_goal_audit_contains_expected_requirement_records(self):
        audit_path = Path("data/goal_audit.json")
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["objective"], "first_workflow_pion_2pt")
        items = {item["id"]: item for item in payload["items"]}
        self.assertIn("req-3-structured-task-spec", items)
        self.assertIn("dod-support-api-and-codex", items)
        self.assertIn("dod-hpc-script-readiness", items)
        self.assertEqual(items["dod-hpc-script-readiness"]["status"], "proved")
        self.assertIn("env-local-runtime-readiness", items)
        self.assertEqual(items["env-local-runtime-readiness"]["status"], "not_proved")


if __name__ == "__main__":
    unittest.main()
