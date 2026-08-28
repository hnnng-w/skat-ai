import copy
import json
from dataclasses import FrozenInstanceError, fields
from types import MappingProxyType

import pytest
from test_historical_declarer_card_exposure_continuation import (
    build_event_record as build_declarer_exposure_continuation,
)
from test_historical_defender_open_play_continuation import (
    build_event_record as build_defender_open_play_continuation,
)
from test_historical_game import (
    build_historical_input,
    build_typed_historical_review_inputs,
)
from test_input_schema import INPUT_VALIDATOR
from test_session_transitions import (
    _apply,
    _live_declaration_state,
    _retrospective_before_play,
)

import skatmind.session_position_export as position_export_module
from skatmind.api.v1.contracts import WorkflowV1
from skatmind.deck import get_full_deck
from skatmind.errors import SkatMindInvariantError
from skatmind.game_declaration import GameDeclaration
from skatmind.historical_snapshot_adapter import build_position_from_historical_snapshot
from skatmind.input_loader import build_position_from_document, get_input_workflow
from skatmind.session_commands import (
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionPublicHandCommandV1,
)
from skatmind.session_export_contracts import SessionRequestExportV1
from skatmind.session_position_export import (
    SESSION_POSITION_EXPORT_OPTIONS_VERSION,
    SESSION_POSITION_EXPORT_POLICY,
    SessionPositionExportOptionsV1,
    export_session_position_analysis_request_v1,
)
from skatmind.session_transitions import apply_session_command_v1, replay_session_state_v1


def _search_settings() -> dict:
    return {
        "random_seed": 113,
        "max_remaining_tricks": 3,
        "max_depth_plies": 9,
        "max_nodes": 100_000,
        "max_selected_worlds": 20,
        "max_sampled_worlds": 20,
        "minimum_comparable_worlds": 5,
        "wall_clock_timeout_ms": None,
    }


def _options(
    *,
    recommendation_method: str | None = None,
    bounded_search_settings: dict | None = None,
) -> SessionPositionExportOptionsV1:
    return SessionPositionExportOptionsV1(
        sample_count=25,
        random_seed=42,
        use_basic_opponent_strategy=True,
        recommendation_method=recommendation_method,
        bounded_search_settings=bounded_search_settings,
    )


def _chronological_plays(data: dict) -> list[dict]:
    return [play for trick in data["tricks"] for play in trick["plays"]]


def _state_for_decision(data: dict, decision_index: int):
    plays = _chronological_plays(data)
    local_player_id = plays[decision_index - 1]["player_id"]
    state = _retrospective_before_play(
        data,
        local_player_id=local_player_id,
    )
    event = data.get("game_events", [None])[0]
    event_recorded = False
    if event is not None and event["after_play_count"] == 0:
        state = _apply(
            state,
            SetSessionGameEventCommandV1(
                expected_revision=state.revision,
                event=event,
            ),
        )
        event_recorded = True
    for play_count, play in enumerate(plays[: decision_index - 1], start=1):
        state = _apply(
            state,
            RecordSessionPlayCommandV1(
                expected_revision=state.revision,
                player_id=play["player_id"],
                card=play["card"],
            ),
        )
        if (
            event is not None
            and not event_recorded
            and event["after_play_count"] == play_count
        ):
            state = _apply(
                state,
                SetSessionGameEventCommandV1(
                    expected_revision=state.revision,
                    event=event,
                ),
            )
            event_recorded = True
    assert event is None or event["after_play_count"] >= decision_index or event_recorded
    assert state.validation.position_export.status == "available"
    return state


def _live_ouvert_defender_state():
    state = _live_declaration_state()
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id="player-b",
        ),
    )
    return _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=GameDeclaration(
                game_type="grand",
                ouvert=True,
                bid_value=24,
            ),
        ),
    )


def _set_opponent_ouvert_hand(state):
    return _apply(
        state,
        SetSessionPublicHandCommandV1(
            expected_revision=state.revision,
            source="declared_ouvert",
            player_id="player-b",
            cards=get_full_deck()[10:20],
        ),
    )


