import unittest
from unittest.mock import patch

from pyquda_agent.intent.interpreter import interpret_request
from pyquda_agent.knowledge.external import maybe_lookup_external_knowledge


class ExternalKnowledgeTests(unittest.TestCase):
    def test_external_lookup_stays_disabled_by_default(self):
        physics = interpret_request("I want a meson correlator script but I am not sure about the exact operator")
        physics = maybe_lookup_external_knowledge(physics, enabled=False)
        self.assertFalse(physics.external_lookup["attempted"])
        self.assertEqual(physics.external_lookup["status"], "disabled")
        self.assertFalse(physics.knowledge_boundary["live_online_lookup"]["used"])

    def test_external_lookup_records_live_results_when_enabled(self):
        physics = interpret_request("I want a meson correlator script but I am not sure about the exact operator")
        with patch("pyquda_agent.knowledge.external._query_arxiv", return_value=[{"title": "Meson", "url": "https://arxiv.org/abs/1234.5678", "summary": "sum_x O Odag", "source_kind": "live_online_lookup", "provider": "arxiv_api"}]):
            physics = maybe_lookup_external_knowledge(physics, enabled=True)
        self.assertTrue(physics.external_lookup["attempted"])
        self.assertEqual(physics.external_lookup["status"], "ok")
        self.assertEqual(physics.external_lookup["effect_on_interpretation"], "formula_proposal_enrichment")
        self.assertTrue(physics.knowledge_boundary["live_online_lookup"]["used"])
        self.assertTrue(any(item["citation_source_kind"] == "live_online_lookup" for item in physics.external_citations))
        self.assertTrue(any(item["provenance"] == "live_online_lookup" for item in physics.formula_proposals))

    def test_external_lookup_is_not_attempted_for_supported_grounded_target(self):
        physics = interpret_request("please compute the pion two-point correlator")
        with patch("pyquda_agent.knowledge.external._query_arxiv") as lookup_mock:
            physics = maybe_lookup_external_knowledge(physics, enabled=True)
        self.assertFalse(lookup_mock.called)
        self.assertEqual(physics.external_lookup["status"], "not_needed")
        self.assertEqual(physics.external_lookup["effect_on_interpretation"], "none")


if __name__ == "__main__":
    unittest.main()
