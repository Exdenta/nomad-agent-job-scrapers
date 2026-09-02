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
        self.assertEqual(ids, [1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(self.blueprint["metadata"]["scenario"]["sequential"])
        self.assertTrue(self.blueprint["metadata"]["instant"])

        self.assertEqual(
            [module["module"] for module in self.blueprint["flow"]],
            [
                "apify:finishedTaskRun",
                "util:SetVariables",
                "http:ActionSendData",
                "builtin:BasicRouter",
            ],
        )

    def test_task_completion_handoff_is_async_and_credential_free(self) -> None:
        trigger = self.by_name["Watch completed LinkedIn Task runs"]
        self.assertEqual(trigger["module"], "apify:finishedTaskRun")
        self.assertEqual(trigger["parameters"], {})
        self.assertEqual(trigger["mapper"], {})

        config = {
            item["name"]: item["value"]
            for item in self.by_name["Configuration"]["mapper"]["variables"]
        }
        self.assertEqual(config["maxitems"], "1")
        self.assertEqual(config["actorbuild"], "1.0.2")
        self.assertEqual(config["apifytaskid"], "REPLACE_WITH_APIFY_TASK_ID")
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

    def test_delivery_uses_closed_v4_status_and_one_bounded_retry_route(self) -> None:
        status = self.by_name["Read public RUN-SUMMARY v4"]
        self.assertEqual(status["mapper"]["url"], "{{1.output.runSummary}}")
        self.assertFalse(status["mapper"]["serializeUrl"])
        self.assertEqual(status["filter"], {
            "name": "Read status only for the exact successful Actor build",
            "conditions": [[
                {"a": "{{1.status}}", "b": "SUCCEEDED", "o": "text:equal"},
                {"a": "{{1.buildNumber}}", "b": "{{2.actorbuild}}", "o": "text:equal"},
                {"a": "{{1.output.runSummary}}", "o": "exist"},
            ]],
        })
        wait = self.by_name["Wait bounded v4 retry delay"]
        retry = self.by_name["Retry the same Apify Task once"]
        self.assertEqual(wait["module"], "util:FunctionSleep")
        self.assertEqual(wait["mapper"]["duration"], "{{3.data.retry.afterSeconds}}")
        retry_filter = json.dumps(wait["filter"])
        self.assertIn("nomad-agent-run-summary-v4", retry_filter)
        self.assertIn("{{1.meta.origin}}", retry_filter)
        self.assertIn('"b": "240"', retry_filter)
        self.assertEqual(retry["module"], "apify:runTask")
        self.assertEqual(retry["mapper"], {
            "taskId": "{{2.apifytaskid}}",
            "runSync": False,
        })
        delivery = self.by_name["Get normalized jobs"]
        self.assertEqual(
            delivery["filter"]["name"],
            "Deliver a valid v4 outcome when no first retry is pending",
        )
        self.assertIn("nomad-agent-run-summary-v4", json.dumps(delivery["filter"]))
        rendered = json.dumps(self.blueprint)
        self.assertIn("RUN-SUMMARY", rendered)
        self.assertNotIn("nomad-agent-fleet-run-summary-v2", rendered)
        self.assertNotIn("sources.linkedin", rendered)

    def test_native_projection_matches_flat_schema_without_paid_code(self) -> None:
        projection = self.by_name["Flatten normalized job"]
        self.assertEqual(projection["module"], "util:SetVariables")
        self.assertEqual(projection["mapper"]["scope"], "roundtrip")
        self.assertEqual(projection["filter"], {
            "name": "Skip empty Actor runs",
            "conditions": [[
                {"a": "{{8.identity.source}}", "o": "exist"},
                {"a": "{{8.identity.externalId}}", "o": "exist"},
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
            "{{8.identity.source}}:{{8.identity.externalId}}",
        )
        self.assertEqual(by_name["title"], "{{8.data.title}}")
        self.assertEqual(by_name["descriptionText"], "{{8.raw.description}}")

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
            self.assertIn('decodeURL("%5B%22")', expression)
            self.assertIn("escapeJSON(join(", expression)
            self.assertEqual(expression.count("__NOMAD_JSON_SEP__"), 2)
            self.assertIn('decodeURL("%22%2C%22")', expression)
            self.assertIn('decodeURL("%22%5D")', expression)
            self.assertIn("; emptystring)", expression)

        expected_sources = {
            "workArrangements": "8.data.employment.workArrangements",
            "workSchedules": "8.data.employment.workSchedules",
            "contractTypes": "8.data.employment.contractTypes",
            "seniorityLevels": "8.data.seniority.levels",
            "industries": "8.data.classification.industries",
            "jobFunctions": "8.data.classification.jobFunctions",
        }
        for field, source in expected_sources.items():
            self.assertEqual(
                by_name[field],
                f'{{{{if({source} = null; null; '
                f'if(length({source}) = 0; "[]"; '
                'join(add(emptyarray; decodeURL("%5B%22"); '
                f'replace(escapeJSON(join({source}; "__NOMAD_JSON_SEP__")); '
                '"__NOMAD_JSON_SEP__"; decodeURL("%22%2C%22")); '
                'decodeURL("%22%5D")); emptystring)))}}',
            )

        notes = projection["metadata"]["notes"]
        self.assertIn("reserved __NOMAD_JSON_SEP__ sentinel", notes)
        self.assertIn("do not reuse this formula for uncontrolled arrays", notes)

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
                [f"{{{{9.{field}}}}}" for field in expected],
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
            "b": "{{9.jobKey}}",
            "o": "text:equal",
        })

        update = self.by_name["Update existing job"]
        append = self.by_name["Append new job"]
        self.assertEqual(update["mapper"]["rowNumber"], "{{10.__ROW_NUMBER__}}")
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
