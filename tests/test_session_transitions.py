import copy
import json
from dataclasses import FrozenInstanceError, replace

import pytest
from test_historical_declarer_card_exposure import build_exposure_prefix
from test_historical_declarer_card_exposure_continuation import (
    build_event_record as build_declarer_exposure_continuation,
)
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_defender_open_play import build_open_play_prefix
from test_historical_defender_open_play_continuation import (
    build_event_record as build_defender_open_play_continuation,
)
from test_historical_game import build_historical_input
from test_historical_game_event_chain import add_continuation
from test_historical_open_card_throw import build_throw_prefix

import skat_ai.session_transitions as transitions
from skat_ai.deck import get_full_deck
from skat_ai.errors import SkatAIInvariantError
from skat_ai.game_declaration import GameDeclaration
from skat_ai.matador_inference import infer_matadors_from_known_ownership
from skat_ai.rules import get_legal_cards, get_trick_points, get_trick_winner
from skat_ai.session_commands import (
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameMetadataCommandV1,
)
from skat_ai.session_contracts import SessionCommandRecordV1, SessionPlayerV1, SessionStateV1
from skat_ai.session_projection import SESSION_PROJECTION_VERSION
from skat_ai.session_transitions import (
    SESSION_REPLAY_POLICY,
    SESSION_TRANSITION_ENGINE_VERSION,
    apply_session_command_v1,
    create_session_state_v1,
    replay_session_state_v1,
)
from skat_ai.session_validation import SessionValidationResultV1


def _players() -> tuple[SessionPlayerV1, ...]:
    return (
        SessionPlayerV1(
            player_id="player-c",
            player_label="Carol",
            seat="rearhand",
        ),
        SessionPlayerV1(
            player_id="player-a",
            player_label="Alice",
            seat="forehand",
        ),
        SessionPlayerV1(
            player_id="player-b",
            player_label=None,
            seat="middlehand",
        ),
    )


def _apply(state: SessionStateV1, command) -> SessionStateV1:
    result = apply_session_command_v1(state, command)
    assert result.status == "applied", result.to_dict()
    return result.state


def _metadata(state: SessionStateV1, **values) -> SessionStateV1:
    return _apply(
        state,
        SetSessionGameMetadataCommandV1(
            expected_revision=state.revision,
            **values,
        ),
    )


def _deal_card(
    state: SessionStateV1,
    *,
    destination: str,
    card: str,
    player_id: str | None = None,
) -> SessionStateV1:
    return _apply(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=state.revision,
            destination=destination,
            player_id=player_id,
            card=card,
        ),
    )


def _declaration_from_data(data: dict) -> GameDeclaration:
    declaration = data["declaration"]
    return GameDeclaration(
        game_type=declaration["game_type"],
        hand_game=declaration.get("hand_game", False),
        ouvert=declaration.get("ouvert", False),
        schneider_announced=declaration.get("schneider_announced", False),
        schwarz_announced=declaration.get("schwarz_announced", False),
        matadors=declaration.get("matadors"),
        bid_value=declaration.get("bid_value"),
    )


def _retrospective_before_play(data: dict) -> SessionStateV1:
    players = tuple(
        SessionPlayerV1(
            player_id=player["player_id"],
            player_label=player.get("player_label"),
            seat=player["seat"],
        )
        for player in reversed(data["players"])
    )
    state = create_session_state_v1(
        session_id=f"session-{data['game_id']}",
        players=players,
        capture_mode="retrospective",
    )
    state = _metadata(
        state,
        game_id=data["game_id"],
        **({"played_at": data["played_at"]} if "played_at" in data else {}),
    )
    for player in data["players"]:
        for card in reversed(player["initial_hand"]):
            state = _deal_card(
                state,
                destination="player_hand",
                player_id=player["player_id"],
                card=card,
            )
    for card in reversed(data["skat"]):
        state = _deal_card(state, destination="skat", card=card)
    assert state.phase == "declaration"
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id=data["declarer_player_id"],
        ),
    )
    state = _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=_declaration_from_data(data),
        ),
    )
    for card in data["discarded_cards"]:
        state = _apply(
            state,
            RecordSessionDiscardCommandV1(
                expected_revision=state.revision,
                card=card,
            ),
        )
    assert state.phase == "play"
    return state


def _play_commands_from_data(
    state: SessionStateV1,
    data: dict,
) -> SessionStateV1:
    event = data.get("game_events", [None])[0]
    play_count = 0
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
    for trick in data["tricks"]:
        for play in trick["plays"]:
            state = _apply(
                state,
                RecordSessionPlayCommandV1(
                    expected_revision=state.revision,
                    player_id=play["player_id"],
                    card=play["card"],
                ),
            )
            play_count += 1
            if event is not None and not event_recorded and event["after_play_count"] == play_count:
                state = _apply(
                    state,
                    SetSessionGameEventCommandV1(
                        expected_revision=state.revision,
                        event=event,
                    ),
                )
                event_recorded = True
    assert event is None or event_recorded
    return state


