from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
LINKEDIN_FIELDS = {
    "aiEnrichment", "analyticsEnabled", "companyFilters",
    "companyProfileEnrichment", "dedupe", "filters", "includeRaw",
    "keyword", "linkedinSearch", "location", "maxItems", "postedWithin",
    "schemaVersion", "strictGeography", "translateToEnglish",
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
            self.assertIn("`0.6.38`", text)
            self.assertIn("`1.0.8`", text)
        for field in (
            "linkedinSearch", "strictGeography", "companyProfileEnrichment",
            "companyFilters", "euraxessSearch", "filters",
        ):
            self.assertIn(field, make + api)

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
