from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".agents" / "skills" / "linkedin-enrich-translate-normalize-scraper" / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "linkedin-job.json"
sys.path.insert(0, str(SCRIPTS))

import flatten_output  # noqa: E402
import parse_output  # noqa: E402


class ContractToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_parser_accepts_raw_null_and_retains_record(self) -> None:
        parsed = parse_output.parse_linkedin_output(self.record)
        self.assertEqual(parsed["jobKey"], "linkedin:4446226935")
        self.assertIsNone(parsed["description"])
        self.assertIs(parsed["normalized"], self.record)

    def test_parser_rejects_open_top_level_envelope(self) -> None:
        record = copy.deepcopy(self.record)
        record["legacyField"] = True
        with self.assertRaisesRegex(parse_output.OutputContractError, "extra=.*legacyField"):
            parse_output.validate_normalized_job(record)

    def test_flat_projection_keeps_array_null_and_empty_distinct(self) -> None:
        flat = flatten_output.flatten_job(self.record)
        self.assertEqual(flat["schemaVersion"], "nomad-agent-flat-job-v1")
        self.assertEqual(flat["workArrangements"], '["hybrid"]')
        self.assertEqual(flat["contractTypes"], "[]")
        self.assertEqual(flat["seniorityLevels"], '["entry"]')
        self.assertEqual(flat["locationText"], "Madrid, Community of Madrid, Spain (Hybrid)")
        self.assertIsNone(flat["descriptionText"])

    def test_flat_projection_can_embed_canonical_json(self) -> None:
        flat = flatten_output.flatten_job(self.record, include_record_json=True)
        self.assertEqual(json.loads(flat["normalizedRecordJson"]), self.record)

    def test_flat_schema_matches_mapper_keys(self) -> None:
        schema = json.loads(
            (ROOT / "integrations" / "shared" / "flat-job-v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        flat = flatten_output.flatten_job(self.record)
        self.assertEqual(set(schema["required"]), set(flat))
        self.assertTrue(set(flat) <= set(schema["properties"]))

    def test_skill_installer_supports_both_clients(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skill.py"),
                    "--client",
                    "both",
                    "--target",
                    str(target),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            for client_root in (".agents", ".claude"):
                skill = target / client_root / "skills" / "linkedin-enrich-translate-normalize-scraper"
                self.assertTrue((skill / "SKILL.md").is_file())
                self.assertTrue((skill / "scripts" / "parse_output.py").is_file())


if __name__ == "__main__":
    unittest.main()