def _complete_retrospective_session(data: dict) -> SessionStateV1:
    state = _play_commands_from_data(_retrospective_before_play(data), data)
    return _apply(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason=data["game_end_reason"],
            game_end=data.get("game_end"),
        ),
    )


def _live_declaration_state(
    *,
    local_player_id: str = "player-a",
) -> SessionStateV1:
    state = create_session_state_v1(
        session_id="session-live",
        players=_players(),
        capture_mode="live",
        local_player_id=local_player_id,
    )
    for card in get_full_deck()[:10]:
        state = _deal_card(
            state,
            destination="player_hand",
            player_id=local_player_id,
            card=card,
        )
    assert state.phase == "declaration"
    return state


def test_versions_initial_state_and_empty_projection_are_canonical() -> None:
    state = create_session_state_v1(
        session_id="session-151",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    projection = replay_session_state_v1(state)

    assert SESSION_TRANSITION_ENGINE_VERSION == 1
    assert SESSION_PROJECTION_VERSION == 1
    assert SESSION_REPLAY_POLICY == "full_accepted_log_before_apply"
    assert state.revision == 0
    assert state.phase == "setup"
    assert state.initial_capture_mode == state.capture_mode == "live"
    assert state.command_log == ()
    assert tuple(player.player_id for player in state.players) == (
        "player-a",
        "player-b",
        "player-c",
    )
    assert state.validation.position_export.status == "unavailable"
    assert state.validation.historical_export.status == "unavailable"
    assert projection.initial_known_hands == ()
    assert projection.remaining_known_hands == ()
    assert projection.to_dict() == replay_session_state_v1(state).to_dict()
    json.dumps(projection.to_dict())
    with pytest.raises(FrozenInstanceError):
        projection.phase = "deal"


def test_revision_conflict_precedes_semantic_validation_and_is_atomic() -> None:
    state = create_session_state_v1(
        session_id="session-conflict",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    command = RecordSessionDealtCardCommandV1(
        expected_revision=3,
        destination="player_hand",
        player_id="player-b",
        card="CA",
    )

    result = apply_session_command_v1(state, command)

    assert result.status == "revision_conflict"
    assert result.state is state
    assert result.current_revision == result.previous_revision == 0
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "revision_conflict"
    assert result.diagnostics[0].path == "/command/expected_revision"
    assert result.state.validation == state.validation

    advanced = _metadata(state, game_id="game-conflict")
    stale = apply_session_command_v1(
        advanced,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        ),
    )
    assert stale.status == "revision_conflict"
    assert stale.state is advanced


def test_semantic_rejection_returns_the_exact_unchanged_state() -> None:
    state = create_session_state_v1(
        session_id="session-rejection",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    command = RecordSessionDealtCardCommandV1(
        expected_revision=0,
        destination="player_hand",
        player_id="player-b",
        card="CA",
    )

    result = apply_session_command_v1(state, command)

    assert result.status == "rejected"
    assert result.state is state
    assert result.state.command_log == ()
    assert result.state.revision == 0
    assert result.diagnostics[0].code == "information_policy_violation"
    assert all(diagnostic not in state.validation.diagnostics for diagnostic in result.diagnostics)


def test_metadata_fields_are_independently_single_assignment() -> None:
    state = create_session_state_v1(
        session_id="session-metadata",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    state = _metadata(state, game_id="game-151")
    state = _metadata(state, played_at="2026-08-07T12:00:00Z")
    projection = replay_session_state_v1(state)
    assert projection.game_id == "game-151"
    assert projection.played_at == "2026-08-07T12:00:00Z"

    repeated = apply_session_command_v1(
        state,
        SetSessionGameMetadataCommandV1(
            expected_revision=state.revision,
            game_id="replacement",
            played_at="2026-08-08T12:00:00Z",
        ),
    )
    assert repeated.status == "rejected"
    assert repeated.state is state
    assert tuple(diagnostic.path for diagnostic in repeated.diagnostics) == (
        "/command/game_id",
        "/command/played_at",
    )
    assert replay_session_state_v1(state).game_id == "game-151"


def test_live_and_retrospective_deals_advance_only_when_mode_complete() -> None:
    live = create_session_state_v1(
        session_id="session-live-deal",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    live = _deal_card(
        live,
        destination="player_hand",
        player_id="player-a",
        card=get_full_deck()[9],
    )
    assert live.phase == "deal"
    for card in get_full_deck()[:9]:
        live = _deal_card(
            live,
            destination="player_hand",
            player_id="player-a",
            card=card,
        )
    assert live.phase == "declaration"
    assert replay_session_state_v1(live).initial_hand_for("player-a") == tuple(get_full_deck()[:10])

    retrospective = _retrospective_before_play(build_historical_input())
    projection = replay_session_state_v1(retrospective)
    assert all(len(cards) == 10 for _, cards in projection.initial_known_hands)
    assert len(projection.known_skat) == 2
    assert set(card for _, cards in projection.initial_known_hands for card in cards) | set(
        projection.known_skat
    ) == set(get_full_deck())


def test_deal_rejects_duplicate_card_hand_overflow_and_unauthorized_live_skat() -> None:
    state = create_session_state_v1(
        session_id="session-deal-errors",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    state = _deal_card(
        state,
        destination="player_hand",
        player_id="player-a",
        card="CA",
    )
    duplicate = apply_session_command_v1(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=state.revision,
            destination="player_hand",
            player_id="player-a",
            card="CA",
        ),
    )
    skat = apply_session_command_v1(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=state.revision,
            destination="skat",
            player_id=None,
            card="D7",
        ),
    )
    assert duplicate.status == "rejected"
    assert duplicate.diagnostics[0].code == "card_identity_violation"
    assert skat.status == "rejected"
    assert skat.diagnostics[0].code == "information_policy_violation"

    state = _live_declaration_state()
    overflow = apply_session_command_v1(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=state.revision,
            destination="player_hand",
            player_id="player-a",
            card="S7",
        ),
    )
    assert overflow.status == "rejected"
    assert overflow.diagnostics[0].code == "card_identity_violation"

    retrospective = create_session_state_v1(
        session_id="session-skat-overflow",
        players=_players(),
        capture_mode="retrospective",
    )
    retrospective = _deal_card(retrospective, destination="skat", card="D8")
    retrospective = _deal_card(retrospective, destination="skat", card="D7")
    skat_overflow = apply_session_command_v1(
        retrospective,
        RecordSessionDealtCardCommandV1(
            expected_revision=retrospective.revision,
            destination="skat",
            player_id=None,
            card="D9",
        ),
    )
    assert skat_overflow.status == "rejected"
    assert skat_overflow.diagnostics[0].code == "card_identity_violation"


@pytest.mark.parametrize("capture_mode", ("live", "retrospective"))
def test_deal_unknown_player_is_an_atomic_reference_rejection(
    capture_mode: str,
) -> None:
    state = create_session_state_v1(
        session_id=f"session-unknown-{capture_mode}",
        players=_players(),
        capture_mode=capture_mode,
        local_player_id="player-a" if capture_mode == "live" else None,
    )
    result = apply_session_command_v1(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=0,
            destination="player_hand",
            player_id="unknown-player",
            card="CA",
        ),
    )
    assert result.status == "rejected"
    assert result.state is state
    assert result.diagnostics[0].code == "player_reference_violation"


def test_declarer_and_declaration_support_either_order_and_branch_phases() -> None:
    declaration_first = _live_declaration_state()
    declaration_first = _apply(
        declaration_first,
        SetSessionDeclarationCommandV1(
            expected_revision=declaration_first.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    assert declaration_first.phase == "declaration"
    declaration_first = _apply(
        declaration_first,
        SetSessionDeclarerCommandV1(
            expected_revision=declaration_first.revision,
            declarer_player_id="player-b",
        ),
    )
    assert declaration_first.phase == "play"

    declarer_first = _live_declaration_state()
    declarer_first = _apply(
        declarer_first,
        SetSessionDeclarerCommandV1(
            expected_revision=declarer_first.revision,
            declarer_player_id="player-a",
        ),
    )
    declarer_first = _apply(
        declarer_first,
        SetSessionDeclarationCommandV1(
            expected_revision=declarer_first.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    assert declarer_first.phase == "skat_and_discard"

    hand = _live_declaration_state()
    hand = _apply(
        hand,
        SetSessionDeclarerCommandV1(
            expected_revision=hand.revision,
            declarer_player_id="player-a",
        ),
    )
    hand = _apply(
        hand,
        SetSessionDeclarationCommandV1(
            expected_revision=hand.revision,
            declaration=GameDeclaration(
                game_type="grand",
                hand_game=True,
                bid_value=24,
            ),
        ),
    )
    assert hand.phase == "play"


def test_matadors_are_information_safe_live_and_exact_retrospective() -> None:
    live_defender = _live_declaration_state()
    live_defender = _apply(
        live_defender,
        SetSessionDeclarerCommandV1(
            expected_revision=live_defender.revision,
            declarer_player_id="player-b",
        ),
    )
    rejected = apply_session_command_v1(
        live_defender,
        SetSessionDeclarationCommandV1(
            expected_revision=live_defender.revision,
            declaration=GameDeclaration(
                game_type="grand",
                matadors=2,
                bid_value=24,
            ),
        ),
    )
    assert rejected.status == "rejected"
    assert rejected.diagnostics[0].code == "information_policy_violation"

    data = build_historical_input()
    state = _retrospective_before_play(data)
    projection = replay_session_state_v1(state)
    declarer_id = data["declarer_player_id"]
    inferred = infer_matadors_from_known_ownership(
        game_type="grand",
        declarer_owned_cards=[
            *(projection.initial_hand_for(declarer_id) or ()),
            *projection.known_skat,
        ],
        non_declarer_owned_cards=[
            card
            for player_id, cards in projection.initial_known_hands
            if player_id != declarer_id
            for card in cards
        ],
    )
    assert inferred is not None

    before_declaration = create_session_state_v1(
        session_id="session-exact-matadors",
        players=_players(),
        capture_mode="retrospective",
    )
    for player in data["players"]:
        for card in player["initial_hand"]:
            before_declaration = _deal_card(
                before_declaration,
                destination="player_hand",
                player_id=player["player_id"],
                card=card,
            )
    for card in data["skat"]:
        before_declaration = _deal_card(
            before_declaration,
            destination="skat",
            card=card,
        )
    exact_deal = before_declaration
    before_declaration = _apply(
        before_declaration,
        SetSessionDeclarerCommandV1(
            expected_revision=before_declaration.revision,
            declarer_player_id=declarer_id,
        ),
    )
    wrong = 1 if inferred != 1 else 2
    wrong_result = apply_session_command_v1(
        before_declaration,
        SetSessionDeclarationCommandV1(
            expected_revision=before_declaration.revision,
            declaration=GameDeclaration(
                game_type="grand",
                matadors=wrong,
                bid_value=24,
            ),
        ),
    )
    assert wrong_result.status == "rejected"
    assert wrong_result.diagnostics[0].code == "declaration_violation"

    declaration_first = _apply(
        exact_deal,
        SetSessionDeclarationCommandV1(
            expected_revision=exact_deal.revision,
            declaration=GameDeclaration(
                game_type="grand",
                matadors=inferred,
                bid_value=24,
            ),
        ),
    )
    declaration_first = _apply(
        declaration_first,
        SetSessionDeclarerCommandV1(
            expected_revision=declaration_first.revision,
            declarer_player_id=declarer_id,
        ),
    )
    assert declaration_first.phase == "skat_and_discard"


def test_live_local_declarer_skat_and_discards_derive_playable_hand() -> None:
    state = _live_declaration_state()
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id="player-a",
        ),
    )
    state = _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    state = _deal_card(state, destination="skat", card="D8")
    incomplete = apply_session_command_v1(
        state,
        RecordSessionDiscardCommandV1(
            expected_revision=state.revision,
            card="CA",
        ),
    )
    assert incomplete.status == "rejected"
    assert incomplete.diagnostics[0].code == "missing_required_value"
    state = _deal_card(state, destination="skat", card="D7")
    state_after_first_discard = _apply(
        state,
        RecordSessionDiscardCommandV1(
            expected_revision=state.revision,
            card="CA",
        ),
    )
    duplicate = apply_session_command_v1(
        state_after_first_discard,
        RecordSessionDiscardCommandV1(
            expected_revision=state_after_first_discard.revision,
            card="CA",
        ),
    )
    assert duplicate.status == "rejected"
    assert duplicate.diagnostics[0].code == "card_identity_violation"
    state = state_after_first_discard
    state = _apply(
        state,
        RecordSessionDiscardCommandV1(
            expected_revision=state.revision,
            card="D8",
        ),
    )
    projection = replay_session_state_v1(state)
    assert state.phase == "play"
    assert projection.known_skat == ("D8", "D7")
    assert projection.discarded_cards == ("CA", "D8")
    assert len(projection.remaining_hand_for("player-a") or ()) == 10
    assert "D7" in (projection.remaining_hand_for("player-a") or ())


def test_hand_game_live_defender_and_duplicate_discards_are_rejected() -> None:
    hand = _live_declaration_state()
    hand = _apply(
        hand,
        SetSessionDeclarerCommandV1(
            expected_revision=hand.revision,
            declarer_player_id="player-a",
        ),
    )
    hand = _apply(
        hand,
        SetSessionDeclarationCommandV1(
            expected_revision=hand.revision,
            declaration=GameDeclaration(
                game_type="grand",
                hand_game=True,
                bid_value=24,
            ),
        ),
    )
    wrong_phase = apply_session_command_v1(
        hand,
        RecordSessionDiscardCommandV1(
            expected_revision=hand.revision,
            card="CA",
        ),
    )
    assert wrong_phase.status == "rejected"
    assert wrong_phase.diagnostics[0].code == "phase_violation"

    defender = _live_declaration_state()
    defender = _apply(
        defender,
        SetSessionDeclarerCommandV1(
            expected_revision=defender.revision,
            declarer_player_id="player-b",
        ),
    )
    defender = _apply(
        defender,
        SetSessionDeclarationCommandV1(
            expected_revision=defender.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    assert defender.phase == "play"
    defender_discard = apply_session_command_v1(
        defender,
        RecordSessionDiscardCommandV1(
            expected_revision=defender.revision,
            card="CA",
        ),
    )
    assert defender_discard.status == "rejected"


def test_turn_order_ownership_follow_rule_and_trick_derivation_reuse_rules() -> None:
    deck = get_full_deck()
    deck[5], deck[12] = deck[12], deck[5]
    data = build_historical_input(deck=deck)
    state = _retrospective_before_play(data)
    first_trick = data["tricks"][0]
    wrong_actor = apply_session_command_v1(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-b",
            card=first_trick["plays"][1]["card"],
        ),
    )
    assert wrong_actor.status == "rejected"
    assert wrong_actor.diagnostics[0].code == "turn_order_violation"

    wrong_owner = apply_session_command_v1(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card=data["players"][1]["initial_hand"][2],
        ),
    )
    assert wrong_owner.status == "rejected"
    assert wrong_owner.diagnostics[0].code == "card_ownership_violation"

    first_play = first_trick["plays"][0]
    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id=first_play["player_id"],
            card=first_play["card"],
        ),
    )
    projection = replay_session_state_v1(state)
    actor = projection.next_player_id
    hand = list(projection.remaining_hand_for(actor or "") or ())
    current = [card for _, card in projection.incomplete_trick.plays]
    legal = get_legal_cards(hand, current, projection.declaration.game_type)
    illegal = next((card for card in hand if card not in legal), None)
    assert illegal is not None
    follow = apply_session_command_v1(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id=actor or "",
            card=illegal,
        ),
    )
    assert follow.status == "rejected"
    assert follow.diagnostics[0].code == "card_ownership_violation"

    for play in first_trick["plays"][1:]:
        state = _apply(
            state,
            RecordSessionPlayCommandV1(
                expected_revision=state.revision,
                player_id=play["player_id"],
                card=play["card"],
            ),
        )
    projection = replay_session_state_v1(state)
    cards = [play["card"] for play in first_trick["plays"]]
    winner_index = get_trick_winner(cards, "grand")
    assert projection.incomplete_trick is None
    assert len(projection.completed_tricks) == 1
    assert (
        projection.completed_tricks[0].winner_player_id
        == first_trick["plays"][winner_index]["player_id"]
    )
    assert projection.completed_tricks[0].trick_points == get_trick_points(cards)
    assert projection.next_player_id == projection.completed_tricks[0].winner_player_id


