from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "euraxess-enrich-translate-normalize-scraper"
SKILL = ROOT / ".agents" / "skills" / SKILL_NAME
SCRIPTS = SKILL / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "euraxess-job.json"
SUMMARY_SCHEMA = ROOT / "integrations" / "shared" / "run-summary-v4.schema.json"
SUMMARY_VALIDATOR = ROOT / "integrations" / "shared" / "validate_run_summary.py"
CUSTOM_SCHEMA = ROOT / "integrations" / "shared" / "euraxess-v1.schema.json"
CANONICAL_CUSTOM_SCHEMA_SHA256 = (
    "2007916ebd1d900a7de5c2db69a1790da426c2a21ef1a7013cec1db1c6dcfcb4"
)
CANONICAL_FIXTURE_SHA256 = (
    "9ab8e26a0bd2ae490b7f760923077a27d4d87fb7f7685eac492f50d72a546d0f"
)


def run_script(name: str, value: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name)],
        input=json.dumps(value),
        capture_output=True,
        text=True,
        check=False,
    )


def run_summary_validator(
    value: object,
    validator: Path = SUMMARY_VALIDATOR,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(validator)],
        input=json.dumps(value),
        capture_output=True,
        text=True,
        check=False,
    )


def valid_summary() -> dict[str, object]:
    return {
        "schemaVersion": "nomad-agent-run-summary-v4",
        "status": "succeeded",
        "startedAt": "2026-08-10T10:00:00Z",
        "finishedAt": "2026-08-10T10:02:00Z",
        "resultsLimited": False,
        "delivered": 2,
        "retry": {
            "recommended": False,
            "afterSeconds": None,
        },
    }


