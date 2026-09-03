from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS = ROOT / "integrations"
BUILD = "0.1.10"
BUILD_ID = "XOOtUsksU2uE89H6l"

adapter_spec = importlib.util.spec_from_file_location(
    "ai_job_fit_adapter",
    INTEGRATIONS / "shared" / "ai_job_fit_adapter.py",
)
assert adapter_spec and adapter_spec.loader
adapter = importlib.util.module_from_spec(adapter_spec)
adapter_spec.loader.exec_module(adapter)


def sample_row() -> dict[str, object]:
    job = json.loads((ROOT / "tests" / "fixtures" / "linkedin-job.json").read_text())
    return {
        "schemaVersion": "nomad-ai-job-fit-v1",
        "matchKey": "a" * 64,
        "evaluationKey": "b" * 64,
        "jobKey": "linkedin:4446226935",
        "candidateHash": "c" * 64,
        "candidateSnapshotHash": "d" * 64,
        "evaluatedAt": "2026-09-03T09:34:18Z",
        "source": "linkedin",
        "externalId": "4446226935",
        "url": job["identity"]["url"],
        "title": job["data"]["title"],
        "company": job["data"]["company"]["name"],
        "location": job["data"]["locations"][0]["raw"],
        "postedAt": job["data"]["application"]["postedAt"],
        "fitScore": 82,
        "deliveryScore": 4,
        "recommendation": "strong",
        "evaluationStatus": "scored",
        "why": "Strong platform and Python overlap.",
        "gapSummary": "Kubernetes depth is not explicit.",
        "blockingGates": [],
        "scoreAdjustedForGates": False,
        "gates": {},
        "staticDecision": {"action": "forward"},
        "scoring": {
            "algorithm": "scoring-v3",
            "sourceProvenance": {
                "actorRunId": "run-1",
                "buildNumber": BUILD,
            },
        },
        "job": job,
    }


def walk_make_modules(flow: list[dict[str, object]]) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    for module in flow:
        modules.append(module)
        for route in module.get("routes", []):
            modules.extend(walk_make_modules(route["flow"]))
    return modules