def test_live_unknown_opponents_use_only_bounded_public_ownership() -> None:
    state = _live_declaration_state(local_player_id="player-c")
    state = _apply(
        state,
        SetSessionDeclarerCommandV1(
            expected_revision=state.revision,
            declarer_player_id="player-b",
        ),
    )
    state = _apply(
        state,
        SetSessionDeclarationCommandV1(
            expected_revision=state.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    local_cards = set(replay_session_state_v1(state).remaining_hand_for("player-c") or ())
    local_conflict = apply_session_command_v1(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card=next(card for card in get_full_deck() if card in local_cards),
        ),
    )
    assert local_conflict.status == "rejected"
    assert local_conflict.diagnostics[0].code == "card_ownership_violation"
    unknown_cards = [card for card in get_full_deck() if card not in local_cards]
    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-a",
            card=unknown_cards[0],
        ),
    )
    state = _apply(
        state,
        RecordSessionPlayCommandV1(
            expected_revision=state.revision,
            player_id="player-b",
            card=unknown_cards[-1],
        ),
    )
    assert state.phase == "play"
    assert state.validation.position_export.status == "available"

    conflict = apply_session_command_v1(
        _live_declaration_state(local_player_id="player-c"),
        PromoteSessionToRetrospectiveCommandV1(expected_revision=10),
    )
    assert conflict.status == "applied"
    assert conflict.state.phase == "declaration"


