#!/usr/bin/env python3
"""Credential-safe Streamable HTTP smoke test for the scoped Apify MCP pack."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCOPED_URL = (
    "https://mcp.apify.com?tools="
    "fetch-actor-details,"
    "nomad-agent/linkedin-enrich-translate-normalize-scraper"
)
ACTOR_TOOL = "nomad-agent--linkedin-enrich-translate-normalize-scraper"
REQUIRED_TOOLS = {
    "fetch-actor-details",
    ACTOR_TOOL,
    "get-actor-run",
    "get-dataset-items",
}
TERMINAL = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
CANONICAL_ROOTS = {"custom", "data", "identity", "llm", "raw", "schemaVersion"}
DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "examples/linkedin-search.mcp.json"


def _decode_response(body: bytes, content_type: str, request_id: int | None):
    text = body.decode("utf-8")
    if "application/json" in content_type:
        return json.loads(text) if text else None
    messages = []
    for line in text.splitlines():
        if line.startswith("data:"):
            messages.append(json.loads(line[5:].strip()))
    if request_id is not None:
        for message in reversed(messages):
            if message.get("id") == request_id:
                return message
    return messages[-1] if messages else None


class McpClient:
    def __init__(self, token: str, timeout: float) -> None:
        self._timeout = timeout
        self._next_id = 1
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict[str, Any], request_id: int | None):
        request = Request(
            SCOPED_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers,
            method="POST",
        )
        with urlopen(request, timeout=self._timeout) as response:
            session_id = response.headers.get("Mcp-Session-Id")
            if session_id:
                self._headers["Mcp-Session-Id"] = session_id
            return _decode_response(
                response.read(), response.headers.get("Content-Type", ""), request_id
            )

    def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        message = self._post(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
            request_id,
        )
        if not isinstance(message, dict):
            raise RuntimeError(f"{method} returned no JSON-RPC response")
        if "error" in message:
            error = message["error"]
            raise RuntimeError(
                f"{method} failed with {error.get('code')}: {error.get('message')}"
            )
        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(f"{method} returned an invalid result")
        return result

    def initialize(self) -> str:
        result = self.call(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "nomad-agent-mcp-smoke", "version": "1.0"},
            },
        )
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            None,
        )
        return str(result.get("protocolVersion", ""))


def _tool_payload(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("isError"):
        texts = [
            item.get("text", "")
            for item in result.get("content", [])
            if item.get("type") == "text"
        ]
        raise RuntimeError("MCP tool failed: " + " ".join(texts)[:1000])
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    for item in result.get("content", []):
        if item.get("type") != "text":
            continue
        try:
            parsed = json.loads(item.get("text", ""))
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError("MCP tool returned no structured object")


def _dataset_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _tool_payload(result)
    for key in ("items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(payload.get("datasetItems"), list):
        return [item for item in payload["datasetItems"] if isinstance(item, dict)]
    return []


def _call_tool(client: McpClient, name: str, arguments: dict[str, Any]):
    return client.call("tools/call", {"name": name, "arguments": arguments})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="start one bounded Actor run")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--max-polls", type=int, default=8)
    parser.add_argument("--poll-wait-secs", type=int, default=30)
    parser.add_argument("--request-timeout-secs", type=float, default=70)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        print("APIFY_TOKEN is required; the value is never printed", file=sys.stderr)
        return 2
    if args.max_polls < 1 or args.max_polls > 20:
        print("--max-polls must be between 1 and 20", file=sys.stderr)
        return 2
    if args.poll_wait_secs < 0 or args.poll_wait_secs > 60:
        print("--poll-wait-secs must be between 0 and 60", file=sys.stderr)
        return 2

    try:
        client = McpClient(token, args.request_timeout_secs)
        protocol = client.initialize()
        tools_result = client.call("tools/list", {})
        tools = tools_result.get("tools", [])
        names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
        missing = REQUIRED_TOOLS - names
        if missing:
            raise RuntimeError(f"scoped MCP server is missing tools: {sorted(missing)}")
        print(
            f"MCP discovery passed: protocol={protocol} tools={len(names)} "
            f"names={','.join(sorted(str(name) for name in names))}"
        )
        if not args.run:
            return 0

        actor_input = json.loads(args.input.read_text(encoding="utf-8"))
        if actor_input.get("maxItems", 0) > 5:
            raise RuntimeError("live smoke input may request at most 5 items")
        actor_input["waitSecs"] = 0
        run = _tool_payload(_call_tool(client, ACTOR_TOOL, actor_input))
        run_id = run.get("runId")
        status = run.get("status")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("Actor tool returned no runId")
        print(f"Actor run started: runId={run_id} status={status}")

        for poll in range(1, args.max_polls + 1):
            if status in TERMINAL:
                break
            run = _tool_payload(
                _call_tool(
                    client,
                    "get-actor-run",
                    {"runId": run_id, "waitSecs": args.poll_wait_secs},
                )
            )
            status = run.get("status")
            print(f"Actor poll {poll}: status={status}")
        if status not in TERMINAL:
            raise RuntimeError("Actor did not reach a terminal status in the polling bound")
        if status != "SUCCEEDED":
            print(
                "Actor run failed: "
                f"runId={run_id} status={status} "
                f"statusMessage={run.get('statusMessage')} exitCode={run.get('exitCode')}",
                file=sys.stderr,
            )
            return 1

        dataset = (
            ((run.get("storages") or {}).get("datasets") or {}).get("default") or {}
        )
        dataset_id = dataset.get("id")
        item_count = dataset.get("itemCount", 0)
        if not isinstance(dataset_id, str) or not dataset_id:
            raise RuntimeError("successful run returned no default dataset ID")
        if item_count == 0:
            print("Actor run succeeded with an empty dataset: no matching jobs")
            return 0
        fetched = _call_tool(
            client,
            "get-dataset-items",
            {"datasetId": dataset_id, "limit": 5, "clean": False},
        )
        items = _dataset_items(fetched)
        if not items:
            raise RuntimeError("non-empty dataset returned no fetched items")
        for index, item in enumerate(items):
            if set(item) != CANONICAL_ROOTS:
                raise RuntimeError(
                    f"dataset item {index} has unexpected roots: {sorted(item)}"
                )
            if item.get("schemaVersion") != "nomad-agent-job-v1":
                raise RuntimeError(f"dataset item {index} has unsupported schemaVersion")
        print(f"MCP end-to-end smoke passed: fetched={len(items)} canonical rows")
        return 0
    except (HTTPError, URLError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        if isinstance(exc, HTTPError):
            detail = f"HTTP {exc.code} {exc.reason}"
        else:
            detail = str(exc)
        print(f"MCP smoke failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
