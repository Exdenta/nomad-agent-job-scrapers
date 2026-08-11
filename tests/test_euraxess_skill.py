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
SUMMARY_SCHEMA = ROOT / "integrations" / "shared" / "fleet-run-summary-v2.schema.json"
SUMMARY_VALIDATOR = ROOT / "integrations" / "shared" / "validate_fleet_run_summary.py"
SKILL_SUMMARY_VALIDATOR = SCRIPTS / "validate_run_summary.py"
CUSTOM_SCHEMA = ROOT / "integrations" / "shared" / "euraxess-v1.schema.json"
CANONICAL_CUSTOM_SCHEMA_SHA256 = (
    "2007916ebd1d900a7de5c2db69a1790da426c2a21ef1a7013cec1db1c6dcfcb4"
)
FINDJOBS = ROOT.parent / "FindJobs"
CANONICAL_CUSTOM_SCHEMA = FINDJOBS / "apify" / "job_custom_schemas" / "euraxess-v1.schema.json"
CANONICAL_ACTOR = FINDJOBS / "apify" / "euraxess-enrich-translate-normalize-scraper"


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
        "schemaVersion": "nomad-agent-fleet-run-summary-v2",
        "status": "succeeded",
        "startedAt": "2026-08-10T10:00:00Z",
        "finishedAt": "2026-08-10T10:02:00Z",
        "partial": False,
        "truncated": False,
        "delivered": 2,
        "sources": {
            "euraxess": {
                "status": "succeeded",
                "searchRequests": 3,
                "cardsSeen": 10,
                "detailsCompleted": 8,
                "normalized": 8,
                "afterFilters": 5,
                "deliveryEligible": 2,
                "delivered": 2,
                "stale": False,
                "blocked": False,
                "stopReason": None,
                "errors": [],
            }
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

    def test_fixture_matches_current_actor_mapper_example_exactly(self) -> None:
        python = FINDJOBS / "apify" / ".venv" / "bin" / "python"
        actor_test = CANONICAL_ACTOR / "test_euraxess_parsing_mapping.py"
        if not python.is_file() or not actor_test.is_file():
            self.skipTest("sibling FindJobs Actor checkout is unavailable")
        code = (
            "import json,sys; "
            f"sys.path.insert(0,{str(CANONICAL_ACTOR)!r}); "
            "import test_euraxess_parsing_mapping as fixture; "
            "record=fixture._mapped(); record['raw']=None; "
            "print(json.dumps(record, sort_keys=True))"
        )
        result = subprocess.run(
            [str(python), "-c", code],
            cwd=CANONICAL_ACTOR,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.record, json.loads(result.stdout))

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
                validator = installed / "scripts" / "validate_run_summary.py"
                self.assertTrue(validator.is_file())
                self.assertTrue((installed / "references" / "run-summary.md").is_file())
                validated = subprocess.run(
                    [sys.executable, str(validator)],
                    input=json.dumps(valid_summary()),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(validated.returncode, 0, validated.stderr)
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
        self.assertIn("fetch-actor-details,nomad-agent/euraxess", metadata)
        self.assertIn('transport: "streamable_http"', metadata)
        self.assertIn("private older `0.5.1`", combined)
        self.assertIn("unreleased", combined.lower())
        self.assertIn("nomad-agent-job-search-input-v1", combined)
        self.assertIn("nomad-agent-euraxess-search-v1", combined)
        self.assertIn("nomad-agent-fleet-run-summary-v2", combined)
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

    def test_fleet_summary_schema_is_closed_and_has_no_retry_schedule(self) -> None:
        schema = json.loads(SUMMARY_SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["schemaVersion"]["const"],
            "nomad-agent-fleet-run-summary-v2",
        )
        source = schema["$defs"]["source"]
        self.assertFalse(source["additionalProperties"])
        self.assertEqual(source["properties"]["errors"]["maxItems"], 32)
        self.assertIn("structural", schema["title"].lower())
        self.assertIn("validate_fleet_run_summary.py", schema["description"])
        rendered = json.dumps(schema)
        for forbidden in ("reschedule", "afterSeconds", "notBefore", "message"):
            self.assertNotIn(forbidden, rendered)

    def test_fleet_summary_semantic_validator_accepts_canonical_example(self) -> None:
        result = run_summary_validator(valid_summary())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "valid fleet run summary")

    def test_shared_and_installed_skill_summary_validators_have_exact_parity(self) -> None:
        values = [valid_summary()]
        invalid = valid_summary()
        invalid["sources"]["euraxess"]["normalized"] = 9
        values.append(invalid)
        for value in values:
            with self.subTest(valid=value is values[0]):
                shared = run_summary_validator(value, SUMMARY_VALIDATOR)
                bundled = run_summary_validator(value, SKILL_SUMMARY_VALIDATOR)
                self.assertEqual(shared.returncode, bundled.returncode)
                self.assertEqual(shared.stdout, bundled.stdout)
                self.assertEqual(shared.stderr, bundled.stderr)

    def test_fleet_summary_semantic_validator_rejects_impossible_facts(self) -> None:
        cases = []

        nonmonotonic = valid_summary()
        nonmonotonic["sources"]["euraxess"]["detailsCompleted"] = 11
        cases.append((nonmonotonic, "monotonically non-increasing"))

        empty_with_cards = valid_summary()
        empty_with_cards.update(status="empty", delivered=0)
        source = empty_with_cards["sources"]["euraxess"]
        source.update(
            status="empty",
            cardsSeen=1,
            detailsCompleted=0,
            normalized=0,
            afterFilters=0,
            deliveryEligible=0,
            delivered=0,
        )
        cases.append((empty_with_cards, "empty status cannot report cards"))

        succeeded_and_blocked = valid_summary()
        source = succeeded_and_blocked["sources"]["euraxess"]
        source.update(blocked=True, stopReason="access-blocked")
        cases.append((succeeded_and_blocked, "blocked requires partial"))

        aggregate_mismatch = valid_summary()
        aggregate_mismatch["delivered"] = 1
        cases.append((aggregate_mismatch, "must equal the sum"))

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

    def test_public_custom_schema_exactly_mirrors_sibling_canonical_schema(self) -> None:
        if not CANONICAL_CUSTOM_SCHEMA.is_file():
            self.skipTest("sibling canonical schema checkout is unavailable")
        self.assertEqual(CUSTOM_SCHEMA.read_bytes(), CANONICAL_CUSTOM_SCHEMA.read_bytes())

    def test_catalog_separates_actor_and_destination_validation_state(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs" / "euraxess.md").read_text(encoding="utf-8")
        agents = (ROOT / "docs" / "agent-skills.md").read_text(encoding="utf-8")
        self.assertIn("Actor catalog", readme)
        self.assertIn(SKILL_NAME, readme)
        self.assertIn("Build `1.0.4` is private and CI-qualified", readme)
        self.assertIn("`latest` remains on legacy `0.5.1`", readme)
        self.assertIn("Private canary\nbuild `1.0.4`", guide)
        self.assertIn("CI run 31478518379", guide)
        self.assertIn(f"--skill {SKILL_NAME}", agents)


if __name__ == "__main__":
    unittest.main()
