"""Run a matched ToolSandbox ablation under a fixed budget and fault setting."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
MATCHED_RUNNER = ROOT_DIR / "scripts" / "run_toolsandbox_bench.py"

MATCHED_SYSTEMS = "tc_full,tc_no_repair,tc_no_fallback,tc_no_reuse,tc_planner_only"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run matched ToolSandbox ablation systems under a shared benchmark configuration")
    parser.add_argument("--source", default=str(ROOT_DIR / "data" / "toolsandbox.formal.json"))
    parser.add_argument("--outdir", default="outputs/toolsandbox_matched_ablation")
    parser.add_argument("--num-runs", type=int, default=3)
    parser.add_argument("--mode", choices=["demo", "planner"], default="planner")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--asset-registry-root", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model-version", default="phase1_executor")
    parser.add_argument("--budget-note", default="matched ToolSandbox ablation under shared budget")
    parser.add_argument("--config-file", default=str(ROOT_DIR / "configs" / "benchmark_toolsandbox.yaml"))
    parser.add_argument("--phase-config", default=str(ROOT_DIR / "configs" / "phase1.yaml"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cmd = [
        sys.executable,
        str(MATCHED_RUNNER),
        "--source",
        args.source,
        "--outdir",
        args.outdir,
        "--mode",
        args.mode,
        "--systems",
        MATCHED_SYSTEMS,
        "--num-runs",
        str(args.num_runs),
        "--seed",
        str(args.seed),
        "--model-version",
        args.model_version,
        "--budget-note",
        args.budget_note,
        "--config-file",
        args.config_file,
        "--phase-config",
        args.phase_config,
    ]
    if args.limit is not None:
        cmd.extend(["--limit", str(args.limit)])
    if args.smoke:
        cmd.append("--smoke")
    if args.asset_registry_root:
        cmd.extend(["--asset-registry-root", args.asset_registry_root])

    completed = subprocess.run(
        cmd,
        cwd=ROOT_DIR,
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        check=False,
    )
    if completed.returncode == 0:
        manifest_path = Path(args.outdir) / "experiment_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            metadata = dict(manifest.get("experiment_metadata", {}))
            metadata["runner_script"] = str(Path(__file__).resolve())
            metadata["delegated_runner_script"] = str(MATCHED_RUNNER.resolve())
            manifest["experiment_metadata"] = metadata
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
