from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / "integrations" / "n8n" / "linkedin-daily-job-alerts.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "linkedin-job.json"


class N8nAlertsPackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
        self.nodes = {node["name"]: node for node in self.workflow["nodes"]}

    def configuration(self) -> dict[str, object]:
        return {
            item["name"]: item["value"]
            for item in self.nodes["Alert configuration"]["parameters"][
                "assignments"
            ]["assignments"]
        }

    def run_code_node(
        self,
        node_name: str,
        values: list[dict[str, object]],
    ) -> subprocess.CompletedProcess[str]:
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const values = JSON.parse(process.argv[2]);
const node = workflow.nodes.find(value => value.name === process.argv[3]);
global.$input = {
  first: () => ({ json: values[0] }),
  all: () => values.map(value => ({ json: value })),
};
const output = new Function(node.parameters.jsCode)();
process.stdout.write(JSON.stringify(output));
"""
        return subprocess.run(
            [
                "node",
                "-e",
                script,
                str(WORKFLOW_PATH),
                json.dumps(values),
                node_name,
            ],
            capture_output=True,
            text=True,
        )

    def test_workflow_is_inactive_and_connections_resolve(self) -> None:
        self.assertFalse(self.workflow["active"])
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

    def test_safe_defaults_require_destination_and_dedupe_configuration(self) -> None:
        config = self.configuration()
        self.assertEqual(config["actorBuild"], "latest")
        self.assertEqual(config["maxItems"], 10)
        self.assertEqual(config["maxTotalChargeUsd"], 0.1)
        self.assertEqual(config["deliveryChannel"], "slack")

        rejected = self.run_code_node("Validate alert setup", [config])
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("replace deliveryTarget", rejected.stderr)

        config["deliveryTarget"] = "C0123456789"
        config["dedupeScope"] = "spain-typescript-daily"
        accepted = self.run_code_node("Validate alert setup", [config])
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        value = json.loads(accepted.stdout)[0]["json"]
        actor_input = value["actorInput"]
        self.assertEqual(actor_input["schemaVersion"], "nomad-agent-job-search-input-v1")
        self.assertEqual(
            actor_input["dedupe"],
            {"enabled": True, "key": "spain-typescript-daily"},
        )
        self.assertFalse(actor_input["translateToEnglish"])
        self.assertEqual(
            actor_input["aiEnrichment"], {"enabled": False, "accuracy": "silver"}
        )
        self.assertFalse(actor_input["includeRaw"])
        self.assertFalse(actor_input["analyticsEnabled"])

    def test_advanced_input_cannot_disable_alert_dedupe_or_raise_item_cap(self) -> None:
        config = self.configuration()
        config["deliveryTarget"] = "C0123456789"
        config["dedupeScope"] = "spain-typescript-daily"
        config["advancedInputJson"] = json.dumps(
            {
                "orderBy": "newest",
                "linkedinSearch": {
                    "schemaVersion": "nomad-agent-linkedin-search-v2",
                    "searches": [
                        {"keyword": "typescript", "location": "Spain"}
                    ],
                },
                "dedupe": {"enabled": False, "key": ""},
                "maxItems": 200,
            }
        )
        accepted = self.run_code_node("Validate alert setup", [config])
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        actor_input = json.loads(accepted.stdout)[0]["json"]["actorInput"]
        self.assertEqual(actor_input["maxItems"], 10)
        self.assertEqual(
            actor_input["dedupe"],
            {"enabled": True, "key": "spain-typescript-daily"},
        )
        self.assertIn("linkedinSearch", actor_input)

    def test_apify_call_is_exact_bounded_and_credential_safe(self) -> None:
        node = self.nodes["Find only new jobs"]
        params = node["parameters"]
        self.assertEqual(params["method"], "POST")
        self.assertEqual(params["authentication"], "genericCredentialType")
        self.assertEqual(params["genericAuthType"], "httpHeaderAuth")
        self.assertIn("run-sync-get-dataset-items", params["url"])
        self.assertNotIn("token=", params["url"].lower())
        query = {
            item["name"]: item["value"]
            for item in params["queryParameters"]["parameters"]
        }
        self.assertEqual(
            query["build"],
            "={{ $('Alert configuration').first().json.actorBuild }}",
        )
        self.assertIn("maxTotalChargeUsd", query)
        self.assertEqual(query["timeout"], "300")
        self.assertEqual(params["options"]["timeout"], 310_000)
        self.assertNotIn("credentials", node)

    def test_canonical_fixture_formats_source_faithful_alert(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        completed = self.run_code_node("Validate and format new jobs", [fixture])
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(len(output), 1)
        value = output[0]["json"]
        self.assertEqual(value["jobKey"], "linkedin:4446226935")
        self.assertIn(value["title"], value["message"])
        self.assertIn("Job key: linkedin:4446226935", value["message"])
        self.assertNotIn("description", value["message"].lower())

        duplicate = self.run_code_node(
            "Validate and format new jobs", [fixture, fixture]
        )
        self.assertEqual(duplicate.returncode, 0, duplicate.stderr)
        self.assertEqual(len(json.loads(duplicate.stdout)), 1)

    def test_missing_or_blank_external_id_fails_closed(self) -> None:
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        for external_id in (None, "", "   "):
            with self.subTest(external_id=external_id):
                record = deepcopy(fixture)
                if external_id is None:
                    record["identity"].pop("externalId", None)
                else:
                    record["identity"]["externalId"] = external_id
                completed = self.run_code_node(
                    "Validate and format new jobs", [record]
                )
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn(
                    "identity.externalId must be a non-empty string",
                    completed.stderr,
                )

    def test_exactly_one_selectable_destination_family_is_present(self) -> None:
        expected = {
            "Send Slack alert": "n8n-nodes-base.slack",
            "Send Telegram alert": "n8n-nodes-base.telegram",
            "Send email alert": "n8n-nodes-base.emailSend",
        }
        for name, node_type in expected.items():
            self.assertEqual(self.nodes[name]["type"], node_type)
            self.assertNotIn("credentials", self.nodes[name])

        telegram = self.nodes["Send Telegram alert"]["parameters"]
        self.assertEqual(telegram["resource"], "message")
        self.assertEqual(telegram["operation"], "sendMessage")
        self.assertEqual(telegram["additionalFields"]["parse_mode"], "HTML")
        self.assertFalse(telegram["additionalFields"]["appendAttribution"])
        self.assertIn("telegramMessage", telegram["text"])
        self.assertIn("Escape Telegram HTML", self.nodes)
        escaped = self.run_code_node(
            "Escape Telegram HTML", [{"message": "R&D <platform>"}]
        )
        self.assertEqual(escaped.returncode, 0, escaped.stderr)
        self.assertEqual(
            json.loads(escaped.stdout)[0]["json"]["telegramMessage"],
            "R&amp;D &lt;platform&gt;",
        )
        self.assertFalse(
            self.nodes["Send email alert"]["parameters"]["options"][
                "appendAttribution"
            ]
        )

        routing = self.workflow["connections"]["Validate and format new jobs"][
            "main"
        ][0]
        self.assertEqual(
            {target["node"] for target in routing},
            {"Deliver to Slack?", "Deliver to Telegram?", "Deliver by email?"},
        )
        rendered = json.dumps(self.workflow).lower()
        self.assertNotIn("apify_api_", rendered)
        self.assertNotIn("99.4", rendered)
        self.assertIn("not evidence of a live", rendered)


if __name__ == "__main__":
    unittest.main()
