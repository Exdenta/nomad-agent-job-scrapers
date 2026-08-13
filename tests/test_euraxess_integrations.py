from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
N8N_PATH = ROOT / "integrations" / "n8n" / "euraxess-jobs-to-google-sheets.json"
MAKE_PATH = (
    ROOT
    / "integrations"
    / "make"
    / "euraxess-jobs-to-google-sheets.blueprint.json"
)
MCP_DIR = ROOT / "integrations" / "mcp"
MCP_URL = "https://mcp.apify.com?tools=fetch-actor-details,call-actor,get-actor-run,get-dataset-items,get-key-value-store-record"


def walk_modules(flow: list[dict[str, object]]) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    for module in flow:
        modules.append(module)
        for route in module.get("routes", []):
            modules.extend(walk_modules(route["flow"]))
    return modules


class EuraxessIntegrationPackTests(unittest.TestCase):
    def test_n8n_is_bounded_strict_and_retry_free(self) -> None:
        workflow = json.loads(N8N_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}
        self.assertEqual(len(nodes), len(workflow["nodes"]))
        self.assertFalse(workflow["active"])
        self.assertNotIn("Retry requested?", nodes)
        self.assertNotIn("Wait before one retry", nodes)
        for source, outputs in workflow["connections"].items():
            self.assertIn(source, nodes)
            for branch in outputs["main"]:
                for target in branch:
                    self.assertIn(target["node"], nodes)

        config = {
            item["name"]: item["value"]
            for item in nodes["Configuration"]["parameters"]["assignments"][
                "assignments"
            ]
        }
        self.assertEqual(config["actorBuild"], "1.0.8")
        self.assertEqual(config["advancedInputJson"], "{}")
        self.assertEqual(config["maxItems"], 5)
        config["googleSpreadsheetId"] = "publicTemplateSpreadsheetId123"
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const config = JSON.parse(process.argv[2]);
const node = workflow.nodes.find(value => value.name === 'Validate template setup');
global.$input = { first: () => ({ json: config }), all: () => [{ json: config }] };
process.stdout.write(JSON.stringify(new Function(node.parameters.jsCode)()));
"""
        result = subprocess.run(
            ["node", "-e", script, str(N8N_PATH), json.dumps(config)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)[0]["json"]
        self.assertEqual(value["actorInput"]["schemaVersion"], "nomad-agent-job-search-input-v1")
        self.assertEqual(value["actorInput"]["maxItems"], 5)

        actor = nodes["Run Actor on Apify"]["parameters"]
        self.assertIn("euraxess-enrich-translate-normalize-scraper", actor["url"])
        self.assertEqual(actor["options"]["timeout"], 30_000)
        query = {item["name"]: item["value"] for item in actor["queryParameters"]["parameters"]}
        self.assertNotIn("waitForFinish", query)
        self.assertEqual(query["memory"], "512")
        poll = nodes["Poll same Actor run"]["parameters"]
        self.assertIn("actor-runs/", poll["url"])
        poll_query = {
            item["name"]: item["value"]
            for item in poll["queryParameters"]["parameters"]
        }
        self.assertEqual(poll_query, {"waitForFinish": "60"})
        self.assertEqual(poll["options"]["timeout"], 70_000)
        combined = json.dumps(workflow)
        self.assertIn("Validate terminal run", nodes)
        self.assertIn("RUN-SUMMARY", combined)
        self.assertIn("Validate run status", nodes)
        self.assertIn("Reconcile run status and dataset", nodes)
        self.assertIn("nomad-agent-fleet-run-summary-v2", combined)
        self.assertIn("identity.source=euraxess", combined)
        self.assertNotIn("nomad-agent-linkedin-run-summary-v1", combined)
        self.assertNotIn("token=", combined.lower())

    def test_n8n_advanced_input_passes_every_current_euraxess_feature(self) -> None:
        workflow = json.loads(N8N_PATH.read_text(encoding="utf-8"))
        nodes = {node["name"]: node for node in workflow["nodes"]}
        config = {
            item["name"]: item["value"]
            for item in nodes["Configuration"]["parameters"]["assignments"][
                "assignments"
            ]
        }
        config["googleSpreadsheetId"] = "publicTemplateSpreadsheetId123"
        advanced = {
            "keyword": "",
            "location": "Germany",
            "euraxessSearch": {
                "schemaVersion": "nomad-agent-euraxess-search-v1",
                "translateKeywords": True,
            },
            "postedWithin": "7d",
            "workArrangements": ["remote"],
            "filters": {
                "schemaVersion": "nomad-agent-job-filter-v1",
                "expression": {"field": "data.title", "operator": "contains", "value": "research"},
            },
            "maxItems": 0,
            "translateToEnglish": True,
            "aiEnrichment": {"enabled": True, "accuracy": "gold"},
            "includeRaw": True,
            "dedupe": {"enabled": True, "key": "profile-opaque"},
            "analyticsEnabled": True,
        }
        config["advancedInputJson"] = json.dumps(advanced)
        script = """
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const config = JSON.parse(process.argv[2]);
const node = workflow.nodes.find(value => value.name === 'Validate template setup');
global.$input = { first: () => ({ json: config }), all: () => [{ json: config }] };
process.stdout.write(JSON.stringify(new Function(node.parameters.jsCode)()));
"""
        result = subprocess.run(
            ["node", "-e", script, str(N8N_PATH), json.dumps(config)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        actor_input = json.loads(result.stdout)[0]["json"]["actorInput"]
        self.assertEqual(set(actor_input), {
            "schemaVersion", "keyword", "location", "euraxessSearch",
            "postedWithin", "workArrangements", "filters", "maxItems",
            "translateToEnglish", "aiEnrichment", "includeRaw", "dedupe",
            "analyticsEnabled",
        })
        for key, expected in advanced.items():
            self.assertEqual(actor_input[key], expected)

    def test_make_is_source_strict_and_has_no_paid_retry_route(self) -> None:
        blueprint = json.loads(MAKE_PATH.read_text(encoding="utf-8"))
        modules = walk_modules(blueprint["flow"])
        ids = [module["id"] for module in modules]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [1, 2, 3, 4, 8, 9, 10, 11, 12, 13])
        by_name = {
            module["metadata"]["designer"]["name"]: module for module in modules
        }
        config = {
            item["name"]: item["value"]
            for item in by_name["Configuration"]["mapper"]["variables"]
        }
        self.assertEqual(config["maxitems"], "5")
        self.assertEqual(config["actorbuild"], "1.0.8")
        self.assertNotIn("apifytaskid", config)
        rendered = json.dumps(blueprint)
        self.assertIn("RUN-SUMMARY", rendered)
        self.assertIn("nomad-agent-fleet-run-summary-v2", rendered)
        self.assertIn("sources.euraxess.status", rendered)
        self.assertIn("{{1.buildNumber}}", rendered)
        self.assertIn("{{2.actorbuild}}", rendered)
        self.assertIn('"b": "euraxess"', rendered)
        self.assertNotIn("runTask", rendered)
        self.assertNotIn("FunctionSleep", rendered)
        self.assertNotIn("nomad-agent-linkedin-run-summary-v1", rendered)
        self.assertNotIn("token", rendered.lower())

    def test_mcp_examples_are_scoped_bounded_and_credential_free(self) -> None:
        example = json.loads(
            (MCP_DIR / "examples" / "euraxess-search.mcp.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(example["actor"], "nomad-agent/euraxess-enrich-translate-normalize-scraper")
        self.assertEqual(example["callOptions"]["build"], "1.0.8")
        self.assertLessEqual(example["callOptions"]["maxItems"], 5)
        self.assertLessEqual(example["input"]["maxItems"], 5)
        self.assertFalse(example["input"]["translateToEnglish"])
        self.assertFalse(example["input"]["aiEnrichment"]["enabled"])
        self.assertFalse(example["input"]["dedupe"]["enabled"])
        self.assertFalse(example["input"]["analyticsEnabled"])

        config_dir = MCP_DIR / "configs" / "euraxess"
        codex = tomllib.loads((config_dir / "codex.oauth.toml").read_text())
        self.assertEqual(codex["mcp_servers"]["apify_euraxess_jobs"]["url"], MCP_URL)
        for filename in (
            "claude-code.oauth.json", "claude-code.token.json",
            "cursor.oauth.json", "cursor.token.json",
        ):
            value = json.loads((config_dir / filename).read_text(encoding="utf-8"))
            server = next(iter(value["mcpServers"].values()))
            self.assertEqual(server["url"], MCP_URL)
        combined = "\n".join(path.read_text() for path in config_dir.iterdir())
        self.assertNotIn("apify_api_", combined)

    def test_docs_and_airtable_state_the_private_validation_boundary(self) -> None:
        fields = json.loads(
            (ROOT / "integrations" / "airtable" / "airtable-fields.json").read_text()
        )
        source = next(field for field in fields["fields"] if field["name"] == "source")
        self.assertEqual(source["options"], ["linkedin", "euraxess"])
        docs = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "docs/euraxess.md",
                "integrations/n8n/README.md",
                "integrations/make/README.md",
                "integrations/mcp/README.md",
            )
        )
        self.assertIn("euraxess-jobs-to-google-sheets.json", docs)
        self.assertIn("euraxess-jobs-to-google-sheets.blueprint.json", docs)
        self.assertIn("offline-tested", docs)
        self.assertIn("private", docs.lower())


if __name__ == "__main__":
    unittest.main()
