#!/usr/bin/env python3
"""Check whether the current OpenRouter API key is valid and tool-capable."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "x-ai/grok-3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the current OpenRouter key with model-list, basic chat, and optional tools probes."
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"OpenRouter-compatible base URL. Default: {DEFAULT_BASE_URL}",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model slug used for probe requests. Default: {DEFAULT_MODEL}",
    )
    parser.add_argument(
        "--probe-mode",
        choices=("basic", "tools", "both"),
        default="both",
        help="Whether to probe plain chat, tool calling, or both. Default: both.",
    )
    parser.add_argument(
        "--skip-model-list",
        action="store_true",
        help="Skip the /models fetch check and only test chat completions.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds. Default: 30.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write a structured result payload.",
    )
    return parser.parse_args()


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


def fetch_models(base_url: str, api_key: str, timeout: float) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/models"
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
    return {
        "status": "OK",
        "model_count": len(models) if isinstance(models, list) else 0,
    }


def _openai_client(*, api_key: str, base_url: str, timeout: float) -> Any:
    try:
        from openai import OpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError("openai package is required to run OpenRouter key probes") from exc
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)


def probe_basic(client: Any, model: str) -> dict[str, Any]:
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


def probe_tools(client: Any, model: str) -> dict[str, Any]:
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


def summarize_status(result: dict[str, Any], probe_mode: str) -> tuple[str, int]:
    models_status = result.get("models", {}).get("status", "SKIPPED")
    basic_status = result.get("basic", {}).get("status", "SKIPPED")
    tools_status = result.get("tools", {}).get("status", "SKIPPED")
    failing = [status for status in (models_status, basic_status, tools_status) if status not in {"OK", "SKIPPED"}]
    if not failing:
        summary = "OPENROUTER_KEY_OK"
        if probe_mode == "basic":
            summary = "OPENROUTER_KEY_OK_BASIC"
        elif probe_mode == "tools":
            summary = "OPENROUTER_KEY_OK_TOOLS"
        elif probe_mode == "both":
            summary = "OPENROUTER_KEY_OK_BOTH"
        return summary, 0
    primary = failing[0]
    exit_codes = {
        "AUTH_ERROR": 10,
        "REGION_BLOCK": 11,
        "MODEL_NAME_ERROR": 12,
        "TOOL_CALLING_UNSUPPORTED": 13,
        "PERMISSION_ERROR": 14,
        "FAIL": 15,
    }
    return primary, exit_codes.get(primary, 15)


def print_human_report(result: dict[str, Any], summary: str) -> None:
    print(f"SUMMARY={summary}")
    if "models" in result:
        models = result["models"]
        if models.get("status") == "OK":
            print(f"MODELS\tOK\tcount={models.get('model_count', 0)}")
        else:
            print(f"MODELS\t{models.get('status')}\t{models.get('error', '')}")
    if "basic" in result:
        basic = result["basic"]
        if basic.get("status") == "OK":
            print(f"BASIC\tOK\tmodel={basic.get('returned_model')}")
        else:
            print(f"BASIC\t{basic.get('status')}\t{basic.get('error', '')}")
    if "tools" in result:
        tools = result["tools"]
        if tools.get("status") == "OK":
            print(f"TOOLS\tOK\tmodel={tools.get('returned_model')}\ttool_calls={tools.get('tool_calls', 0)}")
        else:
            print(f"TOOLS\t{tools.get('status')}\t{tools.get('error', '')}")


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY is required", file=sys.stderr)
        return 2

    result: dict[str, Any] = {
        "base_url": args.base_url,
        "model": args.model,
        "probe_mode": args.probe_mode,
    }

    if not args.skip_model_list:
        try:
            result["models"] = fetch_models(args.base_url, api_key, args.timeout)
        except Exception as exc:
            result["models"] = {"status": classify_error(exc), "error": str(exc)}

    if args.probe_mode in {"basic", "both", "tools"}:
        try:
            client = _openai_client(api_key=api_key, base_url=args.base_url, timeout=args.timeout)
        except Exception as exc:
            status = classify_error(exc)
            result["basic"] = {"status": status, "error": str(exc)}
            if args.probe_mode in {"tools", "both"}:
                result["tools"] = {"status": status, "error": str(exc)}
            summary, exit_code = summarize_status(result, args.probe_mode)
            print_human_report(result, summary)
            return exit_code
    else:
        client = None

    if args.probe_mode in {"basic", "both"}:
        try:
            result["basic"] = probe_basic(client, args.model)
        except Exception as exc:
            result["basic"] = {"status": classify_error(exc), "error": str(exc)}

    if args.probe_mode in {"tools", "both"}:
        try:
            result["tools"] = probe_tools(client, args.model)
        except Exception as exc:
            result["tools"] = {"status": classify_error(exc), "error": str(exc)}

    summary, exit_code = summarize_status(result, args.probe_mode)
    print_human_report(result, summary)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "exit_code": exit_code,
                    "result": result,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
