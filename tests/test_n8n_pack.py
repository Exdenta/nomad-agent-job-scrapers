from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = (
    ROOT
    / "integrations"
    / "n8n"
    / "linkedin-jobs-to-google-sheets.json"
)
COLUMNS_PATH = ROOT / "integrations" / "n8n" / "google-sheets-columns.csv"
FLAT_SCHEMA_PATH = ROOT / "integrations" / "shared" / "flat-job-v1.schema.json"
LISTING_PATH = ROOT / "integrations" / "n8n" / "template-listing.md"


class N8nPackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.nodes = {node["name"]: node for node in self.workflow["nodes"]}

    def run_validation_node(self, config: dict[str, object]) -> subprocess.CompletedProcess[str]:
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const config = JSON.parse(process.argv[2]);
const node = workflow.nodes.find(value => value.name === 'Validate template setup');
global.$input = {
  first: () => ({ json: config }),
  all: () => [{ json: config }],
};
const output = new Function(node.parameters.jsCode)();
process.stdout.write(JSON.stringify(output));
"""
        return subprocess.run(
            ["node", "-e", script, str(WORKFLOW_PATH), json.dumps(config)],
            capture_output=True,
            text=True,
        )

    def run_retry_node(
        self,
        run: dict[str, object],
        summary: dict[str, object],
        *,
        run_index: int = 0,
        retry_limit: int = 1,
    ) -> subprocess.CompletedProcess[str]:
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const run = JSON.parse(process.argv[2]);
const summary = JSON.parse(process.argv[3]);
global.$runIndex = Number(process.argv[4]);
global.$input = { first: () => ({ json: summary }) };
global.$ = (name) => {
  if (name === 'Run Actor on Apify') return { item: { json: { data: run } } };
  if (name === 'Configuration') return { first: () => ({ json: { maxRescheduleRetries: Number(process.argv[5]) } }) };
  throw new Error(`unexpected node reference: ${name}`);
};
const node = workflow.nodes.find(value => value.name === 'Evaluate retry recommendation');
const output = new Function(node.parameters.jsCode)();
process.stdout.write(JSON.stringify(output));
"""
        return subprocess.run(
            [
                "node",
                "-e",
                script,
                str(WORKFLOW_PATH),
                json.dumps(run),
                json.dumps(summary),
                str(run_index),
                str(retry_limit),
            ],
            capture_output=True,
            text=True,
        )

    def test_workflow_has_unique_nodes_and_valid_connections(self) -> None:
        self.assertEqual(len(self.nodes), len(self.workflow["nodes"]))
        ids = [node["id"] for node in self.workflow["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for source, outputs in self.workflow["connections"].items():
            self.assertIn(source, self.nodes)
            for branch in outputs["main"]:
                for target in branch:
                    self.assertIn(target["node"], self.nodes)

        self.assertEqual(
            self.nodes["Every day at 08:00 UTC"]["type"],
            "n8n-nodes-base.scheduleTrigger",
        )
        self.assertEqual(
            self.nodes["Run manually"]["type"],
            "n8n-nodes-base.manualTrigger",
        )
        self.assertFalse(self.workflow["active"])
        self.assertEqual(
            set(self.nodes),
            {
                "Every day at 08:00 UTC",
                "Run manually",
                "Configuration",
                "Validate template setup",
                "Run Actor on Apify",
                "Read RUN-SUMMARY",
                "Evaluate retry recommendation",
                "Retry requested?",
                "Wait before one retry",
                "Get delivery run jobs",
                "Validate and flatten jobs",
                "Upsert jobs in Google Sheets",
                "Setup notes",
            },
        )
        self.assertEqual(
            self.workflow["connections"]["Configuration"]["main"][0][0]["node"],
            "Validate template setup",
        )
        self.assertEqual(
            self.workflow["connections"]["Validate template setup"]["main"][0][0][
                "node"
            ],
            "Run Actor on Apify",
        )
        self.assertEqual(
            self.workflow["connections"]["Run Actor on Apify"]["main"][0][0][
                "node"
            ],
            "Read RUN-SUMMARY",
        )
        self.assertEqual(
            self.workflow["connections"]["Retry requested?"]["main"][0][0]["node"],
            "Wait before one retry",
        )
        self.assertEqual(
            self.workflow["connections"]["Retry requested?"]["main"][1][0]["node"],
            "Get delivery run jobs",
        )
        self.assertEqual(
            self.workflow["connections"]["Validate and flatten jobs"]["main"][0][0]["node"],
            "Upsert jobs in Google Sheets",
        )
        self.assertNotIn("Upsert jobs in Google Sheets", self.workflow["connections"])

    def test_apify_request_uses_header_auth_and_bounded_v1_input(self) -> None:
        node = self.nodes["Run Actor on Apify"]
        params = node["parameters"]
        self.assertEqual(params["method"], "POST")
        self.assertEqual(params["authentication"], "genericCredentialType")
        self.assertEqual(params["genericAuthType"], "httpHeaderAuth")
        self.assertIn(
            "nomad-agent~linkedin-enrich-translate-normalize-scraper/"
            "runs",
            params["url"],
        )
        self.assertNotIn("token=", params["url"].lower())
        body = params["jsonBody"]
        self.assertIn("nomad-agent-job-search-input-v1", body)
        self.assertIn("translateToEnglish: false", body)
        self.assertIn(
            "aiEnrichment: { enabled: false, accuracy: 'silver' }", body,
        )
        self.assertIn("includeRaw: false", body)
        query = {
            item["name"]: item["value"]
            for item in params["queryParameters"]["parameters"]
        }
        self.assertEqual(query["waitForFinish"], "300")
        self.assertIn("maxTotalChargeUsd", query)
        self.assertEqual(
            query["build"], "={{ $('Configuration').first().json.actorBuild }}"
        )

        assignments = {
            item["name"]: item["value"]
            for item in self.nodes["Configuration"]["parameters"]["assignments"][
                "assignments"
            ]
        }
        self.assertEqual(assignments["actorBuild"], "0.6.19")
        self.assertEqual(assignments["maxItems"], 1)
        self.assertEqual(assignments["maxRescheduleRetries"], 1)
        self.assertEqual(
            assignments["googleSpreadsheetId"],
            "REPLACE_WITH_GOOGLE_SPREADSHEET_ID",
        )

    def test_public_template_validates_setup_before_paid_actor_run(self) -> None:
        validation = self.nodes["Validate template setup"]
        self.assertEqual(validation["type"], "n8n-nodes-base.code")
        script = validation["parameters"]["jsCode"]
        self.assertIn("REPLACE_WITH_", script)
        self.assertIn("maxItems must be an integer from 1 to 100", script)
        self.assertIn("maxRescheduleRetries must be 0 or 1", script)
        self.assertIn("actorBuild must be a pinned version", script)
        self.assertIn("remote", script)
        self.assertIn("hybrid", script)
        self.assertIn("onsite", script)

        config = {
            item["name"]: item["value"]
            for item in self.nodes["Configuration"]["parameters"]["assignments"][
                "assignments"
            ]
        }
        rejected = self.run_validation_node(config)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("replace googleSpreadsheetId", rejected.stderr)

        config["googleSpreadsheetId"] = "publicTemplateSpreadsheetId123"
        accepted = self.run_validation_node(config)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertEqual(json.loads(accepted.stdout)[0]["json"], config)

    def test_structured_run_summary_retries_once_and_only_when_blocked(self) -> None:
        not_before = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
        retry_summary = {
            "schemaVersion": "nomad-agent-linkedin-run-summary-v1",
            "resultState": "blocked",
            "blocked": True,
            "reschedule": {
                "recommended": True,
                "afterSeconds": 60,
                "notBefore": not_before,
            },
        }
        run = {
            "id": "run-1",
            "status": "SUCCEEDED",
            "defaultDatasetId": "dataset-1",
        }

        first = self.run_retry_node(run, retry_summary)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_value = json.loads(first.stdout)[0]["json"]
        self.assertTrue(first_value["retryRecommended"])
        self.assertGreaterEqual(first_value["retryAfterSeconds"], 1)
        self.assertLessEqual(first_value["retryAfterSeconds"], 60)

        second = self.run_retry_node(run, retry_summary, run_index=1)
        self.assertEqual(second.returncode, 0, second.stderr)
        second_value = json.loads(second.stdout)[0]["json"]
        self.assertFalse(second_value["retryRecommended"])
        self.assertTrue(second_value["retryExhausted"])

        no_retry = self.run_retry_node(run, {})
        self.assertEqual(no_retry.returncode, 0, no_retry.stderr)
        self.assertFalse(json.loads(no_retry.stdout)[0]["json"]["retryRecommended"])

    def test_failed_run_is_not_blindly_retried(self) -> None:
        failed = self.run_retry_node(
            {"id": "run-2", "status": "FAILED"},
            {},
        )
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("automatic retry is allowed only after SUCCEEDED", failed.stderr)

    def test_retry_nodes_use_kvs_then_wait_then_fetch_delivery_dataset(self) -> None:
        summary = self.nodes["Read RUN-SUMMARY"]
        self.assertIn("key-value-store/records/RUN-SUMMARY", summary["parameters"]["url"])
        self.assertTrue(
            summary["parameters"]["options"]["response"]["response"]["neverError"]
        )
        wait = self.nodes["Wait before one retry"]
        self.assertEqual(wait["type"], "n8n-nodes-base.wait")
        self.assertEqual(wait["parameters"]["unit"], "seconds")
        self.assertIn("retryAfterSeconds", wait["parameters"]["amount"])
        dataset = self.nodes["Get delivery run jobs"]
        self.assertIn("actor-runs/", dataset["parameters"]["url"])
        self.assertIn("/dataset/items", dataset["parameters"]["url"])

    def test_flattening_and_within_run_dedupe_are_contract_bound(self) -> None:
        flatten = self.nodes["Validate and flatten jobs"]["parameters"]["jsCode"]
        self.assertIn("nomad-agent-job-v1", flatten)
        self.assertIn("nomad-agent-flat-job-v1", flatten)
        self.assertIn("unexpected roots", flatten)
        self.assertIn("`${identity.source}:${stablePart}`", flatten)
        self.assertIn("JSON.stringify(value)", flatten)
        self.assertIn("const seen = new Set()", flatten)

    def test_embedded_flatten_javascript_matches_shared_fixture(self) -> None:
        fixture_path = ROOT / "tests" / "fixtures" / "linkedin-job.json"
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const record = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const node = workflow.nodes.find(value => value.name === 'Validate and flatten jobs');
global.$input = { all: () => [{ json: record }] };
const output = new Function(node.parameters.jsCode)();
process.stdout.write(JSON.stringify(output));
"""
        completed = subprocess.run(
            ["node", "-e", script, str(WORKFLOW_PATH), str(fixture_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        flattened = json.loads(completed.stdout)[0]["json"]
        flat_schema = json.loads(FLAT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(list(flattened), flat_schema["required"])
        self.assertEqual(flattened["jobKey"], "linkedin:4446226935")
        self.assertEqual(flattened["workArrangements"], '["hybrid"]')
        self.assertEqual(flattened["contractTypes"], "[]")
        self.assertIsNone(flattened["descriptionText"])

    def test_google_sheet_mapping_matches_flat_schema(self) -> None:
        flat_schema = json.loads(FLAT_SCHEMA_PATH.read_text(encoding="utf-8"))
        expected = flat_schema["required"]
        with COLUMNS_PATH.open(newline="", encoding="utf-8") as handle:
            headers = next(csv.reader(handle))
        self.assertEqual(headers, expected)

        node = self.nodes["Upsert jobs in Google Sheets"]
        self.assertEqual(node["type"], "n8n-nodes-base.googleSheets")
        self.assertEqual(node["typeVersion"], 4.7)
        columns = node["parameters"]["columns"]
        self.assertEqual(node["parameters"]["operation"], "appendOrUpdate")
        self.assertEqual(columns["mappingMode"], "autoMapInputData")
        self.assertEqual(columns["matchingColumns"], ["jobKey"])
        self.assertEqual([field["id"] for field in columns["schema"]], expected)

    def test_basic_template_has_no_notifications_state_or_credentials(self) -> None:
        for name in (
            "Run Actor on Apify",
            "Read RUN-SUMMARY",
            "Get delivery run jobs",
        ):
            self.assertNotIn("credentials", self.nodes[name])
        rendered = json.dumps(self.workflow).lower()
        self.assertNotIn("token=", rendered)
        self.assertNotIn("apify_api_token", rendered)
        self.assertNotIn("@gmail.com", rendered)
        self.assertNotIn("@googlemail.com", rendered)
        self.assertNotIn("telegram", rendered)
        self.assertNotIn("notification digest", rendered)
        self.assertNotIn("$getworkflowstaticdata", rendered)
        self.assertNotIn("previously delivered", rendered)
        self.assertNotIn("remember delivered", rendered)

    def test_public_listing_matches_live_validation_boundary(self) -> None:
        listing = LISTING_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "Find and save new LinkedIn jobs to Google Sheets with Apify", listing
        )
        self.assertIn("n8n Cloud", listing)
        self.assertIn("0.6.19", listing)
        self.assertIn("The published schedule was not", listing)
        self.assertIn("no separate delivery cache", listing)


if __name__ == "__main__":
    unittest.main()