def test_position_export_constants_and_options_contract_are_exact() -> None:
    source_settings = _search_settings()
    options = _options(
        recommendation_method="bounded_search",
        bounded_search_settings=source_settings,
    )
    source_settings["max_nodes"] = 1

    assert SESSION_POSITION_EXPORT_OPTIONS_VERSION == 1
    assert SESSION_POSITION_EXPORT_POLICY == "information_safe_ready_local_decision"
    assert [field.name for field in fields(SessionPositionExportOptionsV1)] == [
        "session_position_export_options_version",
        "sample_count",
        "random_seed",
        "use_basic_opponent_strategy",
        "recommendation_method",
        "bounded_search_settings",
    ]
    assert not hasattr(options, "__dict__")
    assert isinstance(options.bounded_search_settings, MappingProxyType)
    assert options.bounded_search_settings["max_nodes"] == 100_000
    first = options.to_dict()
    first["bounded_search_settings"]["max_nodes"] = 2
    assert options.to_dict()["bounded_search_settings"]["max_nodes"] == 100_000
    json.dumps(options.to_dict())
    with pytest.raises(FrozenInstanceError):
        options.sample_count = 2
    with pytest.raises(TypeError):
        SessionPositionExportOptionsV1(1, 1, True, None, None)


@pytest.mark.parametrize("sample_count", (0, 100_001, True, 1.0))
def test_options_reject_invalid_sample_counts(sample_count: object) -> None:
    with pytest.raises(ValueError, match="sample_count"):
        SessionPositionExportOptionsV1(
            sample_count=sample_count,
            random_seed=0,
            use_basic_opponent_strategy=True,
            recommendation_method=None,
            bounded_search_settings=None,
        )


@pytest.mark.parametrize("random_seed", (True, 1.0, None, "1"))
def test_options_require_a_strict_integer_seed(random_seed: object) -> None:
    with pytest.raises(ValueError, match="random_seed"):
        SessionPositionExportOptionsV1(
            sample_count=1,
            random_seed=random_seed,
            use_basic_opponent_strategy=True,
            recommendation_method=None,
            bounded_search_settings=None,
        )


@pytest.mark.parametrize(
    ("method", "settings"),
    (
        (None, _search_settings()),
        ("immediate_expected_value", _search_settings()),
        ("bounded_search", None),
        ("auto", None),
        ("unknown", None),
    ),
)
def test_options_reuse_exact_recommendation_configuration_validation(
    method: str | None,
    settings: dict | None,
) -> None:
    with pytest.raises(ValueError):
        _options(recommendation_method=method, bounded_search_settings=settings)


def test_public_hand_command_is_narrow_canonical_and_defensive() -> None:
    cards = ["SA", "C7"]
    command = SetSessionPublicHandCommandV1(
        expected_revision=4,
        source="declared_ouvert",
        player_id="player-b",
        cards=cards,
    )
    cards[0] = "D7"
    assert command.cards == ("C7", "SA")
    assert command.to_dict() == {
        "command_version": 1,
        "kind": "set_public_hand",
        "expected_revision": 4,
        "source": "declared_ouvert",
        "player_id": "player-b",
        "cards": ["C7", "SA"],
    }
    with pytest.raises(ValueError, match="source"):
        SetSessionPublicHandCommandV1(
            expected_revision=0,
            source="arbitrary",
            player_id="player-b",
            cards=[],
        )
    with pytest.raises(ValueError, match="duplicate"):
        SetSessionPublicHandCommandV1(
            expected_revision=0,
            source="declared_ouvert",
            player_id="player-b",
            cards=["CA", "CA"],
        )
    with pytest.raises(ValueError, match="at least one"):
        SetSessionPublicHandCommandV1(
            expected_revision=0,
            source="declared_ouvert",
            player_id="player-b",
            cards=[],
        )


def test_opponent_ouvert_readiness_requires_then_accepts_exact_public_hand() -> None:
    state = _live_ouvert_defender_state()
    assert state.phase == "play"
    assert state.validation.position_export.status == "unavailable"
    assert any(
        diagnostic.path == "/exact_public_hands"
        for diagnostic in state.validation.diagnostics
    )
    unavailable = export_session_position_analysis_request_v1(state, _options())
    assert unavailable.status == "unavailable"

    state = _set_opponent_ouvert_hand(state)
    projection = replay_session_state_v1(state)
    assert state.validation.position_export.status == "available"
    assert projection.public_hand_for("player-b") == tuple(get_full_deck()[10:20])
    result = export_session_position_analysis_request_v1(state, _options())
    root = result.request.to_dict()["document"]
    assert root["public_declarer_cards"] == get_full_deck()[10:20]
    assert root["left_hand_size"] == 10

    repeated = apply_session_command_v1(
        state,
        SetSessionPublicHandCommandV1(
            expected_revision=state.revision,
            source="declared_ouvert",
            player_id="player-b",
            cards=get_full_deck()[10:20],
        ),
    )
    assert repeated.status == "rejected"
    assert repeated.state is state

    wrong_owner = apply_session_command_v1(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card="SK",
        ),
    )
    assert wrong_owner.status == "rejected"
    assert wrong_owner.diagnostics[0].code == "card_ownership_violation"


