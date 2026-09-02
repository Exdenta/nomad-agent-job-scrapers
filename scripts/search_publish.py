#!/usr/bin/env python3
"""Build search artifacts and notify Google Search Console and IndexNow."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape


GOOGLE_WEBMASTERS_SCOPE = "https://www.googleapis.com/auth/webmasters"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
INDEXNOW_KEY_PATTERN = re.compile(r"[A-Za-z0-9-]{8,128}\Z")
SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
USER_AGENT = "nomad-agent-search-publisher/1.0"


class CanonicalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag != "link":
            return
        attributes = {key: value or "" for key, value in attrs}
        if "canonical" in attributes.get("rel", "").lower().split():
            self.canonicals.append(attributes.get("href", ""))


def normalize_site_url(raw: str) -> str:
    parsed = urlsplit(raw)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("site URL must be an absolute HTTPS URL")
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("site URL must identify the HTTPS origin root")
    return f"https://{parsed.netloc}/"


def validate_canonical(url: str, site_url: str, source: Path) -> str:
    parsed = urlsplit(url)
    site = urlsplit(site_url)
    if parsed.scheme != "https" or parsed.netloc != site.netloc:
        raise ValueError(f"{source} canonical must use the {site.netloc} HTTPS origin")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{source} canonical cannot contain a query or fragment")
    return url


def discover_canonical_urls(site_dir: Path, site_url: str) -> list[str]:
    site_url = normalize_site_url(site_url)
    urls: dict[str, Path] = {}
    html_paths = sorted(site_dir.rglob("*.html"))
    if not html_paths:
        raise ValueError(f"no HTML documents found under {site_dir}")

    for html_path in html_paths:
        parser = CanonicalParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        if len(parser.canonicals) != 1:
            raise ValueError(
                f"{html_path} must contain exactly one canonical link; "
                f"found {len(parser.canonicals)}"
            )
        canonical = validate_canonical(parser.canonicals[0], site_url, html_path)
        if canonical in urls:
            raise ValueError(
                f"duplicate canonical {canonical!r} in {urls[canonical]} and {html_path}"
            )
        urls[canonical] = html_path

    return sorted(urls, key=lambda url: (url != site_url, url))


def render_sitemap(urls: Iterable[str]) -> str:
    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{SITEMAP_NAMESPACE}">',
    ]
    for url in urls:
        rows.extend(("  <url>", f"    <loc>{escape(url)}</loc>", "  </url>"))
    rows.append("</urlset>")
    return "\n".join(rows) + "\n"


def render_robots(site_url: str) -> str:
    sitemap_url = urljoin(normalize_site_url(site_url), "sitemap.xml")
    return f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"


def validate_indexnow_key(key: str) -> str:
    if not INDEXNOW_KEY_PATTERN.fullmatch(key):
        raise ValueError(
            "INDEXNOW_KEY must contain 8-128 letters, numbers, or dashes"
        )
    return key


def prepare(site_dir: Path, site_url: str, indexnow_key: str | None) -> list[str]:
    urls = discover_canonical_urls(site_dir, site_url)
    (site_dir / "sitemap.xml").write_text(render_sitemap(urls), encoding="utf-8")
    (site_dir / "robots.txt").write_text(render_robots(site_url), encoding="utf-8")
    if indexnow_key:
        key = validate_indexnow_key(indexnow_key)
        (site_dir / "indexnow-key.txt").write_text(f"{key}\n", encoding="utf-8")
    return urls


def parse_sitemap(content: str) -> list[str]:
    root = ET.fromstring(content)
    if root.tag != f"{{{SITEMAP_NAMESPACE}}}urlset":
        raise ValueError("sitemap root must be a standard urlset")
    urls = [
        element.text.strip()
        for element in root.findall(f"{{{SITEMAP_NAMESPACE}}}url/{{{SITEMAP_NAMESPACE}}}loc")
        if element.text and element.text.strip()
    ]
    if not urls:
        raise ValueError("sitemap must contain at least one URL")
    if len(urls) != len(set(urls)):
        raise ValueError("sitemap contains duplicate URLs")
    return urls


def _response_summary(error: HTTPError) -> str:
    try:
        body = error.read(500).decode("utf-8", errors="replace").strip()
    except Exception:
        body = ""
    return f"HTTP {error.code}" + (f": {body}" if body else "")


def fetch_text(url: str, attempts: int = 4) -> str:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"GET {url} returned HTTP {response.status}")
                if response.geturl() != url:
                    raise RuntimeError(f"GET {url} redirected to {response.geturl()}")
                return response.read().decode("utf-8")
        except (HTTPError, URLError, OSError, RuntimeError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"live verification failed for {url}: {last_error}")


def submit_google_sitemap(site_url: str, sitemap_url: str, access_token: str) -> int:
    endpoint = (
        "https://www.googleapis.com/webmasters/v3/sites/"
        f"{quote(site_url, safe='')}/sitemaps/{quote(sitemap_url, safe='')}"
    )
    request = Request(
        endpoint,
        data=b"",
        method="PUT",
        headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status not in {200, 204}:
                raise RuntimeError(
                    f"Search Console sitemap submission returned HTTP {response.status}"
                )
            return response.status
    except HTTPError as error:
        raise RuntimeError(
            f"Search Console sitemap submission failed with {_response_summary(error)}"
        ) from error


def verify_google_property_access(site_url: str, access_token: str) -> str:
    site_url = normalize_site_url(site_url)
    request = Request(
        "https://www.googleapis.com/webmasters/v3/sites",
        headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Search Console property preflight returned HTTP {response.status}"
                )
            payload = json.loads(response.read())
    except HTTPError as error:
        raise RuntimeError(
            f"Search Console property preflight failed with {_response_summary(error)}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError("Search Console property preflight returned invalid JSON") from error

    permissions = {
        entry.get("siteUrl"): entry.get("permissionLevel")
        for entry in payload.get("siteEntry", [])
        if isinstance(entry, dict)
    }
    permission = permissions.get(site_url)
    if permission not in {"siteFullUser", "siteOwner"}:
        detail = permission or "not listed"
        raise RuntimeError(
            f"service account needs full access to {site_url}; current state: {detail}"
        )
    return permission


def submit_indexnow(
    site_url: str, urls: list[str], indexnow_key: str
) -> int:
    site_url = normalize_site_url(site_url)
    key = validate_indexnow_key(indexnow_key)
    host = urlsplit(site_url).netloc
    payload = json.dumps(
        {
            "host": host,
            "key": key,
            "keyLocation": urljoin(site_url, "indexnow-key.txt"),
            "urlList": urls,
        }
    ).encode("utf-8")
    request = Request(
        INDEXNOW_ENDPOINT,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status not in {200, 202}:
                raise RuntimeError(
                    f"IndexNow submission returned HTTP {response.status}"
                )
            return response.status
    except HTTPError as error:
        raise RuntimeError(
            f"IndexNow submission failed with {_response_summary(error)}"
        ) from error


def google_access_token() -> str:
    if access_token := os.environ.get("GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN"):
        return access_token

    raw_credentials = os.environ.get("GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON")
    if not raw_credentials:
        raise RuntimeError(
            "set GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN or "
            "GOOGLE_SEARCH_CONSOLE_CREDENTIALS_JSON"
        )
    try:
        credentials_info = json.loads(raw_credentials)
    except json.JSONDecodeError as error:
        raise RuntimeError("Google service-account JSON is invalid") from error

    try:
        from google.auth.transport.requests import Request as GoogleAuthRequest
        from google.oauth2 import service_account
    except ImportError as error:
        raise RuntimeError(
            "google-auth[requests] is required when using service-account JSON"
        ) from error

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=[GOOGLE_WEBMASTERS_SCOPE]
    )
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise RuntimeError("Google authentication did not return an access token")
    return credentials.token


def notify(site_dir: Path, site_url: str, indexnow_key: str) -> None:
    site_url = normalize_site_url(site_url)
    key = validate_indexnow_key(indexnow_key)
    canonical_urls = discover_canonical_urls(site_dir, site_url)
    local_sitemap = (site_dir / "sitemap.xml").read_text(encoding="utf-8")
    if parse_sitemap(local_sitemap) != canonical_urls:
        raise RuntimeError("local sitemap does not match the HTML canonical URLs")

    sitemap_url = urljoin(site_url, "sitemap.xml")
    live_sitemap = fetch_text(sitemap_url)
    if parse_sitemap(live_sitemap) != canonical_urls:
        raise RuntimeError("live sitemap does not match the deployed canonical URLs")
    for url in canonical_urls:
        fetch_text(url)

    key_url = urljoin(site_url, "indexnow-key.txt")
    if fetch_text(key_url).strip() != key:
        raise RuntimeError("live IndexNow key file does not match INDEXNOW_KEY")

    errors: list[str] = []
    try:
        google_status = submit_google_sitemap(
            site_url, sitemap_url, google_access_token()
        )
        print(f"Google Search Console accepted sitemap (HTTP {google_status})")
    except Exception as error:
        errors.append(f"Google Search Console: {error}")

    try:
        indexnow_status = submit_indexnow(site_url, canonical_urls, key)
        state = "accepted; key validation pending" if indexnow_status == 202 else "accepted"
        print(f"IndexNow {state} {len(canonical_urls)} URL(s) (HTTP {indexnow_status})")
    except Exception as error:
        errors.append(f"IndexNow: {error}")

    if errors:
        raise RuntimeError("; ".join(errors))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "preflight", "notify"):
        child = subparsers.add_parser(command)
        child.add_argument("--site-dir", type=Path, default=Path("website"))
        child.add_argument("--site-url", default="https://nomadagent.dev/")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "prepare":
            urls = prepare(
                args.site_dir,
                args.site_url,
                os.environ.get("INDEXNOW_KEY"),
            )
            print(f"Prepared search artifacts for {len(urls)} canonical URL(s)")
        elif args.command == "preflight":
            permission = verify_google_property_access(
                args.site_url, google_access_token()
            )
            print(f"Search Console property access verified ({permission})")
        else:
            indexnow_key = os.environ.get("INDEXNOW_KEY")
            if not indexnow_key:
                raise RuntimeError("INDEXNOW_KEY is required")
            notify(args.site_dir, args.site_url, indexnow_key)
    except (OSError, ValueError, RuntimeError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
