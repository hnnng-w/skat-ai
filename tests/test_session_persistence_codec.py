import copy
import hashlib
import json

import pytest
from test_historical_game import build_historical_input
from test_session_decision_checkpoint import _checkpoint
from test_session_history import _correction, _record_revision
from test_session_position_export import _options
from test_session_transitions import (
    _apply,
    _complete_retrospective_session,
    _players,
)

import skatmind.session_persistence_codec as codec_module
from skatmind.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skatmind.errors import SkatMindValidationError
from skatmind.game_declaration import GameDeclaration
from skatmind.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameMetadataCommandV1,
    SetSessionPublicHandCommandV1,
)
from skatmind.session_decision_checkpoint import (
    SessionDecisionCheckpointV1,
    build_session_decision_checkpoint_v1,
)
from skatmind.session_historical_export import export_session_historical_game_request_v1
from skatmind.session_history import rewind_session_state_v1
from skatmind.session_persistence_codec import (
    build_session_persistence_document_v1,
    build_session_state_fingerprint_v1,
    resume_session_document_v1,
)
from skatmind.session_position_export import export_session_position_analysis_request_v1
from skatmind.session_transitions import create_session_state_v1


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _commands() -> tuple[object, ...]:
    return (
        SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="game-155",
            played_at=None,
        ),
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="skat",
            player_id=None,
            card="CA",
        ),
        SetSessionDeclarerCommandV1(
            expected_revision=0,
            declarer_player_id="player-a",
        ),
        SetSessionDeclarationCommandV1(
            expected_revision=0,
            declaration=GameDeclaration(
                game_type="grand",
                hand_game=True,
                matadors=2,
                bid_value=24,
            ),
        ),
        RecordSessionDiscardCommandV1(expected_revision=0, card="D7"),
        RecordSessionPlayCommandV1(
            expected_revision=0,
            player_id="player-a",
            card="S7",
        ),
        SetSessionGameEventCommandV1(
            expected_revision=0,
            event={
                "schema_version": 1,
                "kind": "declarer_card_exposure_continuation",
                "after_play_count": 0,
                "exposure": {
                    "form": "shown_to_defender",
                    "shown_to_defender_player_id": "player-b",
                },
                "claimed_play_level": "simple",
                "defender_responses": [
                    {
                        "defender_player_id": "player-b",
                        "response": "continue",
                        "form": "explicit",
                    },
                    {
                        "defender_player_id": "player-c",
                        "response": "accept",
                        "form": "explicit",
                    },
                ],
                "public_declarer_cards": ["CA"],
            },
        ),
        SetSessionGameEndCommandV1(
            expected_revision=0,
            game_end_reason="normal_completion",
            game_end=None,
        ),
        PromoteSessionToRetrospectiveCommandV1(expected_revision=0),
        SetSessionPublicHandCommandV1(
            expected_revision=0,
            source="declared_ouvert",
            player_id="player-a",
            cards=("CA", "C10"),
        ),
    )


def _corrected_same_revision_states():
    state, _, _ = _checkpoint()
    declaration_revision = _record_revision(state, "set_declaration")
    corrected = _correction(
        state,
        declaration_revision,
        SetSessionDeclarationCommandV1(
            expected_revision=declaration_revision - 1,
            declaration=GameDeclaration(
                game_type="grand",
                hand_game=True,
                bid_value=48,
            ),
        ),
    )
    assert corrected.status == "applied"
    assert corrected.state.revision == state.revision
    return state, corrected.state


def test_state_and_content_fingerprints_match_independent_domain_oracles() -> None:
    state, _, checkpoint = _checkpoint()
    document = build_session_persistence_document_v1(
        state,
        decision_checkpoints=(checkpoint,),
    )
    expected_state = hashlib.sha256(
        b"skatmind\0session_state_v1\0" + _canonical_bytes(state.to_dict())
    ).hexdigest()
    content = document.to_dict()
    del content["content_fingerprint"]
    expected_content = hashlib.sha256(
        b"skatmind\0session_persistence_v1\0" + _canonical_bytes(content)
    ).hexdigest()
    assert document.state_fingerprint == expected_state
    assert document.content_fingerprint == expected_content
    assert build_session_state_fingerprint_v1(state) == expected_state
    assert len(expected_state) == len(expected_content) == 64


def test_equal_revision_corrected_histories_have_distinct_state_and_content_identity() -> None:
    source, corrected = _corrected_same_revision_states()
    source_document = build_session_persistence_document_v1(source)
    corrected_document = build_session_persistence_document_v1(corrected)
    assert source.revision == corrected.revision
    assert source.command_log != corrected.command_log
    assert source_document.state_fingerprint != corrected_document.state_fingerprint
    assert source_document.content_fingerprint != corrected_document.content_fingerprint