def test_public_hand_command_rejects_phase_declaration_owner_count_and_conflicts() -> None:
    declaration_state = _live_declaration_state()
    phase_result = apply_session_command_v1(
        declaration_state,
        SetSessionPublicHandCommandV1(
            expected_revision=declaration_state.revision,
            source="declared_ouvert",
            player_id="player-b",
            cards=["CA"],
        ),
    )
    assert phase_result.status == "rejected"
    assert phase_result.diagnostics[0].code == "phase_violation"

    state = _live_ouvert_defender_state()
    for player_id, cards, expected_code in (
        ("player-c", get_full_deck()[20:30], "player_reference_violation"),
        ("player-b", get_full_deck()[10:19], "card_ownership_violation"),
        ("player-b", [*get_full_deck()[10:19], "CA"], "card_ownership_violation"),
    ):
        result = apply_session_command_v1(
            state,
            SetSessionPublicHandCommandV1(
                expected_revision=state.revision,
                source="declared_ouvert",
                player_id=player_id,
                cards=cards,
            ),
        )
        assert result.status == "rejected"
        assert result.diagnostics[0].code == expected_code

    non_ouvert = _live_declaration_state()
    non_ouvert = _apply(
        non_ouvert,
        SetSessionDeclarerCommandV1(
            expected_revision=non_ouvert.revision,
            declarer_player_id="player-b",
        ),
    )
    non_ouvert = _apply(
        non_ouvert,
        SetSessionDeclarationCommandV1(
            expected_revision=non_ouvert.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    result = apply_session_command_v1(
        non_ouvert,
        SetSessionPublicHandCommandV1(
            expected_revision=non_ouvert.revision,
            source="declared_ouvert",
            player_id="player-b",
            cards=get_full_deck()[10:20],
        ),
    )
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "declaration_violation"


def test_declared_ouvert_and_continuation_public_hands_coexist_and_shrink_by_owner() -> None:
    state = _set_opponent_ouvert_hand(_live_ouvert_defender_state())
    defender_cards = get_full_deck()[20:30]
    state = _apply(
        state,
        SetSessionGameEventCommandV1(
            expected_revision=state.revision,
            event={
                "schema_version": 1,
                "kind": "defender_open_play_continuation",
                "after_play_count": 0,
                "exposing_defender_player_id": "player-c",
                "exposed_cards": defender_cards,
                "declarer_response": "request_continued_play",
            },
        ),
    )
    projection = replay_session_state_v1(state)
    assert tuple(player_id for player_id, _ in projection.exact_public_hands) == (
        "player-b",
        "player-c",
    )

    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card="CA",
        ),
    )
    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-b",
            card="SK",
        ),
    )
    projection = replay_session_state_v1(state)
    assert "SK" not in projection.public_hand_for("player-b")
    assert projection.public_hand_for("player-c") == tuple(defender_cards)


@pytest.mark.parametrize("decision_index", (1, 2, 3, 4))
def test_position_mapping_matches_equivalent_historical_snapshot(
    decision_index: int,
) -> None:
    data = build_historical_input()
    record, snapshot_summary = build_typed_historical_review_inputs(data)
    snapshot = snapshot_summary.snapshots[decision_index - 1]
    expected = build_position_from_historical_snapshot(snapshot, record)
    state = _state_for_decision(data, decision_index)
    projection = replay_session_state_v1(state)
    result = export_session_position_analysis_request_v1(state, _options())

    assert result.status == "available"
    assert result.target == "position_analysis"
    assert result.request.workflow is WorkflowV1.POSITION_ANALYSIS
    root = result.request.to_dict()["document"]
    stable_to_relative = {
        player_id: relative
        for relative, player_id in snapshot.relative_player_map.items()
    }
    assert root["player_role"] == expected.state.player_role
    assert root["declarer_player"] == stable_to_relative[record.declarer_player_id]
    assert root["player_position"] == expected.state.player_position
    assert root["hand"] == expected.state.hand
    assert root["current_trick"] == expected.state.current_trick
    assert root["completed_tricks"] == expected.state.completed_tricks
    assert root["trick_leader"] == expected.state.trick_leader
    assert root["next_player"] == "me"
    assert root["declarer_points"] == root["defender_points"] == 0
    assert sum(
        trick.trick_points
        for trick in projection.completed_tricks
        if trick.winner_side == "declarer"
    ) == expected.state.declarer_points
    assert sum(
        trick.trick_points
        for trick in projection.completed_tricks
        if trick.winner_side == "defenders"
    ) == expected.state.defender_points
    assert root["left_hand_size"] == expected.left_hand_size
    assert root["right_hand_size"] == expected.right_hand_size
    assert root["skat"] == expected.state.skat
    assert root["game_declaration"]["matadors"] == (
        expected.game_declaration.matadors
    )
    assert root["played_cards"] == []
    assert root["analysis_mode"] == "live_decision"
    assert root["game_end_reason"] == "not_ended"
    assert list(INPUT_VALIDATOR.iter_errors(root)) == []
    assert build_position_from_document(copy.deepcopy(root)) is not None
    assert get_input_workflow(copy.deepcopy(root)) == "position_analysis"


