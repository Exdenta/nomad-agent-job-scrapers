from __future__ import annotations

import csv
import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_PATH = (
    ROOT
    / "integrations"
    / "make"
    / "linkedin-jobs-to-google-sheets.blueprint.json"
)
COLUMNS_PATH = ROOT / "integrations" / "make" / "google-sheets-columns.csv"
FLAT_SCHEMA_PATH = ROOT / "integrations" / "shared" / "flat-job-v1.schema.json"


def walk_modules(flow: list[dict[str, object]]) -> list[dict[str, object]]:
    modules: list[dict[str, object]] = []
    for module in flow:
        modules.append(module)
        for route in module.get("routes", []):
            modules.extend(walk_modules(route["flow"]))
    return modules


class MakePackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.blueprint = json.loads(BLUEPRINT_PATH.read_text(encoding="utf-8"))
        self.modules = walk_modules(self.blueprint["flow"])
        self.by_name = {
            module["metadata"]["designer"]["name"]: module
            for module in self.modules
        }

    def test_blueprint_has_current_make_envelope_and_unique_modules(self) -> None:
        self.assertEqual(
            set(self.blueprint),
            {"name", "flow", "metadata"},
        )
        self.assertEqual(
            self.blueprint["name"],
            "Find and upsert LinkedIn jobs to Google Sheets with Apify",
        )
        ids = [module["id"] for module in self.modules]
        self.assertEqual(ids, list(range(1, 9)))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(self.blueprint["metadata"]["scenario"]["sequential"])
        self.assertFalse(self.blueprint["metadata"]["instant"])

        self.assertEqual(
            [module["module"] for module in self.blueprint["flow"]],
            [
                "util:BasicTrigger",
                "apify:runActorNew",
                "apify:fetchDatasetItems",
                "code:ExecuteCode",
                "google-sheets:filterRows",
                "builtin:BasicRouter",
            ],
        )

    def test_actor_request_is_pinned_bounded_and_credential_free(self) -> None:
        node = self.by_name["Run LinkedIn jobs Actor"]
        mapper = node["mapper"]
        self.assertEqual(mapper["actorId"], "kqIdAA2UQiPdOtzEB")
        self.assertTrue(mapper["runSync"])
        self.assertEqual(mapper["build"], "{{1.actorBuild}}")
        self.assertEqual(mapper["timeout"], 120)
        self.assertEqual(mapper["memory"], 512)
        self.assertEqual(node["parameters"], {})

        body = mapper["inputBodykqIdAA2UQiPdOtzEB"]
        self.assertIn("nomad-agent-job-search-input-v1", body)
        self.assertIn('"translateToEnglish": false', body)
        self.assertIn('"aiEnrichment": false', body)
        self.assertIn('"includeRaw": false', body)
        self.assertIn('"analyticsEnabled": false', body)
        self.assertIn('"enabled": false', body)

        config = {
            item["name"]: item["value"]
            for item in self.by_name["Configuration"]["parameters"]["values"][0][
                "spec"
            ]
        }
        self.assertEqual(config["actorBuild"], "0.6.19")
        self.assertEqual(config["maxItems"], "1")
        self.assertEqual(config["maxTotalChargeUsd"], "0.1")
        self.assertEqual(
            config["googleSpreadsheetId"],
            "REPLACE_WITH_GOOGLE_SPREADSHEET_ID",
        )

    def test_make_code_projection_matches_shared_fixture(self) -> None:
        fixture_path = ROOT / "tests" / "fixtures" / "linkedin-job.json"
        script = """
const fs = require('fs');
const blueprint = JSON.parse(fs.readFileSync(process.argv[1], 'utf8'));
const record = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const node = blueprint.flow.find(value => value.module === 'code:ExecuteCode');
const output = new Function('input', node.mapper.codeEditorJavascript)({job: record});
process.stdout.write(JSON.stringify(output));
"""
        completed = subprocess.run(
            ["node", "-e", script, str(BLUEPRINT_PATH), str(fixture_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        flattened = json.loads(completed.stdout)
        flat_schema = json.loads(FLAT_SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(list(flattened), flat_schema["required"])
        self.assertEqual(flattened["schemaVersion"], "nomad-agent-flat-job-v1")
        self.assertEqual(flattened["jobKey"], "linkedin:4446226935")
        self.assertEqual(flattened["workArrangements"], '["hybrid"]')
        self.assertEqual(flattened["contractTypes"], "[]")
        self.assertIsNone(flattened["descriptionText"])

    def test_sheet_mapping_matches_32_column_flat_schema(self) -> None:
        flat_schema = json.loads(FLAT_SCHEMA_PATH.read_text(encoding="utf-8"))
        expected = flat_schema["required"]
        with COLUMNS_PATH.open(newline="", encoding="utf-8") as handle:
            headers = next(csv.reader(handle))
        self.assertEqual(headers, expected)

        for name in ("Update existing job", "Append new job"):
            values = self.by_name[name]["mapper"]["values"]
            self.assertEqual(list(values), [str(index) for index in range(32)])
            self.assertEqual(
                list(values.values()),
                [f"{{{{4.result.{field}}}}}" for field in expected],
            )
            self.assertEqual(
                self.by_name[name]["mapper"]["valueInputOption"],
                "USER_ENTERED",
            )

    def test_jobkey_routes_update_or_append_without_delivery_cache(self) -> None:
        lookup = self.by_name["Find row by jobKey"]
        self.assertEqual(lookup["module"], "google-sheets:filterRows")
        self.assertEqual(lookup["mapper"]["limit"], "1")
        self.assertTrue(lookup["mapper"]["continue"])
        self.assertEqual(lookup["mapper"]["filter"][0][0], {
            "a": "B",
            "b": "{{4.result.jobKey}}",
            "o": "text:equal",
        })

        update = self.by_name["Update existing job"]
        append = self.by_name["Append new job"]
        self.assertEqual(update["mapper"]["rowNumber"], "{{5.__ROW_NUMBER__}}")
        self.assertEqual(
            update["filter"]["conditions"][0][0]["o"],
            "exist",
        )
        self.assertEqual(
            append["filter"]["conditions"][0][0]["o"],
            "notexist",
        )

    def test_public_blueprint_has_no_credentials_or_extra_destinations(self) -> None:
        rendered = json.dumps(self.blueprint).lower()
        self.assertNotIn("__imtconn__", rendered)
        self.assertNotIn("bearer ", rendered)
        self.assertNotIn("token=", rendered)
        self.assertNotIn("@gmail.com", rendered)
        self.assertNotIn("@googlemail.com", rendered)
        self.assertNotIn("airtable", rendered)
        self.assertNotIn("slack", rendered)
        self.assertNotIn("telegram", rendered)
        self.assertNotIn("sendemail", rendered)
        self.assertNotIn("datastore", rendered)


if __name__ == "__main__":
    unittest.main()

