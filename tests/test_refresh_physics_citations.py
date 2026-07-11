import json
import tempfile
import unittest
from pathlib import Path

from scripts.refresh_physics_citations import main
from scripts.refresh_physics_citations import render_citation_entry


class RefreshPhysicsCitationsTests(unittest.TestCase):
    def test_render_citation_entry_uses_curated_metadata(self):
        rendered = render_citation_entry(
            {
                "id": "bulava-2022-hadron-spectroscopy",
                "type": "authoritative_review",
                "url": "https://arxiv.org/abs/2203.03230",
                "supports": ["two_point_spectral_decomposition"],
                "chosen_convention": "x",
                "why_needed": "y",
            }
        )
        self.assertEqual(rendered["title"], "Hadron Spectroscopy with Lattice QCD")
        self.assertEqual(rendered["year"], 2022)
        self.assertEqual(rendered["metadata_source"], "curated_fallback")
        self.assertEqual(rendered["metadata_refresh"], "curated_fallback")

    def test_main_refreshes_rendered_json_from_sources_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)
            source_path = data_dir / "workflow.sources.json"
            source_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "bulava-2022-hadron-spectroscopy",
                            "type": "authoritative_review",
                            "url": "https://arxiv.org/abs/2203.03230",
                            "supports": ["two_point_spectral_decomposition"],
                            "chosen_convention": "x",
                            "why_needed": "y",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            exit_code = main(["--data-dir", str(data_dir)])
            self.assertEqual(exit_code, 0)
            rendered_path = data_dir / "workflow.json"
            self.assertTrue(rendered_path.exists())
            payload = json.loads(rendered_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["title"], "Hadron Spectroscopy with Lattice QCD")
            self.assertEqual(payload[0]["metadata_source"], "curated_fallback")
            self.assertEqual(payload[0]["metadata_refresh"], "curated_fallback")


if __name__ == "__main__":
    unittest.main()
