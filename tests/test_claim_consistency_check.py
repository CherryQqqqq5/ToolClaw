from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "check_claim_consistency_module",
        ROOT_DIR / "scripts" / "check_claim_consistency.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_matrix(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "claims": {
                    "interaction_semantic_usefulness_mechanism": {
                        "status": "full405_semantic_repair_unsupported_targeted_slice_only",
                        "claim_strength": "limitation",
                        "boundary": "Do not treat full405 interaction as semantic repair evidence.",
                    },
                    "strict_layer_monotonicity": {
                        "status": "supported_with_cost_boundary",
                        "claim_strength": "mechanism_supporting",
                        "boundary": "Interaction overlay is strict-success non-regression evidence only.",
                    },
                },
                "suites": {
                    "bfcl_fc_core": {
                        "status": "implemented_boundary",
                        "claim_strength": "limitation",
                        "paper_role": "negative_transfer_boundary",
                        "reuse_claim_enabled_for_bfcl": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_claim_consistency_passes_bounded_docs(tmp_path: Path) -> None:
    module = _load_module()
    matrix = tmp_path / "paper_claim_matrix.yaml"
    _write_matrix(matrix)
    doc = tmp_path / "bounded.md"
    doc.write_text(
        "ToolSandbox interaction overlay is a bounded strict non-regression claim only.\n"
        "BFCL remains a negative-transfer boundary, not an exact-call headline.\n"
        "Do not blend BFCL into the ToolSandbox workflow headline.\n"
        "Reuse has no strict-success lift over interaction overlay.\n"
        "Do not claim `s4 > s3` full-core success.\n",
        encoding="utf-8",
    )

    report = module.build_report(matrix, [doc])

    assert report["audit_only"] is True
    assert report["blocker_count"] == 0
    assert report["warning_count"] == 0
    assert report["source_truth"]["interaction_semantic_usefulness_mechanism"]["claim_strength"] == "limitation"


def test_claim_consistency_detects_blockers(tmp_path: Path) -> None:
    module = _load_module()
    matrix = tmp_path / "paper_claim_matrix.yaml"
    _write_matrix(matrix)
    doc = tmp_path / "stale.md"
    doc.write_text(
        "Current strict ladder: s3=1.000000 and s4=1.000000.\n"
        "Interaction delta s3-s2=+0.296296 with paired 360/0/855.\n"
        "| interaction_semantic_usefulness_mechanism | mechanism_primary | supported_current_evidence |\n"
        "Reuse s4 > s3 success lift is part of the headline.\n",
        encoding="utf-8",
    )

    report = module.build_report(matrix, [doc])
    rule_ids = {issue["rule_id"] for issue in report["issues"]}

    assert report["blocker_count"] >= 6
    assert "toolsandbox_s3_strict_one" in rule_ids
    assert "toolsandbox_s4_strict_one" in rule_ids
    assert "toolsandbox_interaction_360_0_855" in rule_ids
    assert "toolsandbox_s3_minus_s2_0296296" in rule_ids
    assert "interaction_semantic_current_positive" in rule_ids
    assert "reuse_s4_over_s3_lift" in rule_ids


def test_claim_consistency_cli_returns_nonzero_on_blocker_and_writes_reports(tmp_path: Path) -> None:
    module = _load_module()
    matrix = tmp_path / "paper_claim_matrix.yaml"
    _write_matrix(matrix)
    doc = tmp_path / "README.md"
    doc.write_text("s3_interaction_overlay | 1.000000\n", encoding="utf-8")
    out_json = tmp_path / "claim_check.json"
    out_md = tmp_path / "claim_check.md"

    exit_code = module.main(
        [
            "--claim-matrix",
            str(matrix),
            "--paths",
            str(doc),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )

    assert exit_code == 1
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["blocker_count"] == 1
    assert "toolsandbox_s3_strict_one" in out_md.read_text(encoding="utf-8")


def test_claim_consistency_warning_can_be_promoted_to_blocker(tmp_path: Path) -> None:
    module = _load_module()
    matrix = tmp_path / "paper_claim_matrix.yaml"
    _write_matrix(matrix)
    doc = tmp_path / "mixed.md"
    doc.write_text("BFCL exact-call results are mixed into the ToolSandbox headline here.\n", encoding="utf-8")

    report = module.build_report(matrix, [doc])
    assert report["blocker_count"] == 0
    assert report["warning_count"] == 1
    assert module.main(["--claim-matrix", str(matrix), "--paths", str(doc)]) == 0
    assert module.main(["--claim-matrix", str(matrix), "--paths", str(doc), "--warnings-as-blockers"]) == 1