def test_all_three_stable_to_relative_seat_maps_are_exact() -> None:
    data = build_historical_input()
    expected_maps = (
        {"me": "player-a", "left": "player-b", "right": "player-c"},
        {"me": "player-b", "left": "player-c", "right": "player-a"},
        {"me": "player-c", "left": "player-a", "right": "player-b"},
    )
    for decision_index, expected_map in enumerate(expected_maps, start=1):
        state = _state_for_decision(data, decision_index)
        projection = replay_session_state_v1(state)
        local_index = projection.player_ids.index(state.local_player_id)
        actual = {
            "me": state.local_player_id,
            "left": projection.player_ids[(local_index + 1) % 3],
            "right": projection.player_ids[(local_index - 1) % 3],
        }
        assert actual == expected_map


def test_last_decision_exports_zero_opponent_hand_sizes() -> None:
    state = _state_for_decision(build_historical_input(), 30)
    root = export_session_position_analysis_request_v1(
        state,
        _options(),
    ).request.to_dict()["document"]
    assert root["left_hand_size"] == root["right_hand_size"] == 0


def test_skat_visibility_never_leaks_retrospective_skat_to_defender() -> None:
    data = build_historical_input()
    defender = _state_for_decision(data, 1)
    defender_root = export_session_position_analysis_request_v1(
        defender, _options()
    ).request.to_dict()["document"]
    assert defender_root["skat"] == []
    assert defender_root["skat_visibility"] == "unknown"
    defender_serialized = json.dumps(defender_root)
    assert all(f'"{card}"' not in defender_serialized for card in data["skat"])

    declarer = _state_for_decision(data, 2)
    declarer_root = export_session_position_analysis_request_v1(
        declarer, _options()
    ).request.to_dict()["document"]
    assert declarer_root["skat"] == data["discarded_cards"]
    assert declarer_root["skat_visibility"] == "known_to_declarer"
    assert "known_post_game" not in json.dumps(declarer_root)


def test_local_and_opponent_ouvert_export_only_authorized_declarer_cards() -> None:
    data = build_historical_input(
        game_type="grand",
        hand_game=True,
        declarer_player_id="player-b",
        bid_value=24,
    )
    data["declaration"]["ouvert"] = True
    data["declaration"]["schneider_announced"] = True
    data["declaration"]["schwarz_announced"] = True

    opponent_state = _state_for_decision(data, 1)
    opponent_root = export_session_position_analysis_request_v1(
        opponent_state, _options()
    ).request.to_dict()["document"]
    assert opponent_root["public_declarer_cards"] == list(
        replay_session_state_v1(opponent_state).remaining_hand_for("player-b")
    )

    local_state = _state_for_decision(data, 2)
    local_root = export_session_position_analysis_request_v1(
        local_state, _options()
    ).request.to_dict()["document"]
    assert local_root["player_role"] == "declarer"
    assert "public_declarer_cards" not in local_root
    assert local_root["hand"] == list(
        replay_session_state_v1(local_state).remaining_hand_for("player-b")
    )


@pytest.mark.parametrize(
    ("builder", "expected_kind", "card_field"),
    (
        (
            build_declarer_exposure_continuation,
            "declarer_card_exposure",
            "public_declarer_cards",
        ),
        (
            build_defender_open_play_continuation,
            "defender_open_play",
            "public_exposing_defender_cards",
        ),
    ),
)
def test_both_historical_continuations_map_to_flat_current_hand_union(
    builder,
    expected_kind: str,
    card_field: str,
) -> None:
    data = builder(after_play_count=12)
    state = _state_for_decision(data, 13)
    projection = replay_session_state_v1(state)
    root = export_session_position_analysis_request_v1(
        state, _options()
    ).request.to_dict()["document"]
    continuation = root["game_continuation"]
    event = data["game_events"][0]
    owner = event.get("exposing_defender_player_id", data["declarer_player_id"])
    assert continuation["kind"] == expected_kind
    assert continuation[card_field] == list(projection.public_hand_for(owner))
    assert list(INPUT_VALIDATOR.iter_errors(root)) == []


