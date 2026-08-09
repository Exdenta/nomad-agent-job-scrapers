from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".agents" / "skills" / "linkedin-enrich-translate-normalize-scraper" / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "linkedin-job.json"
MALFORMED_FIXTURE = ROOT / "tests" / "fixtures" / "malformed-linkedin-jobs.json"
sys.path.insert(0, str(SCRIPTS))

import flatten_output  # noqa: E402
import parse_output  # noqa: E402

installer_spec = importlib.util.spec_from_file_location(
    "nomad_skill_installer", ROOT / "scripts" / "install_skill.py"
)
assert installer_spec and installer_spec.loader
install_skill = importlib.util.module_from_spec(installer_spec)
sys.modules[installer_spec.name] = install_skill
installer_spec.loader.exec_module(install_skill)


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
        with self.assertRaisesRegex(
            parse_output.OutputContractError, "extra keys.*legacyField"
        ):
            parse_output.validate_normalized_job(record)

    def test_parser_rejects_malformed_nested_contract_values(self) -> None:
        cases = json.loads(MALFORMED_FIXTURE.read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["name"]):
                record = copy.deepcopy(self.record)
                parent = record
                for component in case["path"][:-1]:
                    parent = parent[component]
                parent[case["path"][-1]] = case["value"]
                with self.assertRaisesRegex(
                    parse_output.OutputContractError, case["error"]
                ):
                    parse_output.validate_normalized_job(record)

    def test_flatten_rejects_malformed_canonical_input(self) -> None:
        record = copy.deepcopy(self.record)
        record["data"]["application"]["directApply"] = "yes"
        with self.assertRaisesRegex(
            parse_output.OutputContractError, "data.application.directApply"
        ):
            flatten_output.flatten_job(record)

    def test_canonical_identity_may_be_unknown_but_flat_job_key_may_not(self) -> None:
        record = copy.deepcopy(self.record)
        record["identity"]["externalId"] = None
        record["identity"]["url"] = None

        self.assertIs(parse_output.validate_normalized_job(record), record)
        parsed = parse_output.parse_linkedin_output(record)
        self.assertIsNone(parsed["jobKey"])
        with self.assertRaisesRegex(
            ValueError, "identity.externalId or identity.url is required for flat jobKey"
        ):
            flatten_output.flatten_job(record)

    def test_flat_validator_rejects_schema_incompatible_values(self) -> None:
        valid = flatten_output.flatten_job(self.record)
        for field, malformed in (
            ("salaryMinimum", "50000"),
            ("directApply", "yes"),
            ("llmStatus", "done"),
            ("workArrangements", "not-json"),
        ):
            with self.subTest(field=field):
                flat = dict(valid)
                flat[field] = malformed
                with self.assertRaisesRegex(ValueError, field):
                    flatten_output.validate_flat_job(flat)

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
                self.assertTrue((skill / "scripts" / "validate_contract.py").is_file())
                self.assertTrue((skill / "references" / "client-setup.md").is_file())
                self.assertFalse(any(skill.rglob("*.pyc")))
                self.assertFalse(any(path.name == "__pycache__" for path in skill.rglob("*")))

    def test_installer_rejects_symlinked_parent_without_touching_external_tree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "target"
            external = base / "external"
            target.mkdir()
            external_skill = external / "skills" / install_skill.SKILL_NAME
            external_skill.mkdir(parents=True)
            sentinel = external_skill / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            (target / ".agents").symlink_to(external, target_is_directory=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skill.py"),
                    "--client",
                    "codex",
                    "--target",
                    str(target),
                    "--force",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual([path.name for path in external_skill.iterdir()], ["sentinel.txt"])

    def test_installer_rejects_symlinked_skills_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            target = base / "target"
            external = base / "external"
            (target / ".claude").mkdir(parents=True)
            external_skill = external / install_skill.SKILL_NAME
            external_skill.mkdir(parents=True)
            sentinel = external_skill / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            (target / ".claude" / "skills").symlink_to(
                external, target_is_directory=True
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skill.py"),
                    "--client",
                    "claude",
                    "--target",
                    str(target),
                    "--force",
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_both_preflight_is_transactional_when_second_destination_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            claude = target / ".claude" / "skills" / install_skill.SKILL_NAME
            claude.mkdir(parents=True)
            marker = claude / "existing.txt"
            marker.write_text("keep", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "install_skill.py"),
                    "--client",
                    "both",
                    "--target",
                    str(target),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            codex = target / ".agents" / "skills" / install_skill.SKILL_NAME
            self.assertFalse(codex.exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_both_rolls_back_if_second_staged_install_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve()
            destinations = {}
            plans = []
            for client, root in (("codex", ".agents"), ("claude", ".claude")):
                destination = target / root / "skills" / install_skill.SKILL_NAME
                destination.mkdir(parents=True)
                (destination / "existing.txt").write_text(client, encoding="utf-8")
                destinations[client] = destination
                plans.append(install_skill.InstallPlan(client, destination))

            source = ROOT / ".agents" / "skills" / install_skill.SKILL_NAME
            original_rename = Path.rename

            def fail_second_stage(path: Path, destination: Path) -> Path:
                if (
                    path.parent.name.startswith(".nomad-skill-stage-")
                    and destination == destinations["claude"]
                ):
                    raise OSError("simulated second-client commit failure")
                return original_rename(path, destination)

            with mock.patch.object(Path, "rename", fail_second_stage):
                with self.assertRaisesRegex(OSError, "simulated"):
                    install_skill.install_all(source, target, plans, force=True)

            for client, destination in destinations.items():
                self.assertEqual(
                    (destination / "existing.txt").read_text(encoding="utf-8"),
                    client,
                )

    def test_skill_declares_scoped_apify_mcp_dependency(self) -> None:
        skill = ROOT / ".agents" / "skills" / "linkedin-enrich-translate-normalize-scraper"
        metadata = (skill / "agents" / "openai.yaml").read_text(encoding="utf-8")
        scoped_url = (
            "https://mcp.apify.com?tools="
            "fetch-actor-details,"
            "nomad-agent/linkedin-enrich-translate-normalize-scraper"
        )
        self.assertIn('transport: "streamable_http"', metadata)
        self.assertIn(f'url: "{scoped_url}"', metadata)

        setup = (skill / "references" / "client-setup.md").read_text(encoding="utf-8")
        self.assertIn("codex mcp login apify", setup)
        self.assertIn(
            "claude mcp add --transport http --scope project apify", setup
        )
        self.assertIn("Use `--scope local` (the default)", setup)
        self.assertIn("get-actor-run", setup)
        self.assertIn("get-dataset-items", setup)
        self.assertNotIn("APIFY_TOKEN=", setup)

    def test_skill_uses_terminal_run_then_dataset_items_path(self) -> None:
        skill = ROOT / ".agents" / "skills" / "linkedin-enrich-translate-normalize-scraper"
        sources = [
            (skill / "SKILL.md").read_text(encoding="utf-8"),
            (skill / "references" / "client-setup.md").read_text(encoding="utf-8"),
            (skill / "references" / "search-examples.md").read_text(encoding="utf-8"),
        ]
        combined = "\n".join(sources)
        self.assertNotIn("get-actor-output", combined)
        for required in (
            "get-actor-run",
            "SUCCEEDED",
            "storages.datasets.default.id",
            "get-dataset-items",
            "Paginate",
            "zero dataset items",
            "partial",
        ):
            self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
