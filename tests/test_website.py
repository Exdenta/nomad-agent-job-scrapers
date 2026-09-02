from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
HTML_PATH = WEBSITE / "index.html"

EXPECTED_PAGES = {
    "index.html": "https://nomadagent.dev/",
    "actors/euraxess/index.html": "https://nomadagent.dev/actors/euraxess",
    "actors/linkedin/index.html": "https://nomadagent.dev/actors/linkedin",
    "integrations/airtable/index.html": "https://nomadagent.dev/integrations/airtable",
    "integrations/api/index.html": "https://nomadagent.dev/integrations/api",
    "integrations/make/index.html": "https://nomadagent.dev/integrations/make",
    "integrations/mcp/index.html": "https://nomadagent.dev/integrations/mcp",
    "integrations/n8n/index.html": "https://nomadagent.dev/integrations/n8n",
    "integrations/python/index.html": "https://nomadagent.dev/integrations/python",
}

ACTOR_PATHS = {
    "linkedin": "/nomad-agent/linkedin-enrich-translate-normalize-scraper",
    "euraxess": "/nomad-agent/euraxess-enrich-translate-normalize-scraper",
}


class WebsiteHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, dict[str, str]]] = []
        self.ids: list[str] = []
        self.visible_text: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = {key: value or "" for key, value in attrs}
        self.elements.append((tag, attributes))
        if element_id := attributes.get("id"):
            self.ids.append(element_id)
        if tag in {"script", "style"}:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0 and data.strip():
            self.visible_text.append(data.strip())


class WebsiteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.css = (WEBSITE / "styles.css").read_text(encoding="utf-8")
        cls.script = (WEBSITE / "script.js").read_text(encoding="utf-8")
        cls.parser = WebsiteHTMLParser()
        cls.parser.feed(cls.html)

    def test_success_criteria_are_persisted(self) -> None:
        criteria = (WEBSITE / "SUCCESS_CRITERIA.md").read_text(encoding="utf-8")
        for heading in (
            "Reference-style fidelity",
            "Actor promotion and conversion clarity",
            "Conversion attribution",
            "Functional paths",
            "Trust and contract accuracy",
            "Discoverability, accessibility, and efficiency",
            "Verification gate",
        ):
            self.assertIn(heading, criteria)

    def test_ids_are_unique_and_local_assets_exist(self) -> None:
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        for tag, attrs in self.parser.elements:
            reference = attrs.get("src") or attrs.get("href")
            if not reference or not reference.startswith("./"):
                continue
            with self.subTest(tag=tag, reference=reference):
                target = WEBSITE / reference.removeprefix("./").split("?", 1)[0]
                self.assertTrue(target.is_file(), target)

    def test_every_indexable_page_has_unique_metadata_and_valid_local_links(self) -> None:
        titles: set[str] = set()
        descriptions: set[str] = set()

        actual_paths = {
            path.relative_to(WEBSITE).as_posix()
            for path in WEBSITE.rglob("*.html")
        }
        self.assertEqual(actual_paths, set(EXPECTED_PAGES))

        for relative_path, expected_canonical in EXPECTED_PAGES.items():
            with self.subTest(page=relative_path):
                path = WEBSITE / relative_path
                html = path.read_text(encoding="utf-8")
                parser = WebsiteHTMLParser()
                parser.feed(html)

                title_match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
                self.assertIsNotNone(title_match)
                title = re.sub(r"\s+", " ", title_match.group(1)).strip()
                self.assertGreaterEqual(len(title), 20)
                self.assertNotIn(title, titles)
                titles.add(title)

                meta = {
                    attrs.get("name") or attrs.get("property"): attrs.get("content", "")
                    for tag, attrs in parser.elements
                    if tag == "meta"
                }
                description = meta.get("description", "")
                self.assertGreaterEqual(len(description), 70)
                self.assertNotIn(description, descriptions)
                descriptions.add(description)
                self.assertNotIn("noindex", meta.get("robots", "").lower())
                self.assertEqual(meta.get("og:url"), expected_canonical)

                canonicals = [
                    attrs.get("href")
                    for tag, attrs in parser.elements
                    if tag == "link" and "canonical" in attrs.get("rel", "").split()
                ]
                self.assertEqual(canonicals, [expected_canonical])
                self.assertEqual(len(parser.ids), len(set(parser.ids)))

                for tag, attrs in parser.elements:
                    reference = attrs.get("src") or attrs.get("href")
                    if not reference or not reference.startswith(("./", "../")):
                        continue
                    target = (path.parent / reference.split("?", 1)[0]).resolve()
                    self.assertTrue(target.is_file() or target.is_dir(), (tag, target))

    def test_home_page_links_to_every_detail_page(self) -> None:
        internal_hrefs = {
            attrs.get("href")
            for tag, attrs in self.parser.elements
            if tag == "a" and attrs.get("href", "").startswith("/")
        }
        expected = {
            url.removeprefix("https://nomadagent.dev").rstrip("/") or "/"
            for path, url in EXPECTED_PAGES.items()
            if path != "index.html"
        }
        self.assertTrue(expected.issubset(internal_hrefs), expected - internal_hrefs)

    def test_every_apify_cta_is_direct_and_attributed(self) -> None:
        placements: set[str] = set()
        actor_counts = {actor: 0 for actor in ACTOR_PATHS}

        for tag, attrs in self.parser.elements:
            if tag != "a":
                continue
            parsed = urlparse(attrs.get("href", ""))
            if parsed.netloc != "apify.com":
                continue

            actor = attrs.get("data-actor", "")
            placement = attrs.get("data-placement", "")
            query = parse_qs(parsed.query)

            with self.subTest(placement=placement):
                self.assertIn(actor, ACTOR_PATHS)
                self.assertEqual(parsed.path, ACTOR_PATHS[actor])
                self.assertEqual(attrs.get("data-event"), "actor_cta_click")
                self.assertTrue(placement)
                self.assertNotIn(placement, placements)
                self.assertEqual(query.get("utm_source"), ["nomad-agent-job-scrapers"])
                self.assertEqual(query.get("utm_medium"), ["owned-site"])
                self.assertEqual(query.get("utm_campaign"), ["actor-discovery"])
                self.assertEqual(query.get("utm_content"), [placement])
                self.assertEqual(attrs.get("target"), "_blank")
                self.assertIn("noopener", attrs.get("rel", "").split())
                self.assertIn("noreferrer", attrs.get("rel", "").split())

            placements.add(placement)
            actor_counts[actor] += 1

        self.assertGreaterEqual(actor_counts["linkedin"], 4)
        self.assertGreaterEqual(actor_counts["euraxess"], 4)

    def test_both_actor_ctas_appear_before_long_documentation(self) -> None:
        above_documentation = self.html.split('<article class="docs-panel', 1)[0]
        for actor_path in ACTOR_PATHS.values():
            self.assertIn(actor_path, above_documentation)

    def test_actor_skill_selector_and_accessible_copy_status_exist(self) -> None:
        options = {
            attrs.get("data-source-option"): attrs
            for tag, attrs in self.parser.elements
            if tag == "button" and "data-source-option" in attrs
        }
        self.assertEqual(set(options), set(ACTOR_PATHS))
        self.assertEqual(options["linkedin"].get("aria-pressed"), "true")
        self.assertEqual(options["euraxess"].get("aria-pressed"), "false")
        for actor, attrs in options.items():
            self.assertIn(f"--skill {actor}-enrich-translate-normalize-scraper", attrs["data-command-value"])

        self.assertIn('id="command-status" role="status" aria-live="polite"', self.html)
        self.assertIn('aria-describedby="command-status"', self.html)
        self.assertIn('role="group" aria-label="Choose an Actor skill"', self.html)

    def test_conversion_hook_is_local_and_plausible_compatible(self) -> None:
        for token in (
            'CustomEvent("nomad-agent:analytics"',
            "window.nomadAgentAnalytics",
            'typeof window.plausible === "function"',
            "skill_source_selected",
            "install_command_copied",
        ):
            self.assertIn(token, self.script)
        self.assertNotIn("fetch(", self.script)
        self.assertNotIn("XMLHttpRequest", self.script)

    def test_structured_data_describes_exact_actor_catalog(self) -> None:
        match = re.search(
            r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(data["@type"], "ItemList")
        items = data["itemListElement"]
        self.assertEqual(len(items), 2)
        urls = {urlparse(item["item"]["url"]).path for item in items}
        self.assertEqual(urls, set(ACTOR_PATHS.values()))
        self.assertNotIn("aggregateRating", match.group(1))
        self.assertNotIn("offers", match.group(1))

    def test_visible_copy_preserves_trust_boundaries(self) -> None:
        visible = re.sub(r"\s+", " ", " ".join(self.parser.visible_text))
        for required in (
            "nomad-agent-job-v1",
            "null means unknown or unavailable",
            "[] means the source established that the field is empty",
            "RUN-SUMMARY",
            "named destination must be tested independently",
            "not affiliated with or endorsed by",
            "official accuracy percentage will be published only after",
        ):
            self.assertIn(required, visible)
        self.assertNotRegex(visible, r"\b\d+(?:\.\d+)?\s*%")
        self.assertNotIn("$", visible)

    def test_accessibility_and_responsive_guards_are_present(self) -> None:
        for html_token in (
            'class="skip-link"',
            'aria-controls="mobile-menu"',
            'aria-expanded="false"',
            'aria-label="Primary navigation"',
        ):
            self.assertIn(html_token, self.html)
        for css_token in (
            ":focus-visible",
            "@media (max-width: 960px)",
            "@media (max-width: 390px)",
            "@media (prefers-reduced-motion: reduce)",
        ):
            self.assertIn(css_token, self.css)

    def test_webmaster_verification_tags_are_present(self) -> None:
        meta_by_name = {
            attrs["name"]: attrs.get("content")
            for tag, attrs in self.parser.elements
            if tag == "meta" and "name" in attrs
        }
        self.assertEqual(
            meta_by_name.get("google-site-verification"),
            "DqV9MzbsJairpzgPKuojwNpzwRSrP8wC199X7IPbOzM",
        )
        self.assertEqual(
            meta_by_name.get("msvalidate.01"),
            "03430DBD7EDA9B72980270788BB942AB",
        )

    def test_firebase_hosting_is_bound_to_the_isolated_site(self) -> None:
        firebase = json.loads((ROOT / "firebase.json").read_text(encoding="utf-8"))
        firebaserc = json.loads((ROOT / ".firebaserc").read_text(encoding="utf-8"))
        hosting = firebase["hosting"]

        self.assertEqual(firebaserc["projects"]["default"], "hryu-jobs")
        self.assertEqual(hosting["site"], "nomad-agent-job-scrapers")
        self.assertEqual(hosting["public"], "website")
        self.assertNotIn("rewrites", hosting)
        self.assertNotIn("functions", firebase)
        self.assertIn("README.md", hosting["ignore"])
        self.assertIn("SUCCESS_CRITERIA.md", hosting["ignore"])

        global_headers = next(
            entry["headers"]
            for entry in hosting["headers"]
            if entry["source"] == "**"
        )
        header_names = {header["key"] for header in global_headers}
        self.assertTrue(
            {
                "Content-Security-Policy",
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Referrer-Policy",
                "Permissions-Policy",
            }.issubset(header_names)
        )

    def test_first_party_runtime_payload_is_under_100_kib(self) -> None:
        runtime_files = (
            HTML_PATH,
            WEBSITE / "styles.css",
            WEBSITE / "script.js",
            WEBSITE / "assets" / "mark.svg",
        )
        size = sum(path.stat().st_size for path in runtime_files)
        self.assertLess(size, 100 * 1024, size)


if __name__ == "__main__":
    unittest.main()
