#!/usr/bin/env python3
"""Probe OpenRouter model availability for the current account and region."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from openai import OpenAI

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CANDIDATES = [
    "x-ai/grok-3",
    "x-ai/grok-3-mini",
    "openai/o4-mini",
    "anthropic/claude-sonnet-4.5",
    "google/gemini-2.5-pro",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe which OpenRouter models are callable from the current machine, "
            "account, and region."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"OpenRouter-compatible base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--fetch-tools-supported",
        action="store_true",
        help="Fetch candidates from /models?supported_parameters=tools before probing.",
    )
    parser.add_argument(
        "--model",
        dest="models",
        action="append",
        default=[],
        help="Probe one explicit model id. Can be passed multiple times.",
    )
    parser.add_argument(
        "--match",
        action="append",
        default=[],
        help="Only keep fetched candidates whose id contains this substring. Can be repeated.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on fetched candidate count after filtering.",
    )
    parser.add_argument(
        "--probe-mode",
        choices=("basic", "tools", "both"),
        default="both",
        help="Whether to probe plain chat, tool calling, or both. Default: both.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for model list fetches and probes. Default: 30.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write structured probe results as JSON.",
    )
    return parser.parse_args()


def fetch_tool_models(base_url: str, api_key: str, timeout: float) -> list[str]:
    query = urllib.parse.urlencode({"supported_parameters": "tools"})
    url = f"{base_url.rstrip('/')}/models?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    models = payload.get("data", [])
    return [str(item["id"]) for item in models if isinstance(item, dict) and item.get("id")]


def classify_error(exc: Exception) -> str:
    message = str(exc).lower()
    if "unsupported_country_region_territory" in message or "not available in your region" in message:
        return "REGION_BLOCK"
    if "invalid api key" in message or "incorrect api key" in message or "authentication" in message or "401" in message:
        return "AUTH_ERROR"
    if "model" in message and ("not found" in message or "does not exist" in message or "unknown" in message):
        return "MODEL_NAME_ERROR"
    if "tool" in message and ("unsupported" in message or "not supported" in message or "function calling" in message):
        return "TOOL_CALLING_UNSUPPORTED"
    if "permission" in message or "403" in message or "forbidden" in message:
        return "PERMISSION_ERROR"
    return "FAIL"


def probe_basic(client: OpenAI, model: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1,
        temperature=0,
    )
    return {
        "status": "OK",
        "returned_model": getattr(response, "model", None),
    }


def probe_tools(client: OpenAI, model: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "use tools if available"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "ping",
                    "description": "Return pong.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        tool_choice="auto",
        max_tokens=8,
        temperature=0,
    )
    message = response.choices[0].message
    return {
        "status": "OK",
        "returned_model": getattr(response, "model", None),
        "tool_calls": len(message.tool_calls or []),
        "content": message.content,
    }


def print_result(result: dict[str, Any], probe_mode: str) -> None:
    model = result["model"]
    if result["overall_status"] == "OK":
        if probe_mode == "basic":
            print(f"OK\t{model}\tbasic={result['basic']['returned_model']}")
            return
        if probe_mode == "tools":
            print(
                f"OK\t{model}\ttools={result['tools']['returned_model']}"
                f"\ttool_calls={result['tools'].get('tool_calls', 0)}"
            )
            return
        print(
            f"OK\t{model}\tbasic={result['basic']['returned_model']}"
            f"\ttools={result['tools']['returned_model']}"
            f"\ttool_calls={result['tools'].get('tool_calls', 0)}"
        )
        return

    if probe_mode in {"basic", "both"} and result["basic"]["status"] != "OK":
        print(
            f"{result['basic']['status']}\t{model}\tbasic\t{result['basic'].get('error', '')}"
        )
        return
    if probe_mode in {"tools", "both"} and result["tools"]["status"] != "OK":
        print(
            f"{result['tools']['status']}\t{model}\ttools\t{result['tools'].get('error', '')}"
        )
        return
    print(f"{result['overall_status']}\t{model}")


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    candidates: list[str] = []
    if args.fetch_tools_supported:
        try:
            candidates.extend(fetch_tool_models(args.base_url, api_key, args.timeout))
        except Exception as exc:
            print(f"failed to fetch tool-capable models: {exc}", file=sys.stderr)
            return 3

    if args.models:
        candidates.extend(args.models)
    if not candidates:
        candidates.extend(DEFAULT_CANDIDATES)

    seen: set[str] = set()
    ordered_candidates: list[str] = []
    for model in candidates:
        if args.match and not any(pattern in model for pattern in args.match):
            continue
        if model in seen:
            continue
        seen.add(model)
        ordered_candidates.append(model)

    if args.limit > 0:
        ordered_candidates = ordered_candidates[: args.limit]

    client = OpenAI(api_key=api_key, base_url=args.base_url, timeout=args.timeout)
    results: list[dict[str, Any]] = []

    for model in ordered_candidates:
        result: dict[str, Any] = {
            "model": model,
            "base_url": args.base_url,
            "probe_mode": args.probe_mode,
            "overall_status": "OK",
        }

        if args.probe_mode in {"basic", "both"}:
            try:
                result["basic"] = probe_basic(client, model)
            except Exception as exc:
                result["basic"] = {
                    "status": classify_error(exc),
                    "error": str(exc),
                }
                result["overall_status"] = result["basic"]["status"]

        if args.probe_mode in {"tools", "both"}:
            try:
                result["tools"] = probe_tools(client, model)
            except Exception as exc:
                result["tools"] = {
                    "status": classify_error(exc),
                    "error": str(exc),
                }
                result["overall_status"] = result["tools"]["status"]

        results.append(result)
        print_result(result, args.probe_mode)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(
                {
                    "base_url": args.base_url,
                    "probe_mode": args.probe_mode,
                    "results": results,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