def test_checkpoint_content_changes_only_the_content_fingerprint() -> None:
    state, _, checkpoint = _checkpoint()
    without = build_session_persistence_document_v1(state)
    with_checkpoint = build_session_persistence_document_v1(
        state,
        decision_checkpoints=(checkpoint,),
    )
    assert without.state_fingerprint == with_checkpoint.state_fingerprint
    assert without.content_fingerprint != with_checkpoint.content_fingerprint


def test_multiple_same_revision_checkpoints_are_canonical_and_order_independent() -> None:
    state, _, checkpoint = _checkpoint()
    alternate_export = export_session_position_analysis_request_v1(
        state,
        _options(recommendation_method="immediate_expected_value"),
    )
    alternate = build_session_decision_checkpoint_v1(
        state=state,
        position_export=alternate_export,
    )
    assert alternate.source_revision == checkpoint.source_revision
    assert alternate != checkpoint
    forward = build_session_persistence_document_v1(
        state,
        decision_checkpoints=(checkpoint, alternate),
    )
    reverse = build_session_persistence_document_v1(
        state,
        decision_checkpoints=(alternate, checkpoint),
    )
    assert forward == reverse
    assert forward.content_fingerprint == reverse.content_fingerprint
    assert len(forward.decision_checkpoints) == 2


def test_every_current_command_reconstructs_exactly_and_rejects_field_drift() -> None:
    for index, command in enumerate(_commands()):
        source = command.to_dict()
        rebuilt = codec_module._build_command(source, path=f"/command/{index}")
        assert rebuilt == command
        assert rebuilt.to_dict() == source

        missing = dict(source)
        missing.pop(next(iter(missing)))
        with pytest.raises(SkatMindValidationError, match="Missing"):
            codec_module._build_command(missing, path=f"/command/{index}")
        with pytest.raises(SkatMindValidationError, match="Unsupported"):
            codec_module._build_command(
                {**source, "unknown": None},
                path=f"/command/{index}",
            )


def test_command_reconstruction_preserves_nulls_and_rejects_nested_unknown_fields() -> None:
    metadata, dealt, *_, game_end, _, _ = _commands()
    assert codec_module._build_command(metadata.to_dict(), path="/command").played_at is None
    assert codec_module._build_command(dealt.to_dict(), path="/command").player_id is None
    assert codec_module._build_command(game_end.to_dict(), path="/command").game_end is None

    event = _commands()[6].to_dict()
    event["event"]["exposure"]["unknown"] = True
    with pytest.raises(SkatMindValidationError, match="Unsupported"):
        codec_module._build_command(event, path="/command")

    unhashable_end_reason = game_end.to_dict()
    unhashable_end_reason["game_end_reason"] = []
    with pytest.raises(SkatMindValidationError, match="game_end_reason"):
        codec_module._build_command(unhashable_end_reason, path="/command")


def test_document_builder_rejects_checkpoint_with_invalid_session_export_options() -> None:
    state, _, checkpoint = _checkpoint()
    request_data = checkpoint.request.to_dict()
    request_data["document"]["random_seed"] = None
    request = RequestDocumentV1(
        workflow=WorkflowV1.POSITION_ANALYSIS,
        document=request_data["document"],
    )
    checkpoint_data = checkpoint.to_dict()
    checkpoint_data["request"] = request
    permissive_checkpoint = SessionDecisionCheckpointV1(**checkpoint_data)
    with pytest.raises(ValueError, match="canonical or valid"):
        build_session_persistence_document_v1(
            state,
            decision_checkpoints=(permissive_checkpoint,),
        )


def test_strict_state_validation_and_request_checkpoint_reconstruction() -> None:
    state, _, checkpoint = _checkpoint()
    rebuilt_state = codec_module._build_state(state.to_dict(), path="/state")
    rebuilt_checkpoint = codec_module._build_checkpoint(
        checkpoint.to_dict(),
        path="/decision_checkpoints/0",
    )
    assert rebuilt_state == state
    assert rebuilt_state.validation == state.validation
    assert rebuilt_checkpoint == checkpoint
    assert rebuilt_checkpoint.request == checkpoint.request

    noncanonical = state.to_dict()
    noncanonical["players"].reverse()
    with pytest.raises(SkatMindValidationError, match="canonical"):
        codec_module._build_state(noncanonical, path="/state")

    extra_request = checkpoint.to_dict()
    extra_request["request"]["document"]["output_path"] = "result.json"
    with pytest.raises(SkatMindValidationError):
        codec_module._build_checkpoint(
            extra_request,
            path="/decision_checkpoints/0",
        )