class EuraxessSkillTest(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_parser_validates_and_retains_euraxess_custom_contract(self) -> None:
        result = run_script("parse_output.py", self.record)
        self.assertEqual(result.returncode, 0, result.stderr)
        parsed = json.loads(result.stdout)[0]
        self.assertEqual(parsed["jobKey"], "euraxess:452297")
        self.assertEqual(
            parsed["domains"],
            ["Biological sciences", "Medical sciences", "Natural sciences"],
        )
        self.assertEqual(parsed["academicLevelRaw"], ["PhD Positions"])
        self.assertEqual(parsed["normalized"], self.record)

    def test_fixture_is_the_reviewed_standalone_contract_example(self) -> None:
        self.assertEqual(
            hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
            CANONICAL_FIXTURE_SHA256,
        )

    def test_fixture_does_not_claim_unsupported_static_mapper_facts(self) -> None:
        data = self.record["data"]
        application = data["application"]
        self.assertEqual(
            {
                "company.url": data["company"]["url"],
                "employment.durationMonths": data["employment"]["durationMonths"],
                "application.referenceNumberIssuer": application["referenceNumberIssuer"],
                "application.directApply": application["directApply"],
                "application.applyMethodRaw": application["applyMethodRaw"],
                "application.hiringContacts[0].title": application["hiringContacts"][0]["title"],
            },
            {
                "company.url": None,
                "employment.durationMonths": None,
                "application.referenceNumberIssuer": None,
                "application.directApply": None,
                "application.applyMethodRaw": None,
                "application.hiringContacts[0].title": None,
            },
        )
        self.assertEqual(
            self.record["llm"],
            {
                "status": "not_requested",
                "requestedFields": [],
                "filledFields": [],
                "provider": None,
                "model": None,
                "promptVersion": None,
                "completedAt": None,
            },
        )

    def test_flat_projection_reuses_shared_shape_without_erasing_unknowns(self) -> None:
        result = run_script("flatten_output.py", self.record)
        self.assertEqual(result.returncode, 0, result.stderr)
        flat = json.loads(result.stdout)[0]
        schema = json.loads(
            (ROOT / "integrations" / "shared" / "flat-job-v1.schema.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(set(flat), set(schema["required"]))
        self.assertEqual(flat["jobKey"], "euraxess:452297")
        self.assertIsNone(flat["workArrangements"])
        self.assertEqual(flat["contractTypes"], '["Temporary"]')
        self.assertEqual(flat["seniorityLevels"], '["R1"]')

    def test_validator_rejects_wrong_source_or_missing_custom_extension(self) -> None:
        for mutate, expected in (
            (lambda value: value["identity"].__setitem__("source", "linkedin"), "source"),
            (lambda value: value.__setitem__("custom", None), "custom"),
        ):
            with self.subTest(expected=expected):
                record = copy.deepcopy(self.record)
                mutate(record)
                result = run_script("parse_output.py", record)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_validator_requires_named_hiring_contacts(self) -> None:
        record = copy.deepcopy(self.record)
        record["data"]["application"]["hiringContacts"][0]["name"] = None
        result = run_script("parse_output.py", record)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hiringContacts[0].name", result.stderr)

    def test_installer_selects_euraxess_for_both_clients(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skill.py"),
                    "--skill",
                    SKILL_NAME,
                    "--client",
                    "both",
                    "--target",
                    str(target),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for root in (".agents", ".claude"):
                installed = target / root / "skills" / SKILL_NAME
                self.assertTrue((installed / "SKILL.md").is_file())
                self.assertTrue((installed / "scripts" / "parse_output.py").is_file())
                self.assertTrue((installed / "scripts" / "validate_run_summary.py").is_file())
                self.assertTrue((installed / "references" / "run-summary.md").is_file())
                self.assertFalse(any(installed.rglob("*.pyc")))

    def test_skill_metadata_and_docs_pin_the_compatibility_boundary(self) -> None:
        metadata = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                SKILL / "SKILL.md",
                SKILL / "references" / "input-contract.md",
                SKILL / "references" / "output-contract.md",
                SKILL / "references" / "run-summary.md",
                SKILL / "references" / "client-setup.md",
            ]
        )
        self.assertTrue(skill.startswith("---\nname: euraxess-"))
        self.assertIn("fetch-actor-details,call-actor", metadata)
        self.assertIn('transport: "streamable_http"', metadata)
        self.assertIn("exact build `1.0.13`", combined)
        self.assertIn("build `1.0.13`", combined)
        self.assertIn("nomad-agent-job-search-input-v1", combined)
        self.assertIn("nomad-agent-euraxess-search-v1", combined)
        self.assertIn("RUN-SUMMARY", combined)
        self.assertIn("get-key-value-store-record", combined)
        self.assertIn("nomad-agent-run-summary-v4", combined)
        self.assertIn("at most once", combined.lower())
        self.assertIn("academicLevelRaw", combined)
        self.assertIn("only named people", combined.lower())
        self.assertIn("rejects `1h`", combined)
        self.assertIn("calendar-date", combined)
        self.assertIn("inclusive cutoff of the previous UTC calendar date", combined)
        self.assertIn("older than 24 elapsed hours", combined)
        self.assertIn("subtract 7 or 30", combined)
        self.assertIn("explicitly published under EURAXESS `Where to apply`", combined)
        self.assertIn("`Contact` block stay in raw evidence", combined)
        self.assertNotIn("live-validated EURAXESS", combined)
        self.assertNotIn("APIFY_TOKEN=", combined)

    def test_run_summary_v4_schema_is_closed_and_minimal(self) -> None:
        schema = json.loads(SUMMARY_SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["schemaVersion"]["const"],
            "nomad-agent-run-summary-v4",
        )
        self.assertEqual(schema["properties"]["retry"], {"$ref": "#/$defs/retry"})
        retry = schema["$defs"]["retry"]
        self.assertFalse(retry["additionalProperties"])
        self.assertEqual(set(retry["required"]), {"recommended", "afterSeconds"})
        rendered = json.dumps(schema)
        for forbidden in ("sources", "searchRequests", "cardsSeen", "errors", "message"):
            self.assertNotIn(forbidden, rendered)
        self.assertIn("afterSeconds", rendered)
        self.assertNotIn("notBefore", rendered)

    def test_fleet_summary_semantic_validator_accepts_canonical_example(self) -> None:
        result = run_summary_validator(valid_summary())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "valid run summary")

    def test_fleet_summary_semantic_validator_rejects_impossible_facts(self) -> None:
        cases = []

        internal_leak = valid_summary()
        internal_leak["sources"] = {}
        cases.append((internal_leak, "closed object"))

        empty_with_delivery = valid_summary()
        empty_with_delivery.update(status="empty", delivered=1)
        cases.append((empty_with_delivery, "empty requires delivered=0"))

        succeeded_retry = valid_summary()
        succeeded_retry["retry"] = {
            "recommended": True,
            "afterSeconds": 60,
        }
        cases.append((succeeded_retry, "succeeded cannot recommend"))

        false_with_timing = valid_summary()
        false_with_timing["retry"]["afterSeconds"] = 60
        cases.append((false_with_timing, "requires afterSeconds=null"))

        partial_without_jobs = valid_summary()
        partial_without_jobs.update(status="partial", delivered=0)
        cases.append((partial_without_jobs, "require at least one delivered job"))

        for summary, expected in cases:
            with self.subTest(expected=expected):
                result = run_summary_validator(summary)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)

    def test_public_custom_schema_pins_canonical_bytes_and_id(self) -> None:
        raw = CUSTOM_SCHEMA.read_bytes()
        schema = json.loads(raw)
        self.assertEqual(
            schema["$id"],
            "https://raw.githubusercontent.com/Exdenta/OinkJobSearch/main/"
            "apify/job_custom_schemas/euraxess-v1.schema.json",
        )
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            CANONICAL_CUSTOM_SCHEMA_SHA256,
        )

    def test_catalog_separates_actor_and_destination_validation_state(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "euraxess.md").read_text(encoding="utf-8")
        agents = (ROOT / "docs" / "agent-skills.md").read_text(encoding="utf-8")
        self.assertIn("Actor catalog", readme)
        self.assertIn(SKILL_NAME, readme)
        self.assertIn("LinkedIn `0.6` and EURAXESS `1.0` are public Store Actors", readme)
        self.assertIn("exact supported build `1.0.13`", readme)
        self.assertIn("supports exact build `1.0.13`", guide)
        self.assertIn("build `1.0.13`", guide)
        self.assertIn(f"--skill {SKILL_NAME}", agents)


if __name__ == "__main__":
    unittest.main()