@pytest.mark.parametrize(
    "builder",
    (
        build_defender_open_play_continuation,
        build_declarer_exposure_continuation,
    ),
)
def test_both_continuation_events_are_validated_and_public_hands_shrink(builder) -> None:
    data = builder()
    state = _play_commands_from_data(_retrospective_before_play(data), data)
    projection = replay_session_state_v1(state)
    event = data["game_events"][0]
    owner_id = event.get(
        "exposing_defender_player_id",
        data["declarer_player_id"],
    )
    public_hand = projection.public_hand_for(owner_id)
    plays_after_event = [play for trick in data["tricks"] for play in trick["plays"]][
        event["after_play_count"] :
    ]
    originally_public = event.get("exposed_cards", event.get("public_declarer_cards"))
    assert projection.continuation_event is not None
    assert set(public_hand or ()) == set(originally_public) - {
        play["card"] for play in plays_after_event if play["player_id"] == owner_id
    }

    repeated = apply_session_command_v1(
        state,
        SetSessionGameEventCommandV1(
            expected_revision=state.revision,
            event=event,
        ),
    )
    assert repeated.status == "rejected"
    assert repeated.diagnostics[0].code == "event_sequence_violation"


def test_continuation_requires_the_current_boundary_and_exact_known_hand() -> None:
    data = build_defender_open_play_continuation()
    state = _retrospective_before_play(data)
    future_boundary = apply_session_command_v1(
        state,
        SetSessionGameEventCommandV1(
            expected_revision=state.revision,
            event=data["game_events"][0],
        ),
    )
    assert future_boundary.status == "rejected"
    assert future_boundary.diagnostics[0].code == "event_sequence_violation"

    event = copy.deepcopy(data["game_events"][0])
    event["after_play_count"] = 0
    event["exposed_cards"] = event["exposed_cards"][:-1]
    result = apply_session_command_v1(
        state,
        SetSessionGameEventCommandV1(
            expected_revision=state.revision,
            event=event,
        ),
    )
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "card_ownership_violation"

    stale_state = _retrospective_before_play(data)
    chronological_plays = [play for trick in data["tricks"] for play in trick["plays"]]
    for play in chronological_plays[:13]:
        stale_state = _apply(
            stale_state,
            RecordSessionPlayCommandV1(
                expected_revision=stale_state.revision,
                player_id=play["player_id"],
                card=play["card"],
            ),
        )
    stale_boundary = apply_session_command_v1(
        stale_state,
        SetSessionGameEventCommandV1(
            expected_revision=stale_state.revision,
            event=data["game_events"][0],
        ),
    )
    assert stale_boundary.status == "rejected"
    assert stale_boundary.diagnostics[0].code == "event_sequence_violation"