def test_in_memory_resume_rejects_top_level_state_and_fingerprint_tampering() -> None:
    state, _, checkpoint = _checkpoint()
    source = build_session_persistence_document_v1(
        state,
        decision_checkpoints=(checkpoint,),
    ).to_dict()
    assert resume_session_document_v1(source).document.to_dict() == source

    cases = []
    missing = copy.deepcopy(source)
    missing.pop("document_kind")
    cases.append(missing)
    unknown = copy.deepcopy(source)
    unknown["path"] = "private.json"
    cases.append(unknown)
    wrong_state = copy.deepcopy(source)
    wrong_state["state"]["command_log"][0]["command"]["game_id"] = "changed"
    cases.append(wrong_state)
    wrong_state_fingerprint = copy.deepcopy(source)
    wrong_state_fingerprint["state_fingerprint"] = "0" * 64
    cases.append(wrong_state_fingerprint)
    wrong_content_fingerprint = copy.deepcopy(source)
    wrong_content_fingerprint["content_fingerprint"] = "f" * 64
    cases.append(wrong_content_fingerprint)
    for document in cases:
        with pytest.raises(SkatMindValidationError):
            resume_session_document_v1(document)


def test_resume_recomputes_current_ancestor_future_and_diverged_lineage() -> None:
    checkpoint_state, _, checkpoint = _checkpoint()
    played = _apply(
        checkpoint_state,
        RecordSessionPlayCommandV1(
            expected_revision=checkpoint_state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    future_state = rewind_session_state_v1(
        checkpoint_state,
        expected_revision=checkpoint_state.revision,
        target_revision=checkpoint.source_revision - 1,
    ).state
    _, diverged = _corrected_same_revision_states()
    states = (checkpoint_state, played, future_state, diverged)
    expected = ("current", "ancestor", "future", "diverged")
    relationships = tuple(
        resume_session_document_v1(
            build_session_persistence_document_v1(
                state,
                decision_checkpoints=(checkpoint,),
            )
        )
        .checkpoint_lineage[0]
        .relationship
        for state in states
    )
    assert relationships == expected


def test_document_build_and_resume_each_use_one_replay_and_two_hashes(monkeypatch) -> None:
    state = create_session_state_v1(
        session_id="session-persistence-counts",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    counts = {"replay": 0, "sha256": 0}
    original_replay = codec_module.replay_session_state_v1
    original_sha256 = codec_module.hashlib.sha256

    def counted_replay(value):
        counts["replay"] += 1
        return original_replay(value)

    def counted_sha256(value=b""):
        counts["sha256"] += 1
        return original_sha256(value)

    monkeypatch.setattr(codec_module, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(codec_module.hashlib, "sha256", counted_sha256)
    document = codec_module.build_session_persistence_document_v1(state)
    assert counts == {"replay": 1, "sha256": 2}

    counts = {"replay": 0, "sha256": 0}
    resumed = codec_module.resume_session_document_v1(document)
    assert resumed.document == document
    assert counts == {"replay": 1, "sha256": 2}


def test_resumed_states_remain_compatible_with_transitions_and_both_exports() -> None:
    state, _, _ = _checkpoint()
    resumed = resume_session_document_v1(
        build_session_persistence_document_v1(state)
    ).document.state
    transition = _apply(
        resumed,
        RecordSessionPlayCommandV1(
            expected_revision=resumed.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    assert transition.revision == resumed.revision + 1
    assert export_session_position_analysis_request_v1(resumed, _options()).status == ("available")

    historical_state = _complete_retrospective_session(build_historical_input())
    historical_document = build_session_persistence_document_v1(historical_state)
    resumed_historical = resume_session_document_v1(historical_document).document.state
    assert export_session_historical_game_request_v1(resumed_historical) == (
        export_session_historical_game_request_v1(historical_state)
    )


def test_private_persistence_retains_state_facts_without_analysis_or_provenance() -> None:
    state = _complete_retrospective_session(build_historical_input())
    serialized = json.dumps(build_session_persistence_document_v1(state).to_dict())
    assert "initial_hand" not in serialized
    assert '"record_dealt_card"' in serialized
    assert '"destination": "skat"' in serialized
    assert '"record_play"' in serialized
    for excluded in (
        "analysis_result",
        "search_worlds",
        "simulation_ownership",
        "proof_state",
        "cache",
        "principal_variation",
        "field_provenance",
    ):
        assert f'"{excluded}"' not in serialized
