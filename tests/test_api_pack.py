from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "integrations" / "api"


class ApiPackTests(unittest.TestCase):
    def test_examples_are_bounded_and_source_specific(self) -> None:
        linkedin = json.loads((PACK / "linkedin-search.json").read_text())
        euraxess = json.loads((PACK / "euraxess-search.json").read_text())
        for value in (linkedin, euraxess):
            self.assertEqual(value["schemaVersion"], "nomad-agent-job-search-input-v1")
            self.assertLessEqual(value["maxItems"], 5)
            self.assertFalse(value["translateToEnglish"])
            self.assertFalse(value["aiEnrichment"]["enabled"])
            self.assertFalse(value["includeRaw"])
            self.assertFalse(value["dedupe"]["enabled"])
            self.assertFalse(value["analyticsEnabled"])
        self.assertNotIn("euraxessSearch", linkedin)
        self.assertEqual(
            euraxess["euraxessSearch"],
            {
                "schemaVersion": "nomad-agent-euraxess-search-v1",
                "translateKeywords": False,
            },
        )

    def test_readme_pins_both_builds_and_preserves_the_run_contract(self) -> None:
        text = (PACK / "README.md").read_text(encoding="utf-8")
        for required in (
            "build=0.6.42",
            "build=1.0.11",
            "maxTotalChargeUsd",
            "Authorization: Bearer $APIFY_TOKEN",
            "buildNumber",
            "terminal run status",
            "RUN-SUMMARY",
            "nomad-agent-run-summary-v4",
            "RUN-SUMMARY.delivered",
            "limited to one valid v4",
            "webhook",
            "idempotently",
            "schemaVersion`, `identity`, `data`,",
            "`custom`, `llm`, and `raw`",
        ):
            self.assertIn(required, text)
        self.assertNotIn("token=", text.lower())


if __name__ == "__main__":
    unittest.main()
