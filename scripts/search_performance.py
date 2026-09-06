#!/usr/bin/env python3
"""Capture privacy-minimized Google Search Console performance evidence."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

try:
    from scripts import search_publish
except ImportError:  # Direct execution: python3 scripts/search_performance.py
    import search_publish  # type: ignore[no-redef]


SEARCH_ANALYTICS_ENDPOINT = (
    "https://www.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
)
DEFAULT_SITE_URL = "https://jobatlas.dev/"
DEFAULT_ROW_LIMIT = 25_000
MAX_ROWS = 50_000
BRAND_TERMS = ("nomad agent", "nomadagent", "nomad-agent")


def _response_summary(error: HTTPError) -> str:
    try:
        body = error.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    compact = " ".join(body.split())[:300]
    return f"HTTP {error.code}" + (f": {compact}" if compact else "")


def fetch_search_rows(
    site_url: str,
    access_token: str,
    start_date: date,
    end_date: date,
    *,
    row_limit: int = DEFAULT_ROW_LIMIT,
) -> list[dict[str, object]]:
    """Read aggregate page/query rows from Search Console, with pagination."""
    site_url = search_publish.normalize_site_url(site_url)
    if start_date > end_date:
        raise ValueError("start date cannot be after end date")
    if not 1 <= row_limit <= DEFAULT_ROW_LIMIT:
        raise ValueError(f"row limit must be between 1 and {DEFAULT_ROW_LIMIT}")

    endpoint = SEARCH_ANALYTICS_ENDPOINT.format(site=quote(site_url, safe=""))
    rows: list[dict[str, object]] = []
    start_row = 0

    while start_row < MAX_ROWS:
        payload = json.dumps(
            {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
                "dimensions": ["page", "query"],
                "type": "web",
                "dataState": "final",
                "rowLimit": row_limit,
                "startRow": start_row,
            }
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": search_publish.USER_AGENT,
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                page = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise RuntimeError(
                f"Search Console performance query failed with {_response_summary(error)}"
            ) from error
        except (URLError, json.JSONDecodeError) as error:
            raise RuntimeError(f"Search Console performance query failed: {error}") from error

        page_rows = page.get("rows", [])
        if not isinstance(page_rows, list):
            raise RuntimeError("Search Console returned a malformed rows value")
        rows.extend(row for row in page_rows if isinstance(row, dict))
        if len(page_rows) < row_limit:
            break
        start_row += row_limit

    return rows


def _is_brand_query(query: str) -> bool:
    normalized = " ".join(query.lower().split())
    return any(term in normalized for term in BRAND_TERMS)


def _empty_metrics() -> dict[str, float]:
    return {"clicks": 0.0, "impressions": 0.0, "positionWeight": 0.0}


def _add_metrics(target: dict[str, float], row: dict[str, object]) -> None:
    clicks = float(row.get("clicks", 0) or 0)
    impressions = float(row.get("impressions", 0) or 0)
    position = float(row.get("position", 0) or 0)
    target["clicks"] += clicks
    target["impressions"] += impressions
    target["positionWeight"] += position * impressions


def _finalize_metrics(metrics: dict[str, float]) -> dict[str, int | float]:
    clicks = metrics["clicks"]
    impressions = metrics["impressions"]
    return {
        "clicks": int(clicks) if clicks.is_integer() else round(clicks, 3),
        "impressions": (
            int(impressions) if impressions.is_integer() else round(impressions, 3)
        ),
        "ctr": round(clicks / impressions, 6) if impressions else 0,
        "averagePosition": (
            round(metrics["positionWeight"] / impressions, 3) if impressions else 0
        ),
    }


def build_report(
    site_url: str,
    start_date: date,
    end_date: date,
    rows: Iterable[dict[str, object]],
    *,
    generated_at: str | None = None,
    include_query_text: bool = True,
) -> dict[str, object]:
    """Aggregate GSC rows without collecting cookies, sessions, or identities."""
    site_url = search_publish.normalize_site_url(site_url)
    page_metrics: defaultdict[str, dict[str, float]] = defaultdict(_empty_metrics)
    query_metrics: defaultdict[str, dict[str, float]] = defaultdict(_empty_metrics)
    totals = _empty_metrics()
    brand_totals = _empty_metrics()
    non_brand_totals = _empty_metrics()
    row_count = 0

    for row in rows:
        keys = row.get("keys")
        if not isinstance(keys, list) or len(keys) != 2:
            raise ValueError("each Search Console row must have page and query keys")
        page, query = (str(keys[0]), str(keys[1]))
        if not page.startswith(site_url):
            raise ValueError(f"off-origin Search Console page: {page}")
        _add_metrics(totals, row)
        _add_metrics(page_metrics[page], row)
        _add_metrics(query_metrics[query], row)
        if _is_brand_query(query):
            _add_metrics(brand_totals, row)
        else:
            _add_metrics(non_brand_totals, row)
        row_count += 1

    pages = [
        {"page": page, **_finalize_metrics(metrics)}
        for page, metrics in page_metrics.items()
    ]
    pages.sort(
        key=lambda item: (
            -float(item["clicks"]),
            -float(item["impressions"]),
            str(item["page"]),
        )
    )

    queries: list[dict[str, object]] = []
    if include_query_text:
        queries = [
            {
                "query": query,
                "brand": _is_brand_query(query),
                **_finalize_metrics(metrics),
            }
            for query, metrics in query_metrics.items()
        ]
        queries.sort(
            key=lambda item: (
                -float(item["clicks"]),
                -float(item["impressions"]),
                str(item["query"]),
            )
        )

    return {
        "schemaVersion": "nomad-agent-search-performance-v1",
        "siteUrl": site_url,
        "generatedAt": generated_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "dateRange": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "privacy": {
            "source": "Google Search Console aggregate search analytics",
            "containsCookies": False,
            "containsSessionIdentifiers": False,
            "queryTextIncluded": include_query_text,
            "queryTextMayContainPersonalData": include_query_text,
            "handling": (
                "Review query text before quoting or publishing it."
                if include_query_text
                else "Safe for the public-repository workflow artifact; raw query text omitted."
            ),
        },
        "coverage": {
            "rowCount": row_count,
            "maximumRowsRequested": MAX_ROWS,
            "dimensions": ["page", "query"],
            "dataState": "final",
            "limitation": (
                "Search Console returns top rows and does not guarantee exhaustive "
                "page/query data."
            ),
        },
        "totals": _finalize_metrics(totals),
        "brandTotals": _finalize_metrics(brand_totals),
        "nonBrandTotals": _finalize_metrics(non_brand_totals),
        "pages": pages,
        **({"queries": queries} if include_query_text else {}),
    }


def write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Capture aggregate Google Search Console SEO performance evidence."
    )
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    parser.add_argument("--days", type=int, default=28)
    parser.add_argument(
        "--data-lag-days",
        type=int,
        default=2,
        help="End the report this many days before today to request final data.",
    )
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("seo-evidence/search-console.json"),
    )
    parser.add_argument(
        "--omit-query-text",
        action="store_true",
        help="Keep page and brand aggregates but omit raw query strings.",
    )
    args = parser.parse_args()
    if args.days < 1 or args.days > 90:
        parser.error("--days must be between 1 and 90")
    if args.data_lag_days < 0:
        parser.error("--data-lag-days cannot be negative")

    end_date = args.end_date or (date.today() - timedelta(days=args.data_lag_days))
    start_date = end_date - timedelta(days=args.days - 1)
    rows = fetch_search_rows(
        args.site_url,
        search_publish.google_access_token(),
        start_date,
        end_date,
    )
    report = build_report(
        args.site_url,
        start_date,
        end_date,
        rows,
        include_query_text=not args.omit_query_text,
    )
    write_report(args.output, report)
    print(
        f"Wrote {report['coverage']['rowCount']} aggregate page/query rows "
        f"to {args.output} for {start_date} through {end_date}"
    )


if __name__ == "__main__":
    main()
