from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import patch

from scripts import search_publish


class FakeResponse:
    def __init__(self, status: int, url: str, body: bytes = b"") -> None:
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


class SearchPublishTests(unittest.TestCase):
    def test_prepare_discovers_canonicals_and_writes_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            site_dir = Path(directory)
            (site_dir / "index.html").write_text(
                '<link rel="canonical" href="https://nomadagent.dev/">',
                encoding="utf-8",
            )
            docs_dir = site_dir / "docs"
            docs_dir.mkdir()
            (docs_dir / "index.html").write_text(
                '<link rel="canonical" href="https://nomadagent.dev/docs">',
                encoding="utf-8",
            )

            urls = search_publish.prepare(
                site_dir, "https://nomadagent.dev", "abcDEF12-345"
            )

            self.assertEqual(
                urls, ["https://nomadagent.dev/", "https://nomadagent.dev/docs"]
            )
            self.assertEqual(
                search_publish.parse_sitemap(
                    (site_dir / "sitemap.xml").read_text(encoding="utf-8")
                ),
                urls,
            )
            self.assertIn(
                "Sitemap: https://nomadagent.dev/sitemap.xml",
                (site_dir / "robots.txt").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (site_dir / "indexnow-key.txt").read_text(encoding="utf-8"),
                "abcDEF12-345\n",
            )

    def test_discovery_rejects_missing_duplicate_and_off_origin_canonicals(self) -> None:
        cases = (
            ("<title>No canonical</title>", "exactly one canonical"),
            (
                '<link rel="canonical" href="https://example.com/">',
                "must use the nomadagent.dev HTTPS origin",
            ),
            (
                '<link rel="canonical" href="https://nomadagent.dev/#section">',
                "cannot contain a query or fragment",
            ),
        )
        for html, expected in cases:
            with self.subTest(expected=expected), TemporaryDirectory() as directory:
                site_dir = Path(directory)
                (site_dir / "index.html").write_text(html, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, expected):
                    search_publish.discover_canonical_urls(
                        site_dir, "https://nomadagent.dev/"
                    )

    def test_google_submission_uses_encoded_property_and_sitemap(self) -> None:
        captured = []

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(204, request.full_url)

        with patch.object(search_publish, "urlopen", fake_urlopen):
            status = search_publish.submit_google_sitemap(
                "https://nomadagent.dev/",
                "https://nomadagent.dev/sitemap.xml",
                "test-token",
            )

        request, timeout = captured[0]
        self.assertEqual(status, 204)
        self.assertEqual(timeout, 30)
        self.assertEqual(request.get_method(), "PUT")
        self.assertIn(
            "sites/https%3A%2F%2Fnomadagent.dev%2F/sitemaps/"
            "https%3A%2F%2Fnomadagent.dev%2Fsitemap.xml",
            request.full_url,
        )
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_indexnow_submission_contains_all_urls_and_key_location(self) -> None:
        captured = []

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(202, request.full_url)

        urls = ["https://nomadagent.dev/", "https://nomadagent.dev/docs"]
        with patch.object(search_publish, "urlopen", fake_urlopen):
            status = search_publish.submit_indexnow(
                "https://nomadagent.dev/", urls, "abcDEF12-345"
            )

        request, timeout = captured[0]
        payload = json.loads(request.data)
        self.assertEqual(status, 202)
        self.assertEqual(timeout, 30)
        self.assertEqual(request.full_url, search_publish.INDEXNOW_ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(payload["host"], "nomadagent.dev")
        self.assertEqual(payload["key"], "abcDEF12-345")
        self.assertEqual(
            payload["keyLocation"], "https://nomadagent.dev/indexnow-key.txt"
        )
        self.assertEqual(payload["urlList"], urls)

    def test_google_preflight_requires_exact_full_access_property(self) -> None:
        payload = json.dumps(
            {
                "siteEntry": [
                    {
                        "siteUrl": "https://nomadagent.dev/",
                        "permissionLevel": "siteFullUser",
                    }
                ]
            }
        ).encode("utf-8")

        def fake_urlopen(request, timeout):
            self.assertEqual(request.get_method(), "GET")
            self.assertEqual(timeout, 30)
            return FakeResponse(200, request.full_url, payload)

        with patch.object(search_publish, "urlopen", fake_urlopen):
            permission = search_publish.verify_google_property_access(
                "https://nomadagent.dev/", "test-token"
            )
        self.assertEqual(permission, "siteFullUser")

        restricted = json.dumps(
            {
                "siteEntry": [
                    {
                        "siteUrl": "https://nomadagent.dev/",
                        "permissionLevel": "siteRestrictedUser",
                    }
                ]
            }
        ).encode("utf-8")

        with patch.object(
            search_publish,
            "urlopen",
            lambda request, timeout: FakeResponse(200, request.full_url, restricted),
        ), self.assertRaisesRegex(RuntimeError, "needs full access"):
            search_publish.verify_google_property_access(
                "https://nomadagent.dev/", "test-token"
            )

    def test_google_inspection_returns_index_status_without_requesting_indexing(self) -> None:
        captured = []
        payload = json.dumps(
            {
                "inspectionResult": {
                    "indexStatusResult": {
                        "verdict": "PASS",
                        "coverageState": "Submitted and indexed",
                        "lastCrawlTime": "2026-09-03T12:00:00Z",
                    }
                }
            }
        ).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured.append((request, timeout))
            return FakeResponse(200, request.full_url, payload)

        with patch.object(search_publish, "urlopen", fake_urlopen):
            result = search_publish.inspect_google_url(
                "https://nomadagent.dev/",
                "https://nomadagent.dev/actors/linkedin/",
                "test-token",
            )

        request, timeout = captured[0]
        self.assertEqual(timeout, 30)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, search_publish.GOOGLE_INSPECTION_ENDPOINT)
        self.assertEqual(
            json.loads(request.data),
            {
                "inspectionUrl": "https://nomadagent.dev/actors/linkedin/",
                "siteUrl": "https://nomadagent.dev/",
                "languageCode": "en-US",
            },
        )
        self.assertEqual(result["verdict"], "PASS")

    def test_google_access_token_uses_application_default_credentials(self) -> None:
        class FakeCredentials:
            token = None

            def refresh(self, request):
                self.token = "adc-token"

        credentials = FakeCredentials()
        google = ModuleType("google")
        google_auth = ModuleType("google.auth")
        google_auth.default = lambda **kwargs: (credentials, "hryu-jobs")
        google.auth = google_auth
        transport = ModuleType("google.auth.transport")
        transport_requests = ModuleType("google.auth.transport.requests")
        transport_requests.Request = object

        modules = {
            "google": google,
            "google.auth": google_auth,
            "google.auth.transport": transport,
            "google.auth.transport.requests": transport_requests,
        }
        with patch.dict(sys.modules, modules), patch.dict(
            "os.environ",
            {"GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN": ""},
            clear=False,
        ):
            token = search_publish.google_access_token()

        self.assertEqual(token, "adc-token")

    def test_repository_sitemap_matches_current_html_pages(self) -> None:
        root = Path(__file__).resolve().parents[1]
        site_dir = root / "website"
        expected = search_publish.discover_canonical_urls(
            site_dir, "https://nomadagent.dev/"
        )
        actual = search_publish.parse_sitemap(
            (site_dir / "sitemap.xml").read_text(encoding="utf-8")
        )
        self.assertEqual(actual, expected)
        self.assertEqual(
            actual,
            [
                "https://nomadagent.dev/",
                "https://nomadagent.dev/actors/euraxess",
                "https://nomadagent.dev/actors/linkedin",
                "https://nomadagent.dev/integrations/airtable",
                "https://nomadagent.dev/integrations/api",
                "https://nomadagent.dev/integrations/make",
                "https://nomadagent.dev/integrations/mcp",
                "https://nomadagent.dev/integrations/n8n",
                "https://nomadagent.dev/integrations/python",
            ],
        )

    def test_deployment_notifies_only_after_tests_preflight_and_firebase(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/deploy-website.yml").read_text(
            encoding="utf-8"
        )
        script = (root / "scripts/search_publish.py").read_text(encoding="utf-8")

        tests_at = workflow.index("python3 -m unittest discover -s tests -v")
        preflight_at = workflow.index("python3 scripts/search_publish.py preflight")
        auth_at = workflow.index("google-github-actions/auth@v3")
        deploy_at = workflow.index(
            "firebase deploy --only hosting --project hryu-jobs --non-interactive"
        )
        notify_at = workflow.index("python3 scripts/search_publish.py notify")
        self.assertLess(tests_at, auth_at)
        self.assertLess(tests_at, preflight_at)
        self.assertLess(preflight_at, deploy_at)
        self.assertLess(deploy_at, notify_at)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("firebase-tools@15.28.1", workflow)
        self.assertNotIn("FIREBASE_SERVICE_ACCOUNT_HRYU_JOBS", workflow)
        self.assertNotIn("firebaseServiceAccount", workflow)
        self.assertIn("https://api.indexnow.org/indexnow", script)
        self.assertIn("/webmasters/v3/sites/", script)
        self.assertIn("/v1/urlInspection/index:inspect", script)
        self.assertNotIn("indexing.googleapis.com", script)


if __name__ == "__main__":
    unittest.main()