@pytest.mark.parametrize(
    "continuation_kind",
    (
        "defender_open_play_continuation",
        "declarer_card_exposure_continuation",
    ),
)
def test_each_continuation_can_precede_a_supported_terminal_end(
    continuation_kind: str,
) -> None:
    data = build_concession_prefix(
        completed_trick_count=4,
        current_trick_card_count=2,
    )
    data = add_continuation(data, continuation_kind, after_play_count=12)
    state = _complete_retrospective_session(data)
    projection = replay_session_state_v1(state)
    assert projection.continuation_event is not None
    assert projection.game_end_reason == "declarer_concession"
    assert state.validation.historical_export.status == "available"


@pytest.mark.parametrize(
    "data",
    (
        build_historical_input(),
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2),
        build_defender_concession_prefix(
            completed_trick_count=4,
            current_trick_card_count=2,
        ),
        build_exposure_prefix(completed_trick_count=4, current_trick_card_count=2),
        build_open_play_prefix(completed_trick_count=8),
        build_throw_prefix(completed_trick_count=8),
    ),
    ids=(
        "normal_completion",
        "declarer_concession",
        "defender_concession",
        "declarer_card_exposure",
        "defender_open_play",
        "open_card_throw",
    ),
)
def test_all_supported_game_end_shapes_advance_only_after_explicit_end(data: dict) -> None:
    state = _play_commands_from_data(_retrospective_before_play(data), data)
    assert state.phase == "play"
    state = _apply(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason=data["game_end_reason"],
            game_end=data.get("game_end"),
        ),
    )
    projection = replay_session_state_v1(state)
    assert state.phase == "ended"
    assert projection.game_end_reason == data["game_end_reason"]
    assert state.validation.historical_export.status == "available"
    assert state.validation.position_export.status == "unavailable"


