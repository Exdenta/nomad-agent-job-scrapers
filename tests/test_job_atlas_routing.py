"""Customer entry points must route to the public Job Atlas catalog."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SLUGS = ('linkedin-enrich-translate-normalize-scraper', 'euraxess-enrich-translate-normalize-scraper',
         'ycombinator-enrich-translate-normalize-scraper', 'ai-job-fit-scorer')

class JobAtlasRoutingTests(unittest.TestCase):
    def test_website_routes_to_current_store_and_keeps_current_brand(self):
        for path in (ROOT / 'website').rglob('*.html'):
            text = path.read_text()
            self.assertNotIn('apify.com/nomad-agent', text, path)
            for identity in re.findall(r'<title[^>]*>.*?</title>|<header[^>]*>.*?</header>', text, re.S):
                if identity.startswith('<header'):
                    self.assertIn('Job Atlas', identity, path)
                self.assertNotIn('Nomad Agent', identity, path)
            # The homepage FAQ and About may explain the retained legacy domain.
            if path.relative_to(ROOT).as_posix() not in {'website/index.html', 'website/about/index.html'}:
                self.assertNotIn('Nomad Agent', text, path)
            self.assertIn('/assets/job-atlas-mark.svg', text, path)
        home = (ROOT / 'website/index.html').read_text()
        for slug in SLUGS:
            self.assertIn('https://apify.com/job-atlas/' + slug, home)

    def test_runnable_examples_and_skills_use_job_atlas(self):
        for folder in ('integrations', '.agents/skills', 'scripts'):
            for path in (ROOT / folder).rglob('*'):
                if not path.is_file() or 'evidence' in path.parts or path.suffix not in {'.md','.json','.py','.mjs','.yaml'}:
                    continue
                text = path.read_text()
                for slug in SLUGS:
                    self.assertNotRegex(text, r'nomad-agent(?:/|~|%2[Ff])' + re.escape(slug), path)
        self.assertIn('nomad-agent-job-v1', (ROOT / 'README.md').read_text())

    def test_current_brand_assets_are_present(self):
        assets = ROOT / 'website/assets'
        for name in ('job-atlas-mark.svg','job-atlas-mark-512.png','job-atlas-social-card.svg',
                     'job-atlas-social-card.png','linkedin-mark.svg','euraxess-mark.svg',
                     'ycombinator-mark.svg','ai-job-fit-scorer-mark.svg'):
            self.assertGreater((assets / name).stat().st_size, 0)
