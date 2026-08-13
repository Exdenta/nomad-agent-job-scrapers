from __future__ import annotations

import csv
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

    def run_terminal_node(
        self,
        run: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const run = JSON.parse(process.argv[2]);
global.$input = { first: () => ({ json: { data: run } }) };
global.$ = (name) => {
  if (name === 'Configuration') return { first: () => ({ json: { actorBuild: '0.6.42' } }) };
  throw new Error(`unexpected node reference: ${name}`);
};
const node = workflow.nodes.find(value => value.name === 'Validate terminal run');
const output = new Function(node.parameters.jsCode)();
process.stdout.write(JSON.stringify(output));
"""
        return subprocess.run(
            ["node", "-e", script, str(WORKFLOW_PATH), json.dumps(run)],
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
                "Select current run",
                "Run is terminal?",
                "Poll same Actor run",
                "Validate terminal run",
                "Read factual RUN-SUMMARY",
                "Validate run status",
                "Retry requested?",
                "Wait before one retry",
                "Get delivery run jobs",
                "Reconcile run status and dataset",
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
            "Select current run",
        )
        self.assertEqual(
            self.workflow["connections"]["Select current run"]["main"][0][0][
                "node"
            ],
            "Run is terminal?",
        )
        self.assertEqual(
            self.workflow["connections"]["Run is terminal?"]["main"][0][0][
                "node"
            ],
            "Validate terminal run",
        )
        self.assertEqual(
            self.workflow["connections"]["Run is terminal?"]["main"][1][0][
                "node"
            ],
            "Poll same Actor run",
        )
        self.assertEqual(
            self.workflow["connections"]["Poll same Actor run"]["main"][0][0][
                "node"
            ],
            "Select current run",
        )
        self.assertEqual(
            self.workflow["connections"]["Validate terminal run"]["main"][0][0]["node"],
            "Read factual RUN-SUMMARY",
        )
        self.assertEqual(
            self.workflow["connections"]["Read factual RUN-SUMMARY"]["main"][0][0]["node"],
            "Validate run status",
        )
        self.assertEqual(
            self.workflow["connections"]["Validate run status"]["main"][0][0]["node"],
            "Retry requested?",
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
            self.workflow["connections"]["Wait before one retry"]["main"][0][0]["node"],
            "Run Actor on Apify",
        )
        self.assertEqual(
            self.workflow["connections"]["Get delivery run jobs"]["main"][0][0]["node"],
            "Reconcile run status and dataset",
        )
        self.assertEqual(
            self.workflow["connections"]["Reconcile run status and dataset"]["main"][0][0]["node"],
            "Validate and flatten jobs",
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
        self.assertEqual(
            params["jsonBody"],
            "={{ $('Validate template setup').first().json.actorInput }}",
        )
        query = {
            item["name"]: item["value"]
            for item in params["queryParameters"]["parameters"]
        }
        self.assertNotIn("waitForFinish", query)
        self.assertIn("maxTotalChargeUsd", query)
        self.assertEqual(
            query["build"], "={{ $('Configuration').first().json.actorBuild }}"
        )
        poll = self.nodes["Poll same Actor run"]["parameters"]
        self.assertIn("actor-runs/", poll["url"])
        self.assertIn("$json.id", poll["url"])
        poll_query = {
            item["name"]: item["value"]
            for item in poll["queryParameters"]["parameters"]
        }
        self.assertEqual(poll_query, {"waitForFinish": "60"})
        self.assertEqual(poll["options"]["timeout"], 70_000)

        assignments = {
            item["name"]: item["value"]
            for item in self.nodes["Configuration"]["parameters"]["assignments"][
                "assignments"
            ]
        }
        self.assertEqual(assignments["actorBuild"], "0.6.42")
        self.assertEqual(assignments["advancedInputJson"], "{}")
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
        self.assertIn("maxItems must be an integer from 0 to 200", script)
        self.assertIn("maxRescheduleRetries must be 0 or 1", script)
        self.assertIn("actorBuild must be a pinned version", script)
        self.assertIn("advancedInputJson", script)
        self.assertIn("actorInput", script)
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
        value = json.loads(accepted.stdout)[0]["json"]
        self.assertEqual(
            {key: value[key] for key in config},
            config,
        )
        self.assertEqual(value["actorInput"], {
            "schemaVersion": "nomad-agent-job-search-input-v1",
            "keyword": "software engineer",
            "location": "United States",
            "postedWithin": "30d",
            "workArrangements": [],
            "maxItems": 1,
            "translateToEnglish": False,
            "aiEnrichment": {"enabled": False, "accuracy": "silver"},
            "includeRaw": False,
            "dedupe": {"enabled": False, "key": ""},
            "analyticsEnabled": False,
        })

    def test_advanced_input_json_passes_every_current_linkedin_feature(self) -> None:
        config = {
            item["name"]: item["value"]
            for item in self.nodes["Configuration"]["parameters"]["assignments"][
                "assignments"
            ]
        }
        config["googleSpreadsheetId"] = "publicTemplateSpreadsheetId123"
        advanced = {
            "keyword": "",
            "location": "",
            "linkedinSearch": {
                "schemaVersion": "nomad-agent-linkedin-search-v1",
                "searches": [{"keyword": "data engineer", "location": "Spain"}],
                "orderBy": "newest",
            },
            "strictGeography": {
                "schemaVersion": "nomad-agent-linkedin-strict-geography-v1",
                "countries": ["ES"],
                "unknownPolicy": "exclude",
            },
            "filters": {
                "schemaVersion": "nomad-agent-job-filter-v1",
                "expression": {"field": "data.title", "operator": "contains", "value": "engineer"},
            },
            "companyProfileEnrichment": True,
            "companyFilters": {
                "schemaVersion": "nomad-agent-linkedin-company-filter-v1",
                "expression": {"field": "industry", "operator": "contains", "value": "software"},
                "unknownPolicy": "exclude",
            },
            "postedWithin": "7d",
            "workArrangements": ["remote", "hybrid"],
            "maxItems": 0,
            "translateToEnglish": True,
            "aiEnrichment": {"enabled": True, "accuracy": "gold"},
            "includeRaw": True,
            "dedupe": {"enabled": True, "key": "profile-opaque"},
            "analyticsEnabled": True,
        }
        config["advancedInputJson"] = json.dumps(advanced)
        accepted = self.run_validation_node(config)
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        actor_input = json.loads(accepted.stdout)[0]["json"]["actorInput"]
        self.assertEqual(set(actor_input), {
            "schemaVersion", "keyword", "location", "linkedinSearch",
            "strictGeography", "filters", "companyProfileEnrichment",
            "companyFilters", "postedWithin", "workArrangements", "maxItems",
            "translateToEnglish", "aiEnrichment", "includeRaw", "dedupe",
            "analyticsEnabled",
        })
        for key, expected in advanced.items():
            self.assertEqual(actor_input[key], expected)

    def test_terminal_success_selects_the_exact_run_dataset(self) -> None:
        completed = self.run_terminal_node({
            "id": "run-1",
            "status": "SUCCEEDED",
            "exitCode": 0,
            "buildNumber": "0.6.42",
            "defaultDatasetId": "dataset-1",
        })
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)[0]["json"]
        self.assertEqual(value["runId"], "run-1")
        self.assertEqual(value["defaultDatasetId"], "dataset-1")

    def test_failed_or_wrong_build_run_is_not_retried_or_delivered(self) -> None:
        failed = self.run_terminal_node({
            "id": "run-2", "status": "FAILED", "exitCode": 1,
            "buildNumber": "0.6.42", "defaultDatasetId": "dataset-2",
        })
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("failed terminal runs cannot be retried", failed.stderr)
        wrong_build = self.run_terminal_node({
            "id": "run-3", "status": "SUCCEEDED", "exitCode": 0,
            "buildNumber": "0.6.36", "defaultDatasetId": "dataset-3",
        })
        self.assertNotEqual(wrong_build.returncode, 0)
        self.assertIn("expected 0.6.42", wrong_build.stderr)

    def test_workflow_uses_v4_and_one_retry_nodes(self) -> None:
        rendered = json.dumps(self.workflow)
        self.assertIn("key-value-store/records/RUN-SUMMARY", rendered)
        self.assertIn("nomad-agent-run-summary-v4", rendered)
        self.assertNotIn("nomad-agent-fleet-run-summary-v2", rendered)
        self.assertNotIn("sources.linkedin", rendered)
        self.assertIn("maxRescheduleRetries", rendered)
        self.assertIn("Wait before one retry", self.nodes)
        self.assertIn("Retry requested?", self.nodes)
        self.assertIn("Poll same Actor run", self.nodes)
        self.assertEqual(
            self.nodes["Run is terminal?"]["type"], "n8n-nodes-base.if"
        )
        dataset = self.nodes["Get delivery run jobs"]
        self.assertIn("actor-runs/", dataset["parameters"]["url"])
        self.assertIn("/dataset/items", dataset["parameters"]["url"])
        status = self.nodes["Validate run status"]["parameters"]["jsCode"]
        self.assertIn("retry.recommended", status)
        self.assertIn("retryAttempt < retryLimit", status)
        self.assertIn("closed v4 object", status)
        reconcile = self.nodes["Reconcile run status and dataset"]["parameters"]["jsCode"]
        self.assertIn("runSummary.delivered", reconcile)

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
            "Poll same Actor run",
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
        self.assertIn("0.6.42", listing)
        self.assertIn("destination-specific live test", listing)
        self.assertIn("no separate delivery cache", listing)


if __name__ == "__main__":
    unittest.main()