@pytest.mark.parametrize(
    ("method", "settings", "expected_fields"),
    (
        (None, None, set()),
        ("immediate_expected_value", None, {"recommendation_method"}),
        (
            "bounded_search",
            _search_settings(),
            {"recommendation_method", "bounded_search_settings"},
        ),
        (
            "auto",
            _search_settings(),
            {"recommendation_method", "bounded_search_settings"},
        ),
    ),
)
def test_recommendation_settings_are_exported_without_execution(
    method: str | None,
    settings: dict | None,
    expected_fields: set[str],
) -> None:
    state = _state_for_decision(build_historical_input(), 1)
    root = export_session_position_analysis_request_v1(
        state,
        _options(
            recommendation_method=method,
            bounded_search_settings=settings,
        ),
    ).request.to_dict()["document"]
    actual_fields = {
        field
        for field in ("recommendation_method", "bounded_search_settings")
        if field in root
    }
    assert actual_fields == expected_fields
    if settings is not None:
        assert root["bounded_search_settings"] == settings
    assert root["played_cards"] == []
    assert all("players" in trick for trick in root["completed_tricks"])


def test_request_is_immutable_and_excludes_session_and_private_fields() -> None:
    data = build_historical_input()
    state = _state_for_decision(data, 1)
    result = export_session_position_analysis_request_v1(state, _options())
    root = result.request.to_dict()["document"]
    serialized = json.dumps(root)
    forbidden = {
        "session_id",
        "source_revision",
        "capture_mode",
        "command_log",
        "validation",
        "actual_card_played",
        "game_end",
        "remaining_known_hands",
        "search_worlds",
        "principal_variation",
        "field_provenance",
    }
    assert all(f'"{field}"' not in serialized for field in forbidden)
    hidden_cards = set(data["players"][1]["initial_hand"]) | set(
        data["players"][2]["initial_hand"]
    )
    assert all(f'"{card}"' not in serialized for card in hidden_cards)
    with pytest.raises(TypeError):
        result.request.document["hand"] = ()
    mutable = result.to_dict()
    mutable["request"]["document"]["hand"].clear()
    assert result.request.document["hand"]


def test_unavailable_and_available_exports_have_exact_replay_builder_counts(
    monkeypatch,
) -> None:
    unavailable_state = _live_ouvert_defender_state()
    replay_count = 0
    builder_count = 0
    original_replay = position_export_module.replay_session_state_v1
    original_builder = position_export_module.build_position_from_document

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def counted_builder(value):
        nonlocal builder_count
        builder_count += 1
        return original_builder(value)

    monkeypatch.setattr(position_export_module, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(
        position_export_module,
        "build_position_from_document",
        counted_builder,
    )
    unavailable = position_export_module.export_session_position_analysis_request_v1(
        unavailable_state,
        _options(),
    )
    assert unavailable.status == "unavailable"
    assert replay_count == 1
    assert builder_count == 0

    available_state = _set_opponent_ouvert_hand(unavailable_state)
    available = position_export_module.export_session_position_analysis_request_v1(
        available_state,
        _options(),
    )
    assert available.status == "available"
    assert replay_count == 2
    assert builder_count == 1


def test_ready_position_builder_failure_is_an_invariant_with_original_cause(
    monkeypatch,
) -> None:
    state = _state_for_decision(build_historical_input(), 1)

    def fail_builder(value):
        del value
        raise ValueError("position builder disagreement")

    monkeypatch.setattr(
        position_export_module,
        "build_position_from_document",
        fail_builder,
    )
    with pytest.raises(SkatMindInvariantError) as captured:
        export_session_position_analysis_request_v1(state, _options())
    assert isinstance(captured.value.__cause__, ValueError)
    assert str(captured.value.__cause__) == "position builder disagreement"


def test_position_export_rejects_wrong_types() -> None:
    state = _state_for_decision(build_historical_input(), 1)
    with pytest.raises(ValueError, match="SessionStateV1"):
        export_session_position_analysis_request_v1(object(), _options())
    with pytest.raises(ValueError, match="SessionPositionExportOptionsV1"):
        export_session_position_analysis_request_v1(state, object())


def test_generalized_export_result_rejects_mixed_position_invariants() -> None:
    state = _state_for_decision(build_historical_input(), 1)
    available = export_session_position_analysis_request_v1(state, _options())
    assert isinstance(available, SessionRequestExportV1)
    with pytest.raises(ValueError, match="workflow"):
        SessionRequestExportV1(
            session_id=state.session_id,
            source_revision=state.revision,
            target="historical_game",
            status="available",
            request=available.request,
            diagnostics=(),
        )