def test_normal_and_terminal_game_end_chronology_is_rejected_atomically() -> None:
    normal = build_historical_input()
    state = _retrospective_before_play(normal)
    early_normal = apply_session_command_v1(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason="normal_completion",
            game_end=None,
        ),
    )
    assert early_normal.status == "rejected"
    assert early_normal.state is state

    concession = build_concession_prefix(completed_trick_count=4)
    state = _play_commands_from_data(_retrospective_before_play(concession), concession)
    details = copy.deepcopy(concession["game_end"])
    details["declarer_hand_cards_remaining"] -= 1
    wrong_count = apply_session_command_v1(
        state,
        SetSessionGameEndCommandV1(
            expected_revision=state.revision,
            game_end_reason="declarer_concession",
            game_end=details,
        ),
    )
    assert wrong_count.status == "rejected"
    assert wrong_count.diagnostics[0].code == "game_end_violation"

    completed = _play_commands_from_data(
        _retrospective_before_play(normal),
        normal,
    )
    terminal_after_30 = apply_session_command_v1(
        completed,
        SetSessionGameEndCommandV1(
            expected_revision=completed.revision,
            game_end_reason="declarer_concession",
            game_end=build_concession_prefix()["game_end"],
        ),
    )
    assert terminal_after_30.status == "rejected"
    assert terminal_after_30.diagnostics[0].code == "game_end_violation"

    early_open_play = build_open_play_prefix(
        completed_trick_count=4,
        current_trick_card_count=1,
    )
    early_open_state = _play_commands_from_data(
        _retrospective_before_play(early_open_play),
        early_open_play,
    )
    unsupported_open_play = apply_session_command_v1(
        early_open_state,
        SetSessionGameEndCommandV1(
            expected_revision=early_open_state.revision,
            game_end_reason="defender_open_play",
            game_end=early_open_play["game_end"],
        ),
    )
    assert unsupported_open_play.status == "rejected"
    assert unsupported_open_play.diagnostics[0].code == "game_end_violation"


