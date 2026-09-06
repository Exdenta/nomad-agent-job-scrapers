from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import search_performance


class FakeResponse:
    def __init__(self, status: int, url: str, body: bytes) -> None:
        self.status = status
        self._url = url
        self._body = body

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self) -> bytes:
        return self._body


class SearchPerformanceTests(unittest.TestCase):
    def test_fetch_search_rows_pages_and_uses_read_only_query(self) -> None:
        captured = []
        responses = [
            {
                "rows": [
                    {
                        "keys": ["https://jobatlas.dev/", "job data api"],
                        "clicks": 2,
                        "impressions": 20,
                        "ctr": 0.1,
                        "position": 8.5,
                    },
                    {
                        "keys": ["https://jobatlas.dev/actors/linkedin", "linkedin jobs api"],
                        "clicks": 1,
                        "impressions": 10,
                        "ctr": 0.1,
                        "position": 12,
                    },
                ]
            },
            {"rows": []},
        ]

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            payload = responses.pop(0)
            return FakeResponse(200, request.full_url, json.dumps(payload).encode())

        with patch.object(search_performance, "urlopen", fake_urlopen):
            rows = search_performance.fetch_search_rows(
                "https://jobatlas.dev/",
                "test-token",
                date(2026, 8, 1),
                date(2026, 8, 28),
                row_limit=2,
            )

        self.assertEqual(len(rows), 2)
        self.assertEqual(len(captured), 2)
        first_request, timeout = captured[0]
        second_request, _ = captured[1]
        self.assertEqual(timeout, 30)
        self.assertEqual(first_request.get_method(), "POST")
        self.assertIn("searchAnalytics/query", first_request.full_url)
        self.assertEqual(first_request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(json.loads(first_request.data)["dimensions"], ["page", "query"])
        self.assertEqual(json.loads(first_request.data)["startRow"], 0)
        self.assertEqual(json.loads(second_request.data)["startRow"], 2)

    def test_build_report_aggregates_pages_and_non_brand_queries(self) -> None:
        rows = [
            {
                "keys": ["https://jobatlas.dev/", "nomad agent"],
                "clicks": 3,
                "impressions": 10,
                "position": 2,
            },
            {
                "keys": ["https://jobatlas.dev/", "job data api"],
                "clicks": 2,
                "impressions": 20,
                "position": 8,
            },
            {
                "keys": ["https://jobatlas.dev/actors/linkedin", "linkedin jobs api"],
                "clicks": 1,
                "impressions": 10,
                "position": 12,
            },
        ]

        report = search_performance.build_report(
            "https://jobatlas.dev/",
            date(2026, 8, 1),
            date(2026, 8, 28),
            rows,
            generated_at="2026-09-03T12:00:00Z",
        )

        self.assertEqual(report["totals"]["clicks"], 6)
        self.assertEqual(report["totals"]["impressions"], 40)
        self.assertEqual(report["totals"]["ctr"], 0.15)
        self.assertEqual(report["brandTotals"]["clicks"], 3)
        self.assertEqual(report["brandTotals"]["impressions"], 10)
        self.assertEqual(report["nonBrandTotals"]["clicks"], 3)
        self.assertEqual(report["nonBrandTotals"]["impressions"], 30)
        self.assertEqual(report["nonBrandTotals"]["ctr"], 0.1)
        self.assertEqual(report["coverage"]["rowCount"], 3)
        self.assertEqual(report["pages"][0]["page"], "https://jobatlas.dev/")
        self.assertEqual(report["queries"][0]["query"], "nomad agent")
        self.assertFalse(report["privacy"]["containsCookies"])
        self.assertFalse(report["privacy"]["containsSessionIdentifiers"])
        self.assertTrue(report["privacy"]["queryTextIncluded"])
        self.assertTrue(report["privacy"]["queryTextMayContainPersonalData"])
        self.assertIn("review", report["privacy"]["handling"].lower())

        public_report = search_performance.build_report(
            "https://jobatlas.dev/",
            date(2026, 8, 1),
            date(2026, 8, 28),
            rows,
            include_query_text=False,
            generated_at="2026-09-03T12:00:00Z",
        )
        self.assertNotIn("queries", public_report)
        self.assertFalse(public_report["privacy"]["queryTextIncluded"])
        self.assertFalse(public_report["privacy"]["queryTextMayContainPersonalData"])
        self.assertEqual(public_report["pages"], report["pages"])
        self.assertEqual(public_report["brandTotals"], report["brandTotals"])
        self.assertEqual(public_report["nonBrandTotals"], report["nonBrandTotals"])

    def test_write_report_is_deterministic_and_creates_parent(self) -> None:
        report = {"generatedAt": "2026-09-03T12:00:00Z", "totals": {"clicks": 0}}
        with TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "report.json"
            search_performance.write_report(output, report)
            self.assertEqual(json.loads(output.read_text()), report)
            self.assertTrue(output.read_text().endswith("\n"))

    def test_weekly_workflow_uses_oidc_and_retains_minimized_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/seo-observatory.yml").read_text()
        self.assertIn('cron: "15 5 * * 1"', workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("google-github-actions/auth@v3", workflow)
        self.assertIn(
            "scripts/search_performance.py --days 28 --omit-query-text", workflow
        )
        self.assertIn("scripts/search_publish.py inspect", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("retention-days: 90", workflow)
        self.assertNotIn("client_secret", workflow.lower())
        self.assertNotIn("private_key", workflow.lower())

    def test_public_program_has_intent_and_case_study_gates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        program = (root / "docs/seo-program.md").read_text()
        for required in (
            "## Search-intent ownership",
            "## Measurement contract",
            "## 90-day execution cadence",
            "## Case-study evidence template",
            "Do not create a placeholder testimonial",
            "no page is revised solely because it was unindexed for less than 72 hours",
        ):
            self.assertIn(required, program)
        self.assertIn("https://jobatlas.dev/", (root / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
