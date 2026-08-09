from __future__ import annotations

import csv
import json
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
        self.assertTrue(self.blueprint["metadata"]["instant"])

        self.assertEqual(
            [module["module"] for module in self.blueprint["flow"]],
            [
                "apify:finishedActorRuns",
                "util:SetVariables",
                "apify:fetchDatasetItems",
                "util:SetVariables",
                "google-sheets:filterRows",
                "builtin:BasicRouter",
            ],
        )

    def test_actor_completion_handoff_is_async_and_credential_free(self) -> None:
        trigger = self.by_name["Watch completed LinkedIn Actor runs"]
        self.assertEqual(trigger["module"], "apify:finishedActorRuns")
        self.assertEqual(trigger["parameters"], {})
        self.assertEqual(trigger["mapper"], {})

        config = {
            item["name"]: item["value"]
            for item in self.by_name["Configuration"]["mapper"]["variables"]
        }
        self.assertEqual(config["maxitems"], "1")
        self.assertEqual(
            config["googlespreadsheetid"],
            "REPLACE_WITH_GOOGLE_SPREADSHEET_ID",
        )

        dataset = self.by_name["Get normalized jobs"]
        self.assertEqual(
            dataset["mapper"]["datasetId"],
            "{{1.defaultDatasetId}}",
        )
        self.assertEqual(dataset["mapper"]["limit"], "{{2.maxitems}}")

    def test_native_projection_matches_flat_schema_without_paid_code(self) -> None:
        projection = self.by_name["Flatten normalized job"]
        self.assertEqual(projection["module"], "util:SetVariables")
        self.assertEqual(projection["mapper"]["scope"], "roundtrip")
        self.assertEqual(projection["filter"], {
            "name": "Skip empty Actor runs",
            "conditions": [[
                {"a": "{{3.identity.source}}", "o": "exist"},
                {"a": "{{3.identity.externalId}}", "o": "exist"},
            ]],
        })

        flat_schema = json.loads(FLAT_SCHEMA_PATH.read_text(encoding="utf-8"))
        variables = projection["mapper"]["variables"]
        self.assertEqual(
            [variable["name"] for variable in variables],
            flat_schema["required"],
        )
        by_name = {variable["name"]: variable["value"] for variable in variables}
        self.assertEqual(by_name["schemaVersion"], "nomad-agent-flat-job-v1")
        self.assertEqual(
            by_name["jobKey"],
            "{{3.identity.source}}:{{3.identity.externalId}}",
        )
        self.assertEqual(by_name["title"], "{{3.data.title}}")
        self.assertEqual(by_name["descriptionText"], "{{3.data.descriptionText}}")

        for field in (
            "workArrangements",
            "workSchedules",
            "contractTypes",
            "seniorityLevels",
            "industries",
            "jobFunctions",
        ):
            expression = by_name[field]
            self.assertIn(" = null; null;", expression)
            self.assertIn('= 0; "[]";', expression)
            self.assertIn("join(add(emptyarray;", expression)
            self.assertIn("; emptystring)", expression)

        rendered = json.dumps(projection)
        self.assertNotIn("code:ExecuteCode", rendered)
        self.assertNotIn("concat(", rendered)

    def test_sheet_mapping_matches_32_column_flat_schema(self) -> None:
        flat_schema = json.loads(FLAT_SCHEMA_PATH.read_text(encoding="utf-8"))
        expected = flat_schema["required"]
        with COLUMNS_PATH.open(newline="", encoding="utf-8") as handle:
            headers = next(csv.reader(handle))
        self.assertEqual(headers, expected)

        for name in ("Find row by jobKey", "Update existing job", "Append new job"):
            mapper = self.by_name[name]["mapper"]
            self.assertEqual(mapper["spreadsheetId"], "{{2.googlespreadsheetid}}")
            self.assertEqual(mapper["sheetId"], "{{2.googlesheetname}}")

        for name in ("Update existing job", "Append new job"):
            values = self.by_name[name]["mapper"]["values"]
            self.assertEqual(list(values), [str(index) for index in range(32)])
            self.assertEqual(
                list(values.values()),
                [f"{{{{4.{field}}}}}" for field in expected],
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
            "b": "{{4.jobKey}}",
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