@pytest.mark.parametrize(
    ("game_type", "hand_game"),
    (("clubs", True), ("null", False)),
)
def test_suit_and_null_normal_play_use_the_same_incremental_rules(
    game_type: str,
    hand_game: bool,
) -> None:
    state = _complete_retrospective_session(
        build_historical_input(game_type=game_type, hand_game=hand_game)
    )
    projection = replay_session_state_v1(state)
    assert projection.declaration.game_type == game_type
    assert len(projection.completed_tricks) == 10
    assert projection.played_card_count == 30
    assert state.validation.historical_export.status == "available"


def test_promotion_is_one_way_preserves_phase_and_does_not_infer_facts() -> None:
    state = create_session_state_v1(
        session_id="session-promotion",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    state = _deal_card(
        state,
        destination="player_hand",
        player_id="player-a",
        card="CA",
    )
    before = replay_session_state_v1(state)
    state = _apply(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=state.revision),
    )
    after = replay_session_state_v1(state)
    assert state.capture_mode == "retrospective"
    assert state.phase == "deal"
    assert after.initial_known_hands == before.initial_known_hands
    assert after.known_skat == ()
    assert after.declarer_player_id is None

    repeated = apply_session_command_v1(
        state,
        PromoteSessionToRetrospectiveCommandV1(expected_revision=state.revision),
    )
    assert repeated.status == "rejected"


def test_position_and_historical_readiness_are_recomputed_from_current_facts() -> None:
    live = _live_declaration_state()
    live = _apply(
        live,
        SetSessionDeclarerCommandV1(
            expected_revision=live.revision,
            declarer_player_id="player-b",
        ),
    )
    live = _apply(
        live,
        SetSessionDeclarationCommandV1(
            expected_revision=live.revision,
            declaration=GameDeclaration(game_type="grand", bid_value=24),
        ),
    )
    assert live.validation.position_export.status == "available"
    assert live.validation.historical_export.status == "unavailable"
    assert not any(diagnostic.blocks_command for diagnostic in live.validation.diagnostics)

    first = build_historical_input()["tricks"][0]["plays"][0]
    live = _apply(
        live,
        RecordSessionPlayCommandV1(
            expected_revision=live.revision,
            player_id=first["player_id"],
            card=first["card"],
        ),
    )
    assert live.validation.position_export.status == "unavailable"

    historical = _complete_retrospective_session(build_historical_input())
    assert historical.validation.historical_export.status == "available"
    assert historical.validation.game_complete is True
    assert historical.validation.valid_incomplete is False


def test_historical_readiness_requires_game_id_even_for_exact_ended_state() -> None:
    data = build_historical_input()
    state = _retrospective_before_play(data)
    metadata_record = state.command_log[0]
    assert metadata_record.command.kind == "set_game_metadata"
    data_without_metadata = copy.deepcopy(data)
    state_without_metadata = create_session_state_v1(
        session_id="session-without-game-id",
        players=_players(),
        capture_mode="retrospective",
    )
    for record in state.command_log[1:]:
        command = replace(record.command, expected_revision=state_without_metadata.revision)
        state_without_metadata = _apply(state_without_metadata, command)
    state_without_metadata = _play_commands_from_data(
        state_without_metadata,
        data_without_metadata,
    )
    state_without_metadata = _apply(
        state_without_metadata,
        SetSessionGameEndCommandV1(
            expected_revision=state_without_metadata.revision,
            game_end_reason="normal_completion",
            game_end=None,
        ),
    )
    assert state_without_metadata.validation.historical_export.status == "unavailable"
    assert any(
        diagnostic.path == "/game_id"
        for diagnostic in state_without_metadata.validation.diagnostics
    )


