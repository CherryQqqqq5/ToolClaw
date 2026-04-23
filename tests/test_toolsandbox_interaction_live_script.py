import json
from pathlib import Path

from scripts.score_toolsandbox_interaction_live import _actual_targets, _prf, _value_matches
from toolclaw.interaction.reply_provider import DeterministicModeReplyProvider
from toolclaw.interaction.repair_updater import InteractionRequest


def _request(**metadata):
    base = {
        "patch_targets": {"retrieved_info": True},
        "suggested_values": {"retrieved_info": "enabled"},
    }
    base.update(metadata)
    return InteractionRequest(
        interaction_id="int_test",
        question="What value should be used for retrieved_info?",
        expected_answer_type="json_patch",
        metadata=base,
    )


def test_interaction_live_irrelevant_reply_has_no_semantic_target():
    reply = DeterministicModeReplyProvider("irrelevant").reply(_request())

    assert reply.status == "accept"
    assert reply.payload == {"raw_text": "irrelevant answer"}
    assert reply.metadata["interaction_live_user_mode"] == "irrelevant"
    assert _actual_targets({"reply_metadata": {"selected_targets": ["raw_text"]}}) == set()


def test_interaction_live_wrong_parameter_is_not_target_aligned():
    reply = DeterministicModeReplyProvider("wrong_parameter").reply(_request())

    assert reply.payload == {"input_patch": {"value": "wrong_parameter"}}
    assert _actual_targets({"reply_metadata": {"selected_targets": ["value"]}}) == set()


def test_interaction_live_partial_reply_targets_one_expected_slot():
    reply = DeterministicModeReplyProvider("partial").reply(_request())

    assert reply.payload == {"retrieved_info": "enabled"}
    metadata = {
        "reply_metadata": {
            "selected_targets": ["retrieved_info"],
            "decoded_slot_updates": {"retrieved_info": "enabled"},
        }
    }
    gold = {"gold_decoded_signal": {"slot_updates": {"retrieved_info": "enabled"}}}
    assert _actual_targets(metadata) == {"retrieved_info"}
    assert _value_matches(metadata, gold, "retrieved_info") is True


def test_interaction_live_prf_counts_false_positive_rate():
    metrics = _prf(tp=1, fp=1, fn=2)

    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 1 / 3
    assert round(metrics["f1"], 6) == round(0.4, 6)
    assert metrics["false_positive_rate"] == 0.5
