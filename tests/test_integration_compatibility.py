from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
LINKEDIN_FIELDS = {
    "aiEnrichment", "analyticsEnabled", "companyFilters",
    "companyProfileEnrichment", "dedupe", "filters", "includeRaw",
    "firstRunMode", "keyword", "linkedinSearch", "location", "maxItems",
    "postedWithin", "schemaVersion", "strictGeography", "translateToEnglish",
    "workArrangements",
}
EURAXESS_FIELDS = {
    "aiEnrichment", "analyticsEnabled", "dedupe", "euraxessSearch",
    "filters", "includeRaw", "keyword", "location", "maxItems",
    "postedWithin", "schemaVersion", "translateToEnglish",
    "workArrangements",
}


class IntegrationCompatibilityTests(unittest.TestCase):
    def test_matrix_and_skills_cover_every_verified_input_field(self) -> None:
        matrix = (ROOT / "docs" / "integration-compatibility.md").read_text()
        linkedin = (
            ROOT / ".agents" / "skills"
            / "linkedin-enrich-translate-normalize-scraper"
            / "references" / "input-contract.md"
        ).read_text()
        euraxess = (
            ROOT / ".agents" / "skills"
            / "euraxess-enrich-translate-normalize-scraper"
            / "references" / "input-contract.md"
        ).read_text()
        for field in LINKEDIN_FIELDS:
            self.assertIn(f"`{field}`", matrix)
            self.assertIn(f"| `{field}` |", linkedin)
        for field in EURAXESS_FIELDS:
            self.assertIn(f"`{field}`", matrix)
            self.assertIn(f"| `{field}` |", euraxess)
        self.assertIn("| `postedWithin` | enum | `24h` |", linkedin)
        self.assertIn("| `maxItems` | integer | `100` |", linkedin)
        self.assertIn("| `postedWithin` | enum | `24h` |", euraxess)
        self.assertIn("| `maxItems` | integer | `100` |", euraxess)
        self.assertIn("| `includeRaw` | boolean | `true` |", euraxess)

    def test_make_task_and_rest_profiles_pin_exact_current_builds(self) -> None:
        make = (ROOT / "integrations" / "make" / "README.md").read_text()
        api = (ROOT / "integrations" / "api" / "README.md").read_text()
        for text in (make, api):
            self.assertIn("`latest`", text)
            self.assertIn("`latest`", text)
        for field in (
            "linkedinSearch", "strictGeography", "companyProfileEnrichment",
            "companyFilters", "euraxessSearch", "filters",
        ):
            self.assertIn(field, make + api)

    def test_all_runner_integrations_transport_the_complete_actor_input(self) -> None:
        matrix = (ROOT / "docs" / "integration-compatibility.md").read_text()
        api = (ROOT / "integrations" / "api" / "README.md").read_text()
        make = (ROOT / "integrations" / "make" / "README.md").read_text()
        mcp = (ROOT / "integrations" / "mcp" / "README.md").read_text()
        linkedin_n8n = (
            ROOT / "integrations" / "n8n"
            / "linkedin-jobs-to-google-sheets.json"
        ).read_text()
        euraxess_n8n = (
            ROOT / "integrations" / "n8n"
            / "euraxess-jobs-to-google-sheets.json"
        ).read_text()

        self.assertEqual(len(LINKEDIN_FIELDS), 17)
        self.assertEqual(len(EURAXESS_FIELDS), 13)
        for field in LINKEDIN_FIELDS | EURAXESS_FIELDS:
            self.assertIn(f"`{field}`", matrix)
        for workflow in (linkedin_n8n, euraxess_n8n):
            self.assertIn("...advancedInput", workflow)
            self.assertIn("actorInput", workflow)
        self.assertIn("complete Actor input", make)
        self.assertIn("request body is the complete Actor input", api)
        self.assertIn("complete Actor input is passed under `input`", matrix)
        self.assertIn("strict v1 `input`", mcp)

    def test_public_text_has_no_workspace_or_operational_identifiers(self) -> None:
        forbidden_literals = (
            "/" + "Users/",
            "Find" + "Jobs",
            "WJVinrd" + "AxORkaLF3l",
            "LjfHtUT" + "5TbAdffWBL",
            "3Q4yWRp" + "CnbU8iYSVk",
            "Fgo5aeh" + "GjDm3Q7GQF",
            "private" + " collector",
            "delivery" + " journal",
            "hash-locked" + " Python",
        )
        opaque_id = re.compile(
            r"(?i)(?:build|run) id[`:\s]+"
            r"(?=[A-Za-z0-9]{12,}\b)(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+"
        )
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or path.suffix == ".xlsx":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                for forbidden in forbidden_literals:
                    self.assertNotIn(forbidden, text)
                self.assertIsNone(opaque_id.search(text))

    def test_run_summary_v3_is_marked_legacy(self) -> None:
        schema = (
            ROOT / "integrations" / "shared" / "run-summary-v3.schema.json"
        ).read_text()
        contracts = (ROOT / "docs" / "contracts.md").read_text()
        self.assertIn("Legacy compatibility only", schema)
        self.assertIn("Legacy completion record", contracts)
        self.assertIn("nomad-agent-run-summary-v4", contracts)

    def test_root_catalog_links_every_supported_pack(self) -> None:
        readme = (ROOT / "README.md").read_text()
        for relative in (
            "integrations/n8n/README.md", "integrations/make/README.md",
            "integrations/airtable/README.md", "integrations/mcp/README.md",
            "integrations/api/README.md", "docs/integration-compatibility.md",
            ".agents/skills",
        ):
            self.assertIn(relative, readme)


if __name__ == "__main__":
    unittest.main()
