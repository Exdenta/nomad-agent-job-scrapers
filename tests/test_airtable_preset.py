from __future__ import annotations

import json
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIRTABLE_DIR = ROOT / "integrations" / "airtable"
FIELDS_PATH = AIRTABLE_DIR / "airtable-fields.json"
WORKBOOK_PATH = AIRTABLE_DIR / "airtable-jobs-import.xlsx"
FLAT_SCHEMA_PATH = ROOT / "integrations" / "shared" / "flat-job-v1.schema.json"
XML_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


class AirtablePresetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.preset = json.loads(FIELDS_PATH.read_text(encoding="utf-8"))
        self.flat_schema = json.loads(
            FLAT_SCHEMA_PATH.read_text(encoding="utf-8")
        )

    def test_fields_match_shared_32_column_projection(self) -> None:
        self.assertEqual(
            [field["name"] for field in self.preset["fields"]],
            self.flat_schema["required"],
        )
        self.assertEqual(len(self.preset["fields"]), 32)
        self.assertEqual(self.preset["tableName"], "Jobs")
        self.assertEqual(self.preset["primaryField"], "jobKey")

    def test_deduplication_is_exact_jobkey_upsert(self) -> None:
        dedupe = self.preset["deduplication"]
        self.assertEqual(dedupe["field"], "jobKey")
        self.assertEqual(dedupe["definition"], "source:externalId")
        self.assertEqual(dedupe["match"], "exact")
        self.assertEqual(dedupe["onOneMatch"], "update")
        self.assertEqual(dedupe["onNoMatch"], "create")
        self.assertEqual(dedupe["onMultipleMatches"], "error")

    def test_array_fields_remain_json_text(self) -> None:
        by_name = {field["name"]: field for field in self.preset["fields"]}
        for name in (
            "workArrangements",
            "workSchedules",
            "contractTypes",
            "seniorityLevels",
            "industries",
            "jobFunctions",
        ):
            self.assertEqual(by_name[name]["type"], "multilineText")
            self.assertIn("JSON array string or null", by_name[name]["description"])

    def test_workbook_contains_expected_sheets_headers_and_example_row(self) -> None:
        self.assertTrue(WORKBOOK_PATH.is_file())
        with zipfile.ZipFile(WORKBOOK_PATH) as workbook:
            workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
            sheet_names = [
                element.attrib["name"]
                for element in workbook_xml.findall(".//x:sheet", XML_NS)
            ]
            self.assertEqual(sheet_names, ["Jobs", "Field Setup"])

            jobs_xml = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
            first_row = jobs_xml.find(".//x:row[@r='1']", XML_NS)
            second_row = jobs_xml.find(".//x:row[@r='2']", XML_NS)
            self.assertIsNotNone(first_row)
            self.assertIsNotNone(second_row)

            headers = [
                cell.findtext("x:v", default="", namespaces=XML_NS)
                for cell in first_row.findall("x:c", XML_NS)
            ]
            sample = [
                cell.findtext("x:v", default="", namespaces=XML_NS)
                for cell in second_row.findall("x:c", XML_NS)
            ]
            self.assertEqual(headers, self.flat_schema["required"])
            self.assertEqual(len(sample), 32)
            self.assertEqual(sample[0], "nomad-agent-flat-job-v1")
            self.assertTrue(sample[1].startswith("linkedin:EXAMPLE-"))
            self.assertIn("EXAMPLE - DELETE", sample[5])


if __name__ == "__main__":
    unittest.main()
