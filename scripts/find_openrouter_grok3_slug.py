#!/usr/bin/env python3
"""Find callable Grok-3 model slugs on OpenRouter for the current account."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MATCH_PATTERNS = (
    r"\bgrok[-_]?3\b",
    r"\bgrok[-_]?3[-_]",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch OpenRouter models, filter Grok-3 candidates, and optionally probe callability."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"OpenRouter-compatible base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds for both fetch and probe. Default: 30.",
    )
    parser.add_argument(
        "--probe",
        choices=("none", "basic", "tools", "both"),
        default="tools",
        help="Whether to probe filtered candidates after fetch. Default: tools.",
    )
    parser.add_argument(
        "--match",
        action="append",
        default=[],
        help="Additional regex pattern for model id filtering. Can be passed multiple times.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on filtered candidate count after ranking.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write structured results as JSON.",
    )
    return parser.parse_args()


def _authorized_request(url: str, api_key: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
    )


def fetch_openrouter_models(base_url: str, api_key: str, timeout: float) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/models"
    request = _authorized_request(url, api_key)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return [item for item in payload.get("data", []) if isinstance(item, dict) and item.get("id")]


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


def _compile_patterns(extra_patterns: list[str]) -> list[re.Pattern[str]]:
    return [re.compile(pattern, flags=re.IGNORECASE) for pattern in [*DEFAULT_MATCH_PATTERNS, *extra_patterns]]


def filter_grok3_candidates(
    models: list[dict[str, Any]],
    *,
    extra_patterns: list[str] | None = None,
) -> list[dict[str, Any]]:
    patterns = _compile_patterns(extra_patterns or [])
    candidates: list[dict[str, Any]] = []
    for model in models:
        model_id = str(model.get("id") or "")
        if not model_id:
            continue
        if not any(pattern.search(model_id) for pattern in patterns):
            continue
        candidates.append(model)
    candidates.sort(key=_candidate_sort_key)
    return candidates


def _candidate_sort_key(model: dict[str, Any]) -> tuple[int, int, int, str]:
    model_id = str(model.get("id") or "").lower()
    supported_parameters = [
        str(item).lower()
        for item in model.get("supported_parameters", [])
        if str(item)
    ]
    architecture = model.get("architecture", {}) if isinstance(model.get("architecture"), dict) else {}
    input_modalities = [
        str(item).lower()
        for item in architecture.get("input_modalities", [])
        if str(item)
    ]
    tool_bonus = 0 if "tools" in supported_parameters else 1
    text_bonus = 0 if "text" in input_modalities or not input_modalities else 1
    shorter_bonus = len(model_id)
    return (tool_bonus, text_bonus, shorter_bonus, model_id)


def probe_basic(client: OpenAI, model: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "ping"}],
        max_tokens=1,
        temperature=0,
    )
    return {"status": "OK", "returned_model": getattr(response, "model", None)}


def probe_tools(client: OpenAI, model: str) -> dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "use the tool if supported"}],
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


def probe_candidates(
    candidate_ids: list[str],
    *,
    base_url: str,
    api_key: str,
    timeout: float,
    mode: str,
) -> list[dict[str, Any]]:
    if mode == "none":
        return [{"model": model_id, "overall_status": "UNPROBED"} for model_id in candidate_ids]

    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError("openai package is required for probe mode") from exc

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    results: list[dict[str, Any]] = []
    for model_id in candidate_ids:
        result: dict[str, Any] = {"model": model_id, "overall_status": "OK"}
        if mode in {"basic", "both"}:
            try:
                result["basic"] = probe_basic(client, model_id)
            except Exception as exc:
                result["basic"] = {"status": classify_error(exc), "error": str(exc)}
                result["overall_status"] = result["basic"]["status"]
        if mode in {"tools", "both"}:
            try:
                result["tools"] = probe_tools(client, model_id)
            except Exception as exc:
                result["tools"] = {"status": classify_error(exc), "error": str(exc)}
                result["overall_status"] = result["tools"]["status"]
        results.append(result)
    return results


def preferred_candidate(candidates: list[dict[str, Any]], probes: list[dict[str, Any]]) -> str | None:
    probe_by_id = {str(item["model"]): item for item in probes}
    for candidate in candidates:
        model_id = str(candidate.get("id") or "")
        probe = probe_by_id.get(model_id)
        if probe is None:
            continue
        tools_ok = probe.get("tools", {}).get("status") == "OK"
        basic_ok = probe.get("basic", {}).get("status") == "OK"
        if probe.get("overall_status") == "OK" or tools_ok or basic_ok:
            return model_id
    return str(candidates[0].get("id")) if candidates else None


def print_report(candidates: list[dict[str, Any]], probes: list[dict[str, Any]], probe_mode: str) -> None:
    probe_by_id = {str(item["model"]): item for item in probes}
    for candidate in candidates:
        model_id = str(candidate.get("id") or "")
        supported_parameters = ",".join(str(item) for item in candidate.get("supported_parameters", []) if str(item))
        context_length = candidate.get("context_length")
        probe = probe_by_id.get(model_id, {"overall_status": "UNPROBED"})
        if probe_mode == "none":
            print(f"CANDIDATE\t{model_id}\tsupported={supported_parameters}\tcontext={context_length}")
            continue
        status = str(probe.get("overall_status", "UNKNOWN"))
        detail = ""
        if probe_mode in {"tools", "both"} and isinstance(probe.get("tools"), dict):
            detail = f"\ttools={probe['tools'].get('status', '')}"
        elif probe_mode == "basic" and isinstance(probe.get("basic"), dict):
            detail = f"\tbasic={probe['basic'].get('status', '')}"
        print(
            f"{status}\t{model_id}\tsupported={supported_parameters}\tcontext={context_length}{detail}"
        )


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    try:
        models = fetch_openrouter_models(args.base_url, api_key, args.timeout)
    except Exception as exc:
        print(f"failed to fetch OpenRouter models: {exc}", file=sys.stderr)
        return 3

    candidates = filter_grok3_candidates(models, extra_patterns=args.match)
    if args.limit > 0:
        candidates = candidates[: args.limit]
    if not candidates:
        print("no Grok-3 candidate models found in OpenRouter /models response", file=sys.stderr)
        return 4

    candidate_ids = [str(candidate["id"]) for candidate in candidates]
    probes = probe_candidates(
        candidate_ids,
        base_url=args.base_url,
        api_key=api_key,
        timeout=args.timeout,
        mode=args.probe,
    )
    selected = preferred_candidate(candidates, probes)

    print_report(candidates, probes, args.probe)
    if selected:
        print(f"\nRECOMMENDED_MODEL={selected}")

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(
                {
                    "base_url": args.base_url,
                    "probe_mode": args.probe,
                    "candidate_count": len(candidates),
                    "recommended_model": selected,
                    "candidates": candidates,
                    "probes": probes,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