def test_replay_rejects_forged_phase_mode_validation_and_duplicate_card_log() -> None:
    state = create_session_state_v1(
        session_id="session-forged",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    forged_revision = copy.copy(state)
    object.__setattr__(forged_revision, "revision", 1)
    with pytest.raises(SkatAIInvariantError, match="revision"):
        replay_session_state_v1(forged_revision)

    forged_phase_validation = replace(state.validation, phase="deal")
    forged_phase = replace(
        state,
        phase="deal",
        validation=forged_phase_validation,
    )
    with pytest.raises(SkatAIInvariantError, match="phase"):
        replay_session_state_v1(forged_phase)

    forged_mode = copy.copy(state)
    object.__setattr__(forged_mode, "capture_mode", "retrospective")
    with pytest.raises(SkatAIInvariantError, match="Mode"):
        replay_session_state_v1(forged_mode)

    forged_validation = copy.copy(state)
    invalid_validation = copy.copy(state.validation)
    object.__setattr__(invalid_validation, "diagnostics", ())
    object.__setattr__(
        forged_validation,
        "validation",
        invalid_validation,
    )
    with pytest.raises(SkatAIInvariantError, match="Validation"):
        replay_session_state_v1(forged_validation)

    first = RecordSessionDealtCardCommandV1(
        expected_revision=0,
        destination="player_hand",
        player_id="player-a",
        card="CA",
    )
    second = RecordSessionDealtCardCommandV1(
        expected_revision=1,
        destination="player_hand",
        player_id="player-a",
        card="CA",
    )
    valid_first = apply_session_command_v1(state, first).state
    forged_log = SessionStateV1(
        session_id=state.session_id,
        initial_capture_mode="live",
        capture_mode="live",
        revision=2,
        phase="deal",
        players=state.players,
        local_player_id="player-a",
        command_log=(
            SessionCommandRecordV1(revision=1, command=first),
            SessionCommandRecordV1(revision=2, command=second),
        ),
        validation=replace(valid_first.validation, revision=2),
    )
    with pytest.raises(SkatAIInvariantError, match="semantically invalid"):
        replay_session_state_v1(forged_log)


def test_replay_rejects_an_accepted_illegal_play_and_invalid_end_sequence() -> None:
    data = build_historical_input()
    state = _retrospective_before_play(data)
    wrong_card = data["players"][1]["initial_hand"][2]
    illegal = RecordSessionPlayCommandV1(
        expected_revision=state.revision,
        player_id="player-a",
        card=wrong_card,
    )
    forged = SessionStateV1(
        session_id=state.session_id,
        initial_capture_mode=state.initial_capture_mode,
        capture_mode=state.capture_mode,
        revision=state.revision + 1,
        phase="play",
        players=state.players,
        local_player_id=state.local_player_id,
        command_log=(
            *state.command_log,
            SessionCommandRecordV1(revision=state.revision + 1, command=illegal),
        ),
        validation=replace(state.validation, revision=state.revision + 1),
    )
    with pytest.raises(SkatAIInvariantError, match="semantically invalid"):
        replay_session_state_v1(forged)

    early_end = SetSessionGameEndCommandV1(
        expected_revision=state.revision,
        game_end_reason="normal_completion",
        game_end=None,
    )
    forged_end = replace(
        forged,
        command_log=(
            *state.command_log,
            SessionCommandRecordV1(
                revision=state.revision + 1,
                command=early_end,
            ),
        ),
    )
    with pytest.raises(SkatAIInvariantError, match="semantically invalid"):
        replay_session_state_v1(forged_end)


def test_equal_identity_and_logs_produce_equal_projection_validation_and_serialization() -> None:
    first = _complete_retrospective_session(build_historical_input())
    second = _complete_retrospective_session(build_historical_input())
    assert first == second
    assert first.validation == second.validation
    assert replay_session_state_v1(first) == replay_session_state_v1(second)
    assert replay_session_state_v1(first).to_dict() == replay_session_state_v1(second).to_dict()
    assert first.to_dict() == second.to_dict()


def test_one_application_uses_one_prior_replay_and_one_candidate_application(
    monkeypatch,
) -> None:
    state = create_session_state_v1(
        session_id="session-counts",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    replay_count = 0
    candidate_count = 0
    original_replay = transitions.replay_session_state_v1
    original_candidate = transitions.apply_session_command_to_projection_v1

    def counted_replay(value):
        nonlocal replay_count
        replay_count += 1
        return original_replay(value)

    def counted_candidate(projection, command):
        nonlocal candidate_count
        candidate_count += 1
        return original_candidate(projection, command)

    monkeypatch.setattr(transitions, "replay_session_state_v1", counted_replay)
    monkeypatch.setattr(
        transitions,
        "apply_session_command_to_projection_v1",
        counted_candidate,
    )
    result = transitions.apply_session_command_v1(
        state,
        SetSessionGameMetadataCommandV1(
            expected_revision=0,
            game_id="game-counts",
        ),
    )
    assert result.status == "applied"
    assert replay_count == 1
    assert candidate_count == 1


def test_revision_conflict_does_not_apply_a_candidate_validator(monkeypatch) -> None:
    state = create_session_state_v1(
        session_id="session-conflict-count",
        players=_players(),
        capture_mode="live",
        local_player_id="player-a",
    )
    candidate_count = 0
    original_candidate = transitions.apply_session_command_to_projection_v1

    def counted_candidate(projection, command):
        nonlocal candidate_count
        candidate_count += 1
        return original_candidate(projection, command)

    monkeypatch.setattr(
        transitions,
        "apply_session_command_to_projection_v1",
        counted_candidate,
    )
    result = transitions.apply_session_command_v1(
        state,
        RecordSessionDealtCardCommandV1(
            expected_revision=1,
            destination="player_hand",
            player_id="unknown-player",
            card="CA",
        ),
    )
    assert result.status == "revision_conflict"
    assert candidate_count == 0


def test_validation_type_and_public_boundaries_remain_internal() -> None:
    state = create_session_state_v1(
        session_id="session-boundary",
        players=_players(),
        capture_mode="retrospective",
    )
    assert isinstance(state.validation, SessionValidationResultV1)

    import skat_ai
    import skat_ai.api.v1 as api_v1

    assert skat_ai.__all__ == ("api", "errors", "__version__")
    assert all("Session" not in name for name in api_v1.__all__)
