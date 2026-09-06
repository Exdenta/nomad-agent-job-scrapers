from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
N8N_LISTING = ROOT / "integrations" / "n8n" / "template-listing.md"
MAKE_LISTING = ROOT / "integrations" / "make" / "template-listing.md"

REQUIRED_FIELDS = (
    "### Title",
    "### Short description",
    "### Full description",
    "### Apps and services",
    "### Setup",
    "### Verification boundary",
    "### Links",
)


def template_sections(copy: str) -> list[str]:
    return [
        section
        for section in re.split(r"(?=^## Template \d+:)", copy, flags=re.MULTILINE)
        if section.startswith("## Template ")
    ]


class IntegrationListingCopyTests(unittest.TestCase):
    def assert_complete_sections(self, copy: str, expected_count: int) -> None:
        sections = template_sections(copy)
        self.assertEqual(len(sections), expected_count)
        for section in sections:
            for field in REQUIRED_FIELDS:
                self.assertIn(field, section)

    def test_n8n_copy_covers_every_repo_workflow_and_exact_pin(self) -> None:
        copy = N8N_LISTING.read_text(encoding="utf-8")
        self.assert_complete_sections(copy, 4)
        for asset in (
            "linkedin-jobs-to-google-sheets.json",
            "linkedin-daily-job-alerts.json",
            "euraxess-jobs-to-google-sheets.json",
            "ai-job-fit-scorer-to-google-sheets.json",
        ):
            self.assertIn(f"]({asset})", copy)

        for build in ("1.0.2", "latest", "0.1.22"):
            self.assertIn(f"`{build}`", copy)
        for product_url in (
            "https://jobatlas.dev/actors/linkedin",
            "https://jobatlas.dev/actors/euraxess",
            "https://jobatlas.dev/actors/ai-job-fit-scorer",
        ):
            self.assertIn(product_url, copy)
        self.assertGreaterEqual(
            copy.count("https://jobatlas.dev/integrations/n8n"), 4
        )

    def test_make_copy_covers_every_blueprint_and_exact_pin(self) -> None:
        copy = MAKE_LISTING.read_text(encoding="utf-8")
        self.assert_complete_sections(copy, 3)
        for asset in (
            "linkedin-jobs-to-google-sheets.blueprint.json",
            "euraxess-jobs-to-google-sheets.blueprint.json",
            "ai-job-fit-scorer-to-google-sheets.blueprint.json",
        ):
            self.assertIn(f"]({asset})", copy)

        for build in ("1.0.2", "latest", "0.1.22"):
            self.assertIn(f"`{build}`", copy)
        for product_url in (
            "https://jobatlas.dev/actors/linkedin",
            "https://jobatlas.dev/actors/euraxess",
            "https://jobatlas.dev/actors/ai-job-fit-scorer",
        ):
            self.assertIn(product_url, copy)
        self.assertGreaterEqual(
            copy.count("https://jobatlas.dev/integrations/make"), 3
        )

    def test_copy_keeps_marketplace_and_delivery_proof_separate(self) -> None:
        for path, artifact in (
            (N8N_LISTING, "workflow"),
            (MAKE_LISTING, "blueprint"),
        ):
            copy = path.read_text(encoding="utf-8")
            normalized = re.sub(r"\s+", " ", copy)
            self.assertIn(
                "No listing below has been submitted to or published in",
                normalized,
            )
            self.assertIn(
                f"Importing a {artifact} is artifact availability; it is not "
                "deployment, successful execution, or named-destination proof.",
                normalized,
            )
            self.assertNotIn("currently listed in", copy.casefold())


if __name__ == "__main__":
    unittest.main()
