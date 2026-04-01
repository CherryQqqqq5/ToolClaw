from types import SimpleNamespace

from toolclaw.registry import FileAssetRegistry


def test_file_asset_registry_persists_and_reads_assets(tmp_path) -> None:
    registry = FileAssetRegistry(str(tmp_path / "assets"))
    asset_id = registry.upsert(
        SimpleNamespace(
            snippet_id="ws_test_001",
            task_signature="phase1::test",
            capability_skeleton=["cap_retrieve", "cap_write"],
            recommended_bindings={"cap_retrieve": "search_tool"},
        )
    )
    matches = registry.query("phase1::test")
    asset = registry.get(asset_id)

    assert matches[0].asset_id == asset_id
    assert asset.capability_skeleton == ["cap_retrieve", "cap_write"]