class AiJobFitScorerIntegrationTests(unittest.TestCase):
    def test_api_and_mcp_starters_are_bounded_exact_and_secret_free(self) -> None:
        actor_input = json.loads(
            (INTEGRATIONS / "api" / "ai-job-fit-scorer-input.json").read_text()
        )
        self.assertEqual(actor_input["mode"], "search")
        self.assertLessEqual(actor_input["maxItems"], 5)
        self.assertTrue(actor_input["search"]["keywords"])
        self.assertNotIn("resumeText", actor_input)

        mcp = json.loads(
            (
                INTEGRATIONS
                / "mcp"
                / "examples"
                / "ai-job-fit-scorer.mcp.json"
            ).read_text()
        )
        self.assertEqual(mcp["actor"], "nomad-agent/ai-job-fit-scorer")
        self.assertEqual(mcp["input"], actor_input)
        self.assertEqual(
            mcp["callOptions"],
            {"build": BUILD, "maxItems": 5, "maxTotalChargeUsd": 0.10},
        )

        runner_path = (
            INTEGRATIONS / "api" / "ai-job-fit-scorer-run-and-fetch.mjs"
        )
        runner = runner_path.read_text()
        self.assertIn("const VERIFIED_BUILD = '0.1.10'", runner)
        self.assertIn("/v2/actors/${ACTOR}/runs", runner)
        self.assertNotIn("/v2/acts/${ACTOR}/runs", runner)
        self.assertIn("settlementDeadline", runner)
        self.assertIn("chargedEventCounts?.['job-fit-result']", runner)
        self.assertIn("defaultDatasetId", runner)
        self.assertIn("defaultKeyValueStoreId", runner)
        self.assertIn("Authorization: `Bearer ${token}`", runner)
        self.assertNotIn("token=", runner.casefold())
        completed = subprocess.run(
            ["node", "--check", str(runner_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_closed_adapter_projects_and_upserts_by_match_key(self) -> None:
        row = sample_row()
        projected = adapter.project_rows([row])
        self.assertEqual(len(projected), 1)
        self.assertEqual(set(projected[0]), set(adapter.COLUMNS))
        self.assertEqual(projected[0]["matchKey"], row["matchKey"])
        self.assertEqual(projected[0]["schemaVersion"], "nomad-ai-job-fit-destination-v1")

        destination: dict[str, dict[str, object]] = {}
        self.assertEqual(adapter.upsert_rows(destination, [row]), (1, 0))
        self.assertEqual(adapter.upsert_rows(destination, [row]), (0, 1))

        failed = row | {
            "evaluationStatus": "ai_failed",
            "fitScore": None,
            "deliveryScore": None,
            "recommendation": "unavailable",
        }
        self.assertEqual(adapter.project_rows([failed]), [])
        with self.assertRaisesRegex(adapter.ContractError, "exact nomad-ai-job-fit-v1"):
            adapter.project_rows([row | {"unexpected": True}])

    def test_shared_contracts_match_adapter_and_sheet_projection(self) -> None:
        fit_schema = json.loads(
            (INTEGRATIONS / "shared" / "nomad-ai-job-fit-v1.schema.json").read_text()
        )
        destination_schema = json.loads(
            (
                INTEGRATIONS
                / "shared"
                / "nomad-ai-job-fit-destination-v1.schema.json"
            ).read_text()
        )
        summary_schema = json.loads(
            (
                INTEGRATIONS
                / "shared"
                / "nomad-ai-job-fit-run-summary-v3.schema.json"
            ).read_text()
        )
        self.assertFalse(fit_schema["additionalProperties"])
        self.assertEqual(set(fit_schema["properties"]), adapter.EXPECTED_KEYS)
        self.assertEqual(destination_schema["required"], list(adapter.COLUMNS))
        self.assertFalse(destination_schema["additionalProperties"])
        self.assertEqual(
            summary_schema["properties"]["schemaVersion"]["const"],
            "nomad-ai-job-fit-run-summary-v3",
        )
        headers = (
            INTEGRATIONS
            / "shared"
            / "ai-job-fit-google-sheets-columns.csv"
        ).read_text().strip().split(",")
        self.assertEqual(headers, list(adapter.COLUMNS))

    def test_n8n_workflow_is_inactive_and_executes_projection(self) -> None:
        path = INTEGRATIONS / "n8n" / "ai-job-fit-scorer-to-google-sheets.json"
        workflow = json.loads(path.read_text())
        self.assertFalse(workflow["active"])
        nodes = {node["name"]: node for node in workflow["nodes"]}
        assignments = {
            item["name"]: item["value"]
            for item in nodes["Configuration"]["parameters"]["assignments"]["assignments"]
        }
        self.assertEqual(assignments["actorBuild"], BUILD)
        self.assertEqual(assignments["maxTotalChargeUsd"], 0.10)
        self.assertEqual(
            nodes["Start exact Actor build"]["parameters"]["url"],
            "https://api.apify.com/v2/actors/nomad-agent~ai-job-fit-scorer/runs",
        )
        self.assertEqual(
            nodes["Upsert Google Sheets by matchKey"]["parameters"]["columns"]["matchingColumns"],
            ["matchKey"],
        )
        rendered = json.dumps(workflow)
        for required in (
            "RUN-SUMMARY",
            "nomad-ai-job-fit-run-summary-v3",
            "job-fit-result",
            "ai_failed",
            "polling deadline exceeded",
        ):
            self.assertIn(required, rendered)

        runner = r"""
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const row = JSON.parse(process.argv[2]);
const summary = {counts:{outputRows:1},billing:{chargedCount:1}};
const node = workflow.nodes.find(value => value.name === 'Validate and project fit rows');
global.$input = {all: () => [{json: row}]};
global.$ = () => ({first: () => ({json: summary})});
const result = new Function(node.parameters.jsCode)();
process.stdout.write(JSON.stringify(result));
"""
        completed = subprocess.run(
            ["node", "-e", runner, str(path), json.dumps(sample_row())],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        projected = json.loads(completed.stdout)[0]["json"]
        self.assertEqual(projected["matchKey"], "a" * 64)
        self.assertEqual(set(projected), set(adapter.COLUMNS))

    def test_make_and_zapier_are_pinned_with_explicit_live_gaps(self) -> None:
        blueprint = json.loads(
            (
                INTEGRATIONS
                / "make"
                / "ai-job-fit-scorer-to-google-sheets.blueprint.json"
            ).read_text()
        )
        modules = walk_make_modules(blueprint["flow"])
        by_name = {
            module["metadata"]["designer"]["name"]: module for module in modules
        }
        config = {
            item["name"]: item["value"]
            for item in by_name["Configuration"]["mapper"]["variables"]
        }
        self.assertEqual(config["expectedbuild"], BUILD)
        self.assertEqual(config["expectedactorid"], "mBRj1sgHTWmoPJEcb")
        self.assertIn("RUN-SUMMARY", json.dumps(blueprint))
        self.assertIn("ai_failed", json.dumps(blueprint))
        self.assertEqual(
            {route["flow"][0]["module"] for route in by_name["Update or append"]["routes"]},
            {"google-sheets:updateRow", "google-sheets:addRow"},
        )

        zapier = json.loads(
            (
                INTEGRATIONS
                / "zapier"
                / "ai-job-fit-scorer-template-spec.json"
            ).read_text()
        )
        self.assertEqual(zapier["distribution"], "editor-only")
        self.assertEqual(zapier["actions"][0]["build"], BUILD)
        self.assertEqual(zapier["publicationState"], "not-created-in-Zapier-editor")
        self.assertIn("named Google Sheets row created", zapier["requiredLiveTests"])

    def test_evidence_separates_actor_channel_and_destination_proof(self) -> None:
        evidence = json.loads(
            (INTEGRATIONS / "evidence" / "ai-job-fit-scorer.json").read_text()
        )
        self.assertEqual(evidence["schemaVersion"], "apify-integration-evidence-v1")
        self.assertEqual(
            evidence["actor"],
            {
                "id": "nomad-agent/ai-job-fit-scorer",
                "buildNumber": BUILD,
                "buildId": BUILD_ID,
            },
        )
        self.assertEqual(
            {
                item["runId"] for item in evidence["actorCanaries"].values()
            },
            {
                "KuuEnCoMfFbFj3z5R",
                "udTJyz3zJWOkKSNUS",
                "uqwj8p5qPU74JUyEo",
            },
        )
        for channel in evidence["channels"].values():
            self.assertTrue(channel["artifactValidated"])
            self.assertTrue(channel["liveActorRunTested"])
            self.assertFalse(channel["liveChannelTested"])
            self.assertFalse(channel["liveDestinationWriteTested"])

    def test_customer_docs_state_contract_price_and_caveats(self) -> None:
        text = (ROOT / "docs" / "ai-job-fit-scorer.md").read_text()
        normalized = " ".join(text.split())
        for required in (
            BUILD,
            BUILD_ID,
            "$0.02",
            "matchKey",
            "nomad-ai-job-fit-v1",
            "nomad-ai-job-fit-run-summary-v3",
            "rate-limit",
            "No zero-data-retention claim",
            "not hosted MCP",
            "named destination write",
        ):
            self.assertIn(required, normalized)


if __name__ == "__main__":
    unittest.main()
