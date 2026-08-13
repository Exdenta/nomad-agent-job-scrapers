#!/usr/bin/env python3
"""Credential-safe Streamable HTTP smoke test for both Apify MCP profiles."""
from __future__ import annotations

import argparse
from http.client import IncompleteRead, RemoteDisconnected
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
from retry_policy import (  # noqa: E402
    RunStateError,
    evaluate_terminal_run,
    validate_dataset_count,
)


PINNED_URL = (
    "https://mcp.apify.com?tools="
    "fetch-actor-details,call-actor,get-actor-run,get-dataset-items,"
    "get-key-value-store-record"
)
SCOPED_URL = PINNED_URL  # Backward-compatible import for pack tests.
COMMON_TOOLS = {
    "fetch-actor-details", "call-actor", "get-actor-run", "get-dataset-items",
    "get-key-value-store-record",
}
REQUIRED_TOOLS = COMMON_TOOLS
READ_ONLY_TOOLS = {
    "fetch-actor-details",
    "get-actor-run",
    "get-dataset-items",
    "get-key-value-store-record",
}
PROFILES = {
    "linkedin": {
        "url": PINNED_URL,
        "tool": "call-actor",
        "build": "0.6.39",
        "source": "linkedin",
        "input": Path(__file__).resolve().parents[1] / "examples/linkedin-search.mcp.json",
    },
    "euraxess": {
        "url": PINNED_URL,
        "tool": "call-actor",
        "build": "1.0.9",
        "source": "euraxess",
        "input": Path(__file__).resolve().parents[1] / "examples/euraxess-search.mcp.json",
    },
}
TERMINAL = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
CANONICAL_ROOTS = {"custom", "data", "identity", "llm", "raw", "schemaVersion"}


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
    def __init__(self, token: str, timeout: float, endpoint: str = SCOPED_URL) -> None:
        self._timeout = timeout
        self._endpoint = endpoint
        self._next_id = 1
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict[str, Any], request_id: int | None):
        request = Request(
            self._endpoint,
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
    attempts = 3 if name in READ_ONLY_TOOLS else 1
    for attempt in range(1, attempts + 1):
        try:
            return client.call(
                "tools/call", {"name": name, "arguments": arguments}
            )
        except (
            IncompleteRead,
            RemoteDisconnected,
            URLError,
            TimeoutError,
            ConnectionError,
        ):
            if attempt == attempts:
                raise
            print(
                f"Transient MCP read failure for {name}; "
                f"retrying read {attempt}/{attempts - 1}"
            )
            time.sleep(1)
    raise AssertionError("unreachable")


def _default_storage_id(run: dict[str, Any], group: str, legacy_key: str) -> str:
    storage = (((run.get("storages") or {}).get(group) or {}).get("default") or {})
    value = storage.get("id") or run.get(legacy_key)
    return value if isinstance(value, str) else ""


def _run_to_terminal(
    client: McpClient,
    tool_name: str,
    tool_arguments: dict[str, Any],
    *,
    max_polls: int,
    poll_wait_secs: int,
) -> dict[str, Any]:
    run = _tool_payload(_call_tool(client, tool_name, tool_arguments))
    run_id = run.get("runId") or run.get("id")
    status = run.get("status")
    if not isinstance(run_id, str) or not run_id:
        raise RuntimeError("Actor tool returned no runId")
    print(f"Actor run started: runId={run_id} status={status}")

    for poll in range(1, max_polls + 1):
        if status in TERMINAL:
            break
        run = _tool_payload(
            _call_tool(
                client,
                "get-actor-run",
                {"runId": run_id, "waitSecs": poll_wait_secs},
            )
        )
        status = run.get("status")
        print(f"Actor poll {poll}: status={status}")
    if status not in TERMINAL:
        raise RuntimeError("Actor did not reach a terminal status in the polling bound")
    if status != "SUCCEEDED":
        raise RuntimeError(
            "Actor run failed: "
            f"runId={run_id} status={status} "
            f"statusMessage={run.get('statusMessage')} exitCode={run.get('exitCode')}"
        )
    return run


def _require_build(run: dict[str, Any], expected: str) -> None:
    if run.get("buildNumber") != expected:
        raise RuntimeError(
            f"run used build {run.get('buildNumber')!r}; expected {expected}"
        )


def _verified_rest_run(token: str, run_id: str, timeout: float) -> dict[str, Any]:
    """Read authoritative run metadata when MCP omits buildNumber."""
    request = Request(
        f"https://api.apify.com/v2/actor-runs/{run_id}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read())
    run = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(run, dict) or run.get("id") != run_id:
        raise RuntimeError("Apify REST run verification returned an invalid record")
    if run.get("status") != "SUCCEEDED" or run.get("exitCode") not in {None, 0}:
        raise RuntimeError(
            "verified Actor run is not successful: "
            f"status={run.get('status')} exitCode={run.get('exitCode')}"
        )
    return run


def _run_summary(client: McpClient, run: dict[str, Any]) -> Any:
    """Read one run's minimal public v3 outcome."""
    store_id = _default_storage_id(run, "keyValueStores", "defaultKeyValueStoreId")
    if not store_id:
        return None
    try:
        payload = _tool_payload(
            _call_tool(
                client,
                "get-key-value-store-record",
                {"keyValueStoreId": store_id, "recordKey": "RUN-SUMMARY"},
            )
        )
    except RuntimeError as exc:
        if "not found" in str(exc).lower() or "does not exist" in str(exc).lower():
            return None
        raise
    value = payload.get("value")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise RuntimeError("RUN-SUMMARY value is not valid JSON") from exc
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile", choices=sorted(PROFILES), default="linkedin",
        help="integration profile to discover or run (default: linkedin)",
    )
    parser.add_argument("--run", action="store_true", help="start one bounded Actor run")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--max-polls", type=int, default=8)
    parser.add_argument("--poll-wait-secs", type=int, default=30)
    parser.add_argument("--request-timeout-secs", type=float, default=70)
    parser.add_argument(
        "--max-reschedule-retries",
        type=int,
        default=1,
        help="honor at most one valid RUN-SUMMARY v3 retry (default: 1)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = PROFILES[args.profile]
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
    if args.max_reschedule_retries not in {0, 1}:
        print("--max-reschedule-retries must be 0 or 1", file=sys.stderr)
        return 2
    try:
        client = McpClient(token, args.request_timeout_secs, str(profile["url"]))
        protocol = client.initialize()
        tools_result = client.call("tools/list", {})
        tools = tools_result.get("tools", [])
        names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
        required_tools = COMMON_TOOLS | {str(profile["tool"])}
        missing = required_tools - names
        if missing:
            raise RuntimeError(f"scoped MCP server is missing tools: {sorted(missing)}")
        print(
            f"MCP discovery passed: protocol={protocol} tools={len(names)} "
            f"names={','.join(sorted(str(name) for name in names))}"
        )
        if not args.run:
            return 0

        input_path = args.input or Path(profile["input"])
        tool_arguments = json.loads(input_path.read_text(encoding="utf-8"))
        actor_input = tool_arguments.get("input", {})
        if not isinstance(actor_input, dict) or actor_input.get("maxItems", 0) > 5:
            raise RuntimeError("live smoke input may request at most 5 items")
        tool_arguments["waitSecs"] = 0
        call_options = tool_arguments.get("callOptions", {})
        if call_options.get("build") != profile["build"]:
            raise RuntimeError("MCP smoke input must pin the qualified build")
        if call_options.get("maxItems", 0) > 5:
            raise RuntimeError("MCP callOptions may request at most 5 items")
        run = _run_to_terminal(
            client,
            str(profile["tool"]),
            tool_arguments,
            max_polls=args.max_polls,
            poll_wait_secs=args.poll_wait_secs,
        )
        run_id = run.get("runId") or run.get("id")
        if not isinstance(run_id, str) or not run_id:
            raise RuntimeError("terminal Actor run returned no run ID")
        run = _verified_rest_run(token, run_id, args.request_timeout_secs)
        _require_build(run, str(profile["build"]))

        summary = None
        for retry_attempt in range(args.max_reschedule_retries + 1):
            summary = _run_summary(client, run)
            decision = evaluate_terminal_run(
                run,
                summary,
                retry_attempt=retry_attempt,
                max_retries=args.max_reschedule_retries,
            )
            if decision.automatic_retry:
                print(
                    "Actor RUN-SUMMARY requested one retry: "
                    f"waiting {decision.delay_seconds} seconds"
                )
                time.sleep(decision.delay_seconds)
                run = _run_to_terminal(
                    client,
                    str(profile["tool"]),
                    tool_arguments,
                    max_polls=args.max_polls,
                    poll_wait_secs=args.poll_wait_secs,
                )
                retry_run_id = run.get("runId") or run.get("id")
                if not isinstance(retry_run_id, str) or not retry_run_id:
                    raise RuntimeError("retried Actor run returned no run ID")
                run = _verified_rest_run(
                    token, retry_run_id, args.request_timeout_secs,
                )
                _require_build(run, str(profile["build"]))
                continue
            if not decision.fetch_dataset:
                raise RuntimeError(f"delivery stopped: {decision.reason}")
            break
        if summary is None:
            raise RuntimeError("RUN-SUMMARY was not evaluated")

        dataset_id = _default_storage_id(run, "datasets", "defaultDatasetId")
        if not dataset_id:
            raise RuntimeError("successful run returned no default dataset ID")
        fetched = _call_tool(
            client,
            "get-dataset-items",
            {"datasetId": dataset_id, "limit": 5, "clean": False},
        )
        items = _dataset_items(fetched)
        validate_dataset_count(summary, len(items))
        if not items:
            print("Actor RUN-SUMMARY is empty and the dataset has no matching jobs")
            return 0
        for index, item in enumerate(items):
            if set(item) != CANONICAL_ROOTS:
                raise RuntimeError(
                    f"dataset item {index} has unexpected roots: {sorted(item)}"
                )
            if item.get("schemaVersion") != "nomad-agent-job-v1":
                raise RuntimeError(f"dataset item {index} has unsupported schemaVersion")
            source = ((item.get("identity") or {}).get("source"))
            if source != profile["source"]:
                raise RuntimeError(
                    f"dataset item {index} has source {source!r}; "
                    f"expected {profile['source']!r}"
                )
        print(f"MCP end-to-end smoke passed: fetched={len(items)} canonical rows")
        return 0
    except (
        HTTPError,
        IncompleteRead,
        RemoteDisconnected,
        URLError,
        OSError,
        RuntimeError,
        RunStateError,
        json.JSONDecodeError,
    ) as exc:
        if isinstance(exc, HTTPError):
            detail = f"HTTP {exc.code} {exc.reason}"
        else:
            detail = str(exc)
        print(f"MCP smoke failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
