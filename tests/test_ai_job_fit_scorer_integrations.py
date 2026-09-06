from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS = ROOT / "integrations"
BUILD = "0.1.22"
BUILD_ID = "XQhyxEg3YZ3NMel70"

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
        self.assertEqual(actor_input["resultMode"], "shortlist")
        self.assertEqual(actor_input["minDeliveryScore"], 2)
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
        self.assertEqual(mcp["actor"], "job-atlas/ai-job-fit-scorer")
        self.assertEqual(mcp["input"], actor_input)
        self.assertEqual(
            mcp["callOptions"],
            {"build": "latest", "maxItems": 5, "maxTotalChargeUsd": 0.10},
        )

        runner_path = (
            INTEGRATIONS / "api" / "ai-job-fit-scorer-run-and-fetch.mjs"
        )
        runner = runner_path.read_text()
        self.assertIn("const BUILD_SELECTOR = 'latest'", runner)
        self.assertIn("/v2/actors/${ACTOR}/runs", runner)
        self.assertNotIn("/v2/acts/${ACTOR}/runs", runner)
        self.assertIn("settlementDeadline", runner)
        self.assertIn("nomad-ai-job-fit-run-summary-v4", runner)
        self.assertIn("resultFilteredOut", runner)
        self.assertIn("minDeliveryScore", runner)
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

    def test_rest_starter_accepts_a_v4_filtered_empty_shortlist(self) -> None:
        module_url = (
            INTEGRATIONS / "api" / "ai-job-fit-scorer-run-and-fetch.mjs"
        ).as_uri()
        runner = f"""
process.env.APIFY_TOKEN = 'test-token';
globalThis.fetch = async (url) => {{
  const run = {{
    id:'run-v4', actId:'OZ919PaAyAbifOdcL', status:'SUCCEEDED', exitCode:0, buildNumber:'0.9.99', buildId:'build-future',
    defaultDatasetId:'dataset-v4', defaultKeyValueStoreId:'store-v4',
    chargedEventCounts:{{'job-fit-result':0}}
  }};
  let body;
  if (url.includes('/runs?')) {{
    if (new URL(url).searchParams.get('build') !== 'latest') throw new Error('start must select latest');
    body = {{data:run}};
  }} else if (url.includes('/actor-runs/run-v4')) {{
    body = {{data:run}};
  }} else if (url.includes('/records/RUN-SUMMARY')) {{
    body = {{
      schemaVersion:'nomad-ai-job-fit-run-summary-v4', status:'complete',
      cleanEmpty:false,
      actor:{{id:'OZ919PaAyAbifOdcL',runId:'run-v4',buildId:'build-future',buildNumber:'0.9.99'}},
      algorithm:{{name:'scoring-v3',interactionStateUsed:false}},
      parameters:{{resultMode:'shortlist',minDeliveryScore:2}},
      counts:{{evaluatedJobs:1,staticDropped:0,staticHeld:0,aiScored:1,
        aiFailed:0,resultFilteredOut:1,outputRows:0}},
      ai:{{providerCostLimitUsd:0.25,maxProviderAttempts:2,
        providerCostLimited:false,providerCostReservedUsd:0.01}},
      billing:{{eventName:'job-fit-result',unitPriceUsd:0.02,chargedCount:0,
        totalChargedUsd:0,budgetAuthorizedCount:1,budgetLimited:false}}
    }};
  }} else if (url.includes('/datasets/')) {{
    body = [];
  }} else {{
    throw new Error('unexpected URL ' + url);
  }}
  return {{ok:true,status:200,json:async()=>body}};
}};
await import({json.dumps(module_url)});
"""
        completed = subprocess.run(
            ["node", "--input-type=module", "-e", runner],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["runId"], "run-v4")
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["summary"]["counts"]["resultFilteredOut"], 1)
        self.assertEqual(result["summary"]["billing"]["chargedCount"], 0)
        self.assertEqual(result["buildNumber"], "0.9.99")
        self.assertEqual(result["buildId"], "build-future")
        for field, original, changed in [
            ("runId", "run-v4", "other-run"),
            ("buildId", "build-future", "other-build"),
            ("buildNumber", "0.9.99", "0.9.98"),
        ]:
            with self.subTest(mismatched_summary=field):
                actor_block = "actor:{id:'OZ919PaAyAbifOdcL',runId:'run-v4',buildId:'build-future',buildNumber:'0.9.99'}"
                mutated = runner.replace(actor_block, actor_block.replace(f"{field}:'{original}'", f"{field}:'{changed}'"))
                rejected = subprocess.run(["node", "--input-type=module", "-e", mutated], cwd=ROOT, capture_output=True, text=True)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn("does not match the exact run", rejected.stderr)


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
        summary_v3_schema = json.loads(
            (
                INTEGRATIONS
                / "shared"
                / "nomad-ai-job-fit-run-summary-v3.schema.json"
            ).read_text()
        )
        summary_v4_schema = json.loads(
            (
                INTEGRATIONS
                / "shared"
                / "nomad-ai-job-fit-run-summary-v4.schema.json"
            ).read_text()
        )
        self.assertFalse(fit_schema["additionalProperties"])
        self.assertEqual(set(fit_schema["properties"]), adapter.EXPECTED_KEYS)
        self.assertEqual(destination_schema["required"], list(adapter.COLUMNS))
        self.assertFalse(destination_schema["additionalProperties"])
        self.assertEqual(
            summary_v3_schema["properties"]["schemaVersion"]["const"],
            "nomad-ai-job-fit-run-summary-v3",
        )
        self.assertEqual(
            summary_v4_schema["properties"]["schemaVersion"]["const"],
            "nomad-ai-job-fit-run-summary-v4",
        )
        self.assertFalse(summary_v4_schema["additionalProperties"])
        self.assertEqual(
            summary_v4_schema["properties"]["parameters"]["properties"]["resultMode"]["enum"],
            ["shortlist", "audit"],
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
        self.assertEqual(assignments["actorBuild"], "latest")
        self.assertEqual(assignments["maxTotalChargeUsd"], 0.10)
        self.assertEqual(
            nodes["Start exact Actor build"]["parameters"]["url"],
            "https://api.apify.com/v2/acts/job-atlas~ai-job-fit-scorer/runs",
        )
        self.assertEqual(
            nodes["Upsert Google Sheets by matchKey"]["parameters"]["columns"]["matchingColumns"],
            ["matchKey"],
        )
        rendered = json.dumps(workflow)
        for required in (
            "RUN-SUMMARY",
            "nomad-ai-job-fit-run-summary-v3",
            "nomad-ai-job-fit-run-summary-v4",
            "resultFilteredOut",
            "minDeliveryScore",
            "job-fit-result",
            "ai_failed",
            "polling deadline exceeded",
        ):
            self.assertIn(required, rendered)

        runner = r"""
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const row = JSON.parse(process.argv[2]);
const summary = {
  schemaVersion:'nomad-ai-job-fit-run-summary-v4',
  parameters:{resultMode:'shortlist',minDeliveryScore:2},
  counts:{outputRows:1},
  billing:{chargedCount:1}
};
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

    def test_n8n_terminal_receipt_binds_resolved_build(self) -> None:
        path = INTEGRATIONS / "n8n" / "ai-job-fit-scorer-to-google-sheets.json"
        runner = r"""
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const started = JSON.parse(process.argv[2]);
const run = JSON.parse(process.argv[3]);
global.$input = {first: () => ({json:{data:run}})};
global.$ = () => ({first: () => ({json:{data:started}})});
const node = workflow.nodes.find(value => value.name === 'Validate terminal run');
process.stdout.write(JSON.stringify(new Function(node.parameters.jsCode)()));
"""
        run = dict(id="new-run", actId="OZ919PaAyAbifOdcL", buildId="new-build", buildNumber="0.9.99", status="SUCCEEDED", exitCode=0, defaultDatasetId="dataset", defaultKeyValueStoreId="store")
        for field in [None, "id", "actId", "buildId", "buildNumber"]:
            with self.subTest(changed=field):
                terminal = dict(run)
                if field:
                    terminal[field] = "changed"
                result = subprocess.run(["node", "-e", runner, str(path), json.dumps(run), json.dumps(terminal)], capture_output=True, text=True)
                if field:
                    self.assertNotEqual(result.returncode, 0)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)[0]["json"]["buildNumber"], "0.9.99")

    def test_n8n_v4_summary_validation_rejects_count_and_audit_drift(self) -> None:
        path = INTEGRATIONS / "n8n" / "ai-job-fit-scorer-to-google-sheets.json"
        runner = r"""
const fs = require('fs');
const workflow = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const summary = JSON.parse(process.argv[2]);
const node = workflow.nodes.find(value => value.name === 'Validate RUN-SUMMARY');
global.$input = {first: () => ({json: summary})};
global.$ = () => ({first: () => ({json: {actorId:'OZ919PaAyAbifOdcL',runId:'run-new',buildId:'new-build',buildNumber:'0.9.99'}})});
try {
  const result = new Function(node.parameters.jsCode)();
  process.stdout.write(JSON.stringify(result));
} catch (error) {
  process.stderr.write(error.message);
  process.exitCode = 1;
}
"""

        def validate(summary: dict[str, object]) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                ["node", "-e", runner, str(path), json.dumps(summary)],
                capture_output=True,
                text=True,
                check=False,
            )

        base = {
            "schemaVersion": "nomad-ai-job-fit-run-summary-v4",
            "actor": {"id":"OZ919PaAyAbifOdcL","runId":"run-new","buildId":"new-build","buildNumber":"0.9.99"},
            "status": "complete",
            "cleanEmpty": False,
            "algorithm": {"name": "scoring-v3", "interactionStateUsed": False},
            "parameters": {"resultMode": "shortlist", "minDeliveryScore": 2},
            "counts": {
                "evaluatedJobs": 4,
                "staticDropped": 1,
                "staticHeld": 1,
                "aiScored": 2,
                "aiFailed": 0,
                "resultFilteredOut": 3,
                "outputRows": 1,
            },
            "ai": {
                "providerCostLimitUsd": 0.25,
                "providerCostReservedUsd": 0.01,
                "providerCostLimited": False,
                "maxProviderAttempts": 2,
            },
            "billing": {
                "eventName": "job-fit-result",
                "unitPriceUsd": 0.02,
                "chargedCount": 1,
                "totalChargedUsd": 0.02,
                "budgetAuthorizedCount": 4,
                "budgetLimited": False,
            },
        }
        completed = validate(base)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        for field in ["id", "runId", "buildId", "buildNumber"]:
            mismatch = json.loads(json.dumps(base))
            mismatch["actor"][field] = "mismatched"
            rejected = validate(mismatch)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("exact run and resolved build", rejected.stderr)

        count_drift = json.loads(json.dumps(base))
        count_drift["counts"]["resultFilteredOut"] = 2
        completed = validate(count_drift)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("filtered and output counts", completed.stderr)

        audit = json.loads(json.dumps(base))
        audit["parameters"]["resultMode"] = "audit"
        audit["counts"].update(
            {
                "staticDropped": 1,
                "staticHeld": 1,
                "aiScored": 1,
                "aiFailed": 1,
                "resultFilteredOut": 0,
                "outputRows": 4,
            }
        )
        audit["billing"].update({"chargedCount": 3, "totalChargedUsd": 0.06})
        completed = validate(audit)
        self.assertEqual(completed.returncode, 0, completed.stderr)

        incomplete_audit = json.loads(json.dumps(audit))
        incomplete_audit["counts"].update({"resultFilteredOut": 1, "outputRows": 3})
        incomplete_audit["billing"].update(
            {"chargedCount": 2, "totalChargedUsd": 0.04}
        )
        completed = validate(incomplete_audit)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("audit counts", completed.stderr)

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
        self.assertNotIn("expectedbuild", config)
        self.assertEqual(config["expectedactorid"], "OZ919PaAyAbifOdcL")
        rendered_blueprint = json.dumps(blueprint)
        self.assertIn("RUN-SUMMARY", rendered_blueprint)
        self.assertIn("nomad-ai-job-fit-run-summary-v4", rendered_blueprint)
        self.assertIn("shortlist", rendered_blueprint)
        self.assertIn("audit", rendered_blueprint)
        self.assertIn("ai_failed", rendered_blueprint)
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
        self.assertEqual(zapier["actions"][0]["build"], "latest")
        steps = {action["step"]: action for action in zapier["actions"]}
        self.assertEqual(steps[2]["url"], "https://api.apify.com/v2/actor-runs/{{1.startedRun.id}}")
        self.assertEqual(steps[2]["outputName"], "run")
        self.assertEqual(steps[3]["url"], "https://api.apify.com/v2/key-value-stores/{{2.run.defaultKeyValueStoreId}}/records/RUN-SUMMARY")
        self.assertEqual(steps[3]["outputName"], "summary")
        self.assertEqual(steps[4]["dataset"], "{{2.run.defaultDatasetId}}")
        self.assertEqual(steps[5]["bindings"]["summary"], "{{3.summary}}")
        for field, run_field in [("id", "actId"), ("runId", "id"), ("buildId", "buildId"), ("buildNumber", "buildNumber")]:
            self.assertIn(f"summary.actor.{field} == run.{run_field}", steps[5]["conditions"])
        self.assertGreater(steps[6]["step"], steps[5]["step"])

        self.assertEqual(zapier["actions"][0]["input"]["resultMode"], "shortlist")
        self.assertEqual(zapier["actions"][0]["input"]["minDeliveryScore"], 2)
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
                item["runId"] for item in evidence["historicalActorCanaries"].values()
            },
            {
                "fhMYR6bzdbzdNl84y",
                "wkk8NkZv43JEIcv3m",
                "lIpiLiudBukaaFI7d",
                "vzhqlbVeXhp5tKs4N",
            },
        )
        default_demo = evidence["historicalActorCanaries"]["defaultShortlist"]
        self.assertEqual(default_demo["runId"], "fhMYR6bzdbzdNl84y")
        self.assertEqual(default_demo["resolvedBuildNumber"], "0.1.12")
        self.assertEqual(default_demo["resolvedBuildId"], "eLfTnCWohYVKejvsD")
        self.assertEqual(default_demo["runSummarySchema"], "nomad-ai-job-fit-run-summary-v4")
        self.assertEqual(default_demo["resultMode"], "shortlist")
        self.assertEqual(default_demo["minDeliveryScore"], 2)
        self.assertEqual(default_demo["aiScored"], 3)
        self.assertEqual(default_demo["resultFilteredOut"], 2)
        self.assertEqual(default_demo["datasetRows"], 1)
        self.assertEqual(default_demo["maxTotalChargeUsd"], 0.06)
        self.assertEqual(default_demo["chargedEventCounts"], {"job-fit-result": 1})
        self.assertEqual(
            set(default_demo["sourceStatuses"].values()), {"succeeded"}
        )
        self.assertEqual(default_demo["warnings"], [])
        self.assertEqual(
            evidence["historicalActorCanaries"]["auditRetainsHold"]["runId"],
            "lIpiLiudBukaaFI7d",
        )
        self.assertEqual(evidence["deployment"]["latestBuildNumber"], "0.1.24")
        self.assertEqual(evidence["deployment"]["latestBuildId"], evidence["releaseActorRun"]["resolvedBuildId"])
        self.assertEqual(evidence["releaseActorRun"]["selector"], "latest")
        self.assertEqual(evidence["releaseActorRun"]["chargedEventCounts"]["job-fit-result"], evidence["releaseActorRun"]["datasetRows"])
        self.assertEqual(
            evidence["historicalDeployment"]["documentationSmoke"]["chargedEventCounts"],
            {"job-fit-result": 0},
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
            "latest",
            BUILD_ID,
            "$0.02",
            "matchKey",
            "nomad-ai-job-fit-v1",
            "nomad-ai-job-fit-run-summary-v3",
            "nomad-ai-job-fit-run-summary-v4",
            "shortlist",
            "audit",
            "minDeliveryScore",
            "rate-limit",
            "No zero-data-retention claim",
            "not hosted MCP",
            "named destination write",
            "all ten adapters",
        ):
            self.assertIn(required, normalized)


if __name__ == "__main__":
    unittest.main()
