#!/usr/bin/env python3
"""Download tau-bench (optional) and convert task files into ToolClaw-compatible JSONL."""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_REPO_URL = "https://github.com/sierra-research/tau-bench"
DEFAULT_ZIP_URL = "https://codeload.github.com/sierra-research/tau-bench/zip/refs/heads/main"
TASK_FILE_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("retail", "train", "tau_bench/envs/retail/tasks_train.py"),
    ("retail", "test", "tau_bench/envs/retail/tasks_test.py"),
    ("airline", "train", "tau_bench/envs/airline/tasks_train.py"),
    ("airline", "test", "tau_bench/envs/airline/tasks_test.py"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare ToolClaw tau-bench source JSONL from official tau-bench tasks.")
    parser.add_argument(
        "--tau-repo-dir",
        default="data/external/tau-bench",
        help="Path to local tau-bench repository root (contains tau_bench/envs/...).",
    )
    parser.add_argument(
        "--out",
        default="data/tau_bench/tau_bench.aligned.jsonl",
        help="Output JSONL path for scripts/run_tau_bench.py --source",
    )
    parser.add_argument(
        "--download-if-missing",
        action="store_true",
        help="Download tau-bench from GitHub if --tau-repo-dir does not exist.",
    )
    parser.add_argument(
        "--zip-url",
        default=DEFAULT_ZIP_URL,
        help="Zip URL used when --download-if-missing is enabled.",
    )
    return parser.parse_args()


def _extract_python_literal(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_extract_python_literal(item) for item in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_extract_python_literal(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return {
            _extract_python_literal(key): _extract_python_literal(value)
            for key, value in zip(node.keys, node.values)
        }
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = _extract_python_literal(node.operand)
        if isinstance(value, (int, float)):
            return -value
    if isinstance(node, ast.Call):
        call_name = getattr(node.func, "id", "")
        if call_name == "Action":
            return {
                "name": _extract_python_literal(next((kw.value for kw in node.keywords if kw.arg == "name"), ast.Constant(value="action"))),
                "kwargs": _extract_python_literal(next((kw.value for kw in node.keywords if kw.arg == "kwargs"), ast.Dict(keys=[], values=[]))),
            }
    return ast.unparse(node)


def _call_to_kwargs(call: ast.Call) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for keyword in call.keywords:
        if keyword.arg is None:
            continue
        result[keyword.arg] = _extract_python_literal(keyword.value)
    return result


def _extract_tasks_from_module(py_path: Path) -> List[Dict[str, Any]]:
    root = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
    tasks: List[Dict[str, Any]] = []

    for node in root.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.List):
            continue

        for item in node.value.elts:
            if not isinstance(item, ast.Call):
                continue
            func_name = getattr(item.func, "id", "")
            if func_name != "Task":
                continue
            task_kwargs = _call_to_kwargs(item)
            action_names: List[str] = []
            actions_raw = task_kwargs.get("actions", [])
            if isinstance(actions_raw, list):
                for action in actions_raw:
                    if isinstance(action, str):
                        action_names.append(action)
                    elif isinstance(action, dict):
                        action_names.append(str(action.get("name", "action")))
            tasks.append(
                {
                    "instruction": str(task_kwargs.get("instruction", "")).strip(),
                    "annotator": task_kwargs.get("annotator", "unknown"),
                    "user_id": task_kwargs.get("user_id"),
                    "action_names": action_names,
                    "actions_count": len(actions_raw) if isinstance(actions_raw, list) else 0,
                }
            )
    return tasks


def _download_zip_repo(zip_url: str, target_repo_dir: Path) -> None:
    target_repo_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="toolclaw_tau_bench_") as tmp:
        zip_path = Path(tmp) / "tau-bench.zip"
        with urllib.request.urlopen(zip_url, timeout=60) as resp:
            zip_path.write_bytes(resp.read())
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)

        extracted_root = next((p for p in Path(tmp).iterdir() if p.is_dir() and p.name.startswith("tau-bench-")), None)
        if extracted_root is None:
            raise RuntimeError("Downloaded archive missing tau-bench-* root directory.")

        if target_repo_dir.exists():
            shutil.rmtree(target_repo_dir)
        shutil.copytree(extracted_root, target_repo_dir)


def _build_aligned_rows(repo_root: Path) -> Iterable[Dict[str, Any]]:
    for domain, split, rel in TASK_FILE_SPECS:
        task_path = repo_root / rel
        if not task_path.exists():
            continue
        raw_tasks = _extract_tasks_from_module(task_path)
        for idx, task in enumerate(raw_tasks, start=1):
            if not task["instruction"]:
                continue
            sample_id = f"tau_{domain}_{split}_{idx:05d}"
            yield {
                "sample_id": sample_id,
                "scenario": "success",
                "query": task["instruction"],
                "metadata": {
                    "domain": domain,
                    "split": split,
                    "source": str(rel),
                    "annotator": task["annotator"],
                    "user_id": task["user_id"],
                    "action_names": task["action_names"],
                    "actions_count": task["actions_count"],
                    "upstream_repo": DEFAULT_REPO_URL,
                },
            }


def main() -> None:
    args = parse_args()
    repo_dir = Path(args.tau_repo_dir)
    if not repo_dir.exists():
        if not args.download_if_missing:
            raise FileNotFoundError(
                f"tau-bench repo not found: {repo_dir}. "
                "Set --download-if-missing or provide an existing local repo path."
            )
        print(f"Downloading tau-bench to: {repo_dir}")
        _download_zip_repo(args.zip_url, repo_dir)

    rows = list(_build_aligned_rows(repo_dir))
    if not rows:
        raise RuntimeError(f"No tasks found under expected paths in {repo_dir}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"wrote aligned tau-bench source: {out_path}")
    print(f"total samples: {len(rows)}")


if __name__ == "__main__":
    main()
