from types import SimpleNamespace

from toolclaw.registry import FileAssetRegistry


def test_file_asset_registry_persists_and_reads_assets(tmp_path) -> None:
    registry = FileAssetRegistry(str(tmp_path / "assets"))
    asset_id = registry.upsert(
        SimpleNamespace(
            snippet_id="ws_test_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_retrieve": "search_tool"},
        )
    )
    matches = registry.query(
        "phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
        required_capability_skeleton=["cap_retrieve", "cap_write"],
        failure_context="none",
    )
    asset = registry.get(asset_id)

    assert matches[0].asset_id == asset_id
    assert asset.capability_skeleton == ["cap_retrieve", "cap_write"]


def test_file_asset_registry_indexes_signature_aliases(tmp_path) -> None:
    registry = FileAssetRegistry(str(tmp_path / "assets"))
    asset_id = registry.upsert(
        SimpleNamespace(
            snippet_id="ws_test_002",
            task_signature="phase1::family=toolsandbox_reuse_transfer_001::caps=cap_retrieve+cap_write::fail=binding_failure::goal=retrieve_the_customer_handoff_summary",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            metadata={
                "source_task_id": "contact_edit__pair00__pass1",
                "reuse_family_id": "contact_edit__pair00",
                "semantic_reuse_family": "contact_edit",
                "task_signature_aliases": [
                    "phase1::family=toolsandbox_reuse_transfer_001::caps=cap_retrieve+cap_write::fail=binding_failure"
                ]
            },
        )
    )

    matches = registry.query("phase1::family=toolsandbox_reuse_transfer_001::caps=cap_retrieve+cap_write::fail=binding_failure")

    assert matches[0].asset_id == asset_id
    assert matches[0].metadata["reuse_mode"] == "transfer_reuse"
    assert matches[0].metadata["exact_score"] == 0.0
    assert matches[0].metadata["source_task_id"] == "contact_edit__pair00__pass1"
    assert matches[0].metadata["source_reuse_family_id"] == "contact_edit__pair00"
    assert matches[0].metadata["source_semantic_reuse_family"] == "contact_edit"


def test_file_asset_registry_rejects_state_slot_incompatible_reuse(tmp_path) -> None:
    registry = FileAssetRegistry(str(tmp_path / "assets"))
    registry.upsert(
        SimpleNamespace(
            snippet_id="ws_test_003",
            task_signature="phase1::family=toolsandbox_state_dep_001::caps=cap_retrieve+cap_write::fail=state_failure::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            metadata={
                "failure_context": "state_failure",
                "required_state_slots": ["retrieved_info"],
            },
        )
    )

    matches = registry.query(
        "phase1::family=toolsandbox_state_dep_001::caps=cap_retrieve+cap_write::fail=state_failure::goal=retrieve_and_write_report",
        required_capability_skeleton=["cap_retrieve", "cap_write"],
        failure_context="state_failure",
        required_state_slots=["approval_token"],
    )

    assert matches == []


def test_file_asset_registry_prefers_higher_utility_execution_prior(tmp_path) -> None:
    registry = FileAssetRegistry(str(tmp_path / "assets"))
    registry.upsert(
        SimpleNamespace(
            snippet_id="ws_low_utility_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={"cap_retrieve": {"result_key": "cached_result"}},
            metadata={
                "reuse_application_hint": "binding_prior",
                "utility_gain_score": 0.0,
            },
        )
    )
    high_id = registry.upsert(
        SimpleNamespace(
            snippet_id="ws_high_utility_001",
            task_signature="phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_write": "write_tool"},
            recommended_inputs={"cap_retrieve": {"result_key": "cached_result"}},
            metadata={
                "reuse_application_hint": "execution_prior",
                "utility_gain_score": 0.4,
            },
        )
    )

    matches = registry.query(
        "phase1::family=t0_general::caps=cap_retrieve+cap_write::fail=none::goal=retrieve_and_write_report",
        required_capability_skeleton=["cap_retrieve", "cap_write"],
        failure_context="none",
    )

    assert matches[0].asset_id == high_id
    assert matches[0].metadata["reuse_application_hint"] == "execution_prior"
    assert matches[0].metadata["utility_gain_score"] == 0.4
