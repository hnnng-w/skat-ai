from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skatmind.api.v1.contracts import RequestDocumentV1, WorkflowV1
from skatmind.errors import SkatMindInvariantError
from skatmind.game_continuation import build_game_continuation
from skatmind.game_declaration import (
    GameDeclaration,
    build_serializable_game_declaration,
)
from skatmind.historical_declarer_card_exposure_continuation import (
    HistoricalDeclarerCardExposureContinuationEvent,
)
from skatmind.historical_defender_open_play_continuation import (
    HistoricalDefenderOpenPlayContinuationEvent,
)
from skatmind.input_loader import build_position_from_document
from skatmind.matador_inference import infer_visible_matadors_for_decision
from skatmind.recommendation_workflow import (
    build_recommendation_method_configuration,
    build_serializable_bounded_search_settings,
)
from skatmind.session_contracts import SessionStateV1
from skatmind.session_export_contracts import SessionRequestExportV1
from skatmind.session_projection import SessionProjectionV1
from skatmind.session_transitions import replay_session_state_v1
from skatmind.turn_phase import normalize_turn_phase_for_position

SESSION_POSITION_EXPORT_OPTIONS_VERSION = 1
SESSION_POSITION_EXPORT_POLICY = "information_safe_ready_local_decision"

_POSITION_TARGET = "position_analysis"


def _freeze_json_value(value: object, field_name: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} JSON numbers must be finite.")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError(f"{field_name} JSON object keys must be strings.")
        return MappingProxyType(
            {
                key: _freeze_json_value(value[key], f"{field_name}.{key}")
                for key in sorted(value)
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json_value(item, f"{field_name}[{index}]")
            for index, item in enumerate(value)
        )
    raise ValueError(f"{field_name} must contain only JSON-compatible values.")


def _thaw_json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionPositionExportOptionsV1:
    """Immutable analysis settings attached to one Session Position export."""

    session_position_export_options_version: int = (
        SESSION_POSITION_EXPORT_OPTIONS_VERSION
    )
    sample_count: int
    random_seed: int
    use_basic_opponent_strategy: bool
    recommendation_method: str | None
    bounded_search_settings: Mapping[str, object] | None

    def __post_init__(self) -> None:
        if (
            type(self.session_position_export_options_version) is not int
            or self.session_position_export_options_version
            != SESSION_POSITION_EXPORT_OPTIONS_VERSION
        ):
            raise ValueError(
                "session_position_export_options_version must equal "
                f"{SESSION_POSITION_EXPORT_OPTIONS_VERSION}."
            )
        if (
            isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or not 1 <= self.sample_count <= 100_000
        ):
            raise ValueError("sample_count must be an integer from 1 through 100000.")
        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed, int
        ):
            raise ValueError("random_seed must be an integer.")
        if not isinstance(self.use_basic_opponent_strategy, bool):
            raise ValueError("use_basic_opponent_strategy must be a boolean.")
        if self.recommendation_method is not None and not isinstance(
            self.recommendation_method, str
        ):
            raise ValueError(
                "recommendation_method must be null or a recommendation method string."
            )

        configuration_data: dict[str, Any] = {}
        if self.recommendation_method is not None:
            configuration_data["recommendation_method"] = self.recommendation_method
        if self.bounded_search_settings is not None:
            if not isinstance(self.bounded_search_settings, Mapping):
                raise ValueError("bounded_search_settings must be an object or null.")
            configuration_data["bounded_search_settings"] = _thaw_json_value(
                _freeze_json_value(
                    self.bounded_search_settings,
                    "bounded_search_settings",
                )
            )
        configuration = build_recommendation_method_configuration(
            configuration_data
        )
        normalized_settings = build_serializable_bounded_search_settings(
            configuration
        )
        object.__setattr__(
            self,
            "bounded_search_settings",
            (
                None
                if normalized_settings is None
                else _freeze_json_value(
                    normalized_settings,
                    "bounded_search_settings",
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_position_export_options_version": (
                self.session_position_export_options_version
            ),
            "sample_count": self.sample_count,
            "random_seed": self.random_seed,
            "use_basic_opponent_strategy": self.use_basic_opponent_strategy,
            "recommendation_method": self.recommendation_method,
            "bounded_search_settings": (
                None
                if self.bounded_search_settings is None
                else _thaw_json_value(self.bounded_search_settings)
            ),
        }


def _raise_export_invariant(
    message: str,
    *,
    path: str,
    cause: Exception | None = None,
) -> None:
    error = SkatMindInvariantError(message, path=path)
    if cause is None:
        raise error
    raise error from cause


def _build_relative_player_map(projection: SessionProjectionV1) -> dict[str, str]:
    local_player_id = projection.local_player_id
    if local_player_id is None or local_player_id not in projection.player_ids:
        raise ValueError("A Position-ready Session has no local Player.")
    local_index = projection.player_ids.index(local_player_id)
    return {
        "me": local_player_id,
        "left": projection.player_ids[(local_index + 1) % 3],
        "right": projection.player_ids[(local_index - 1) % 3],
    }


def _build_stable_to_relative(relative_player_map: Mapping[str, str]) -> dict[str, str]:
    return {
        stable_player_id: relative_player
        for relative_player, stable_player_id in relative_player_map.items()
    }


def _expected_hand_size(projection: SessionProjectionV1, player_id: str) -> int:
    return 10 - sum(candidate_id == player_id for candidate_id, _ in projection.plays)


def _validate_exact_hand_sizes(projection: SessionProjectionV1) -> None:
    for player_id, cards in (
        *projection.remaining_known_hands,
        *projection.exact_public_hands,
    ):
        if len(cards) != _expected_hand_size(projection, player_id):
            raise ValueError(
                f"Exact current hand for '{player_id}' conflicts with accepted Plays."
            )
    for player_id in projection.player_ids:
        known_hand = projection.remaining_hand_for(player_id)
        public_hand = projection.public_hand_for(player_id)
        if (
            known_hand is not None
            and public_hand is not None
            and set(known_hand) != set(public_hand)
        ):
            raise ValueError(
                f"Known and public current hands for '{player_id}' disagree."
            )


def _build_completed_tricks(
    projection: SessionProjectionV1,
    stable_to_relative: Mapping[str, str],
) -> list[dict[str, Any]]:
    return [
        {
            "cards": [card for _, card in trick.plays],
            "players": [
                stable_to_relative[player_id] for player_id, _ in trick.plays
            ],
            "winner_player": stable_to_relative[trick.winner_player_id],
            "winner_role": trick.winner_side,
        }
        for trick in projection.completed_tricks
    ]


def _build_current_trick(
    projection: SessionProjectionV1,
) -> tuple[list[str], str]:
    if projection.incomplete_trick is None:
        if projection.next_player_id is None:
            raise ValueError("A Position-ready Session has no next Player.")
        return [], projection.next_player_id
    return (
        [card for _, card in projection.incomplete_trick.plays],
        projection.incomplete_trick.leader_player_id,
    )


def _build_authorized_public_hands(
    projection: SessionProjectionV1,
    *,
    local_hand: tuple[str, ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    hands = {player_id: cards for player_id, cards in projection.exact_public_hands}
    declaration = projection.declaration
    declarer_player_id = projection.declarer_player_id
    if declaration is not None and declaration.ouvert and declarer_player_id is not None:
        declarer_cards = (
            local_hand
            if declarer_player_id == projection.local_player_id
            else projection.public_hand_for(declarer_player_id)
            or projection.remaining_hand_for(declarer_player_id)
        )
        if declarer_cards is None:
            raise ValueError(
                "Opponent-declarer Ouvert has no exact current public hand."
            )
        existing = hands.get(declarer_player_id)
        if existing is not None and set(existing) != set(declarer_cards):
            raise ValueError("Declared-Ouvert public hand constraints disagree.")
        hands[declarer_player_id] = declarer_cards
    return tuple(
        (player_id, hands[player_id])
        for player_id in projection.player_ids
        if player_id in hands
    )


def _build_visible_declaration(
    projection: SessionProjectionV1,
    *,
    local_hand: tuple[str, ...],
    authorized_public_hands: tuple[tuple[str, tuple[str, ...]], ...],
) -> dict[str, Any]:
    declaration = projection.declaration
    local_player_id = projection.local_player_id
    declarer_player_id = projection.declarer_player_id
    if declaration is None or local_player_id is None or declarer_player_id is None:
        raise ValueError("A Position-ready Session has no complete Declaration.")
    known_skat_cards = (
        projection.discarded_cards
        if local_player_id == declarer_player_id and not declaration.hand_game
        else ()
    )
    visible_matadors = infer_visible_matadors_for_decision(
        game_type=declaration.game_type,
        hand_game=declaration.hand_game,
        acting_player_id=local_player_id,
        declarer_player_id=declarer_player_id,
        own_hand=local_hand,
        known_skat_cards=known_skat_cards,
        public_plays=projection.plays,
        public_hands=authorized_public_hands,
    )
    return build_serializable_game_declaration(
        GameDeclaration(
            game_type=declaration.game_type,
            hand_game=declaration.hand_game,
            ouvert=declaration.ouvert,
            schneider_announced=declaration.schneider_announced,
            schwarz_announced=declaration.schwarz_announced,
            matadors=visible_matadors,
            bid_value=declaration.bid_value,
        )
    )


def _build_continuation_document(
    projection: SessionProjectionV1,
    stable_to_relative: Mapping[str, str],
) -> dict[str, Any] | None:
    event = projection.continuation_event
    if event is None:
        return None
    if isinstance(event, HistoricalDeclarerCardExposureContinuationEvent):
        if projection.declarer_player_id is None:
            raise ValueError("Declarer exposure continuation has no Declarer.")
        cards = projection.public_hand_for(projection.declarer_player_id)
        if cards is None:
            raise ValueError("Declarer exposure continuation has no current public hand.")
        exposure: dict[str, Any] = {"form": event.exposure.form}
        if event.exposure.shown_to_defender_player_id is not None:
            exposure["shown_to_player"] = stable_to_relative[
                event.exposure.shown_to_defender_player_id
            ]
        document = {
            "schema_version": event.schema_version,
            "kind": "declarer_card_exposure",
            "exposure": exposure,
            "claimed_play_level": event.claimed_play_level,
            "defender_responses": [
                {
                    "player": stable_to_relative[response.defender_player_id],
                    "response": response.response,
                    "form": response.form,
                }
                for response in event.defender_responses
            ],
            "public_declarer_cards": list(cards),
        }
    elif isinstance(event, HistoricalDefenderOpenPlayContinuationEvent):
        cards = projection.public_hand_for(event.exposing_defender_player_id)
        if cards is None:
            raise ValueError("Defender open-play continuation has no current public hand.")
        document = {
            "schema_version": event.schema_version,
            "kind": "defender_open_play",
            "exposing_defender": stable_to_relative[
                event.exposing_defender_player_id
            ],
            "declarer_response": event.declarer_response,
            "public_exposing_defender_cards": list(cards),
        }
    else:
        raise ValueError("A Position-ready Session has an unsupported continuation.")
    build_game_continuation(document)
    return document


def _build_position_root(
    projection: SessionProjectionV1,
    options: SessionPositionExportOptionsV1,
) -> dict[str, Any]:
    relative_player_map = _build_relative_player_map(projection)
    stable_to_relative = _build_stable_to_relative(relative_player_map)
    local_player_id = relative_player_map["me"]
    declarer_player_id = projection.declarer_player_id
    declaration = projection.declaration
    local_hand = projection.remaining_hand_for(local_player_id)
    if declarer_player_id is None or declaration is None or local_hand is None:
        raise ValueError("A Position-ready Session has incomplete local state.")

    _validate_exact_hand_sizes(projection)
    if len(local_hand) != _expected_hand_size(projection, local_player_id):
        raise ValueError("The exact local hand conflicts with accepted Plays.")
    completed_tricks = _build_completed_tricks(projection, stable_to_relative)
    current_trick, stable_trick_leader = _build_current_trick(projection)
    trick_leader = stable_to_relative[stable_trick_leader]
    normalized_phase = normalize_turn_phase_for_position(
        trick_leader=trick_leader,
        next_player="me",
        current_trick=current_trick,
        completed_tricks=completed_tricks,
    )
    authorized_public_hands = _build_authorized_public_hands(
        projection,
        local_hand=local_hand,
    )

    is_local_declarer = local_player_id == declarer_player_id
    skat = (
        list(projection.discarded_cards)
        if is_local_declarer and not declaration.hand_game
        else []
    )
    root: dict[str, Any] = {
        "game_type": declaration.game_type,
        "player_role": "declarer" if is_local_declarer else "defender",
        "declarer_player": stable_to_relative[declarer_player_id],
        "player_position": next(
            player.seat
            for player in projection.players
            if player.player_id == local_player_id
        ),
        "trick_leader": normalized_phase.trick_leader,
        "hand": list(local_hand),
        "current_trick": current_trick,
        "played_cards": [],
        "completed_tricks": completed_tricks,
        "declarer_points": 0,
        "defender_points": 0,
        "next_player": normalized_phase.next_player,
        "skat": skat,
        "skat_visibility": "known_to_declarer" if skat else "unknown",
        "left_hand_size": _expected_hand_size(
            projection, relative_player_map["left"]
        ),
        "right_hand_size": _expected_hand_size(
            projection, relative_player_map["right"]
        ),
        "sample_count": options.sample_count,
        "random_seed": options.random_seed,
        "use_basic_opponent_strategy": options.use_basic_opponent_strategy,
        "analysis_mode": "live_decision",
        "game_end_reason": "not_ended",
        "game_declaration": _build_visible_declaration(
            projection,
            local_hand=local_hand,
            authorized_public_hands=authorized_public_hands,
        ),
    }
    if declaration.ouvert and not is_local_declarer:
        public_declarer_cards = dict(authorized_public_hands).get(
            declarer_player_id
        )
        if public_declarer_cards is None:
            raise ValueError("Opponent-declarer Ouvert has no public Declarer Cards.")
        root["public_declarer_cards"] = list(public_declarer_cards)
    continuation = _build_continuation_document(projection, stable_to_relative)
    if continuation is not None:
        root["game_continuation"] = continuation
    if options.recommendation_method is not None:
        root["recommendation_method"] = options.recommendation_method
    if options.bounded_search_settings is not None:
        root["bounded_search_settings"] = _thaw_json_value(
            options.bounded_search_settings
        )
    return root


def _export_replayed_session_position_analysis_request_v1(
    *,
    state: SessionStateV1,
    projection: SessionProjectionV1,
    options: SessionPositionExportOptionsV1,
) -> SessionRequestExportV1:
    readiness = state.validation.position_export
    blockers = tuple(
        diagnostic
        for diagnostic in state.validation.diagnostics
        if diagnostic.blocks_position_export
    )
    if readiness.status == "unavailable":
        return SessionRequestExportV1(
            session_id=state.session_id,
            source_revision=state.revision,
            target=_POSITION_TARGET,
            status="unavailable",
            request=None,
            diagnostics=blockers,
        )
    if (
        projection.phase != "play"
        or projection.local_player_id is None
        or projection.next_player_id != projection.local_player_id
        or projection.game_end_reason is not None
        or blockers
    ):
        _raise_export_invariant(
            "Session Position readiness disagrees with the replayed Projection.",
            path="/validation/position_export",
        )

    try:
        root = _build_position_root(projection, options)
        validated_root = build_position_from_document(root)
        request = RequestDocumentV1(
            workflow=WorkflowV1.POSITION_ANALYSIS,
            document=validated_root,
        )
        return SessionRequestExportV1(
            session_id=state.session_id,
            source_revision=state.revision,
            target=_POSITION_TARGET,
            status="available",
            request=request,
            diagnostics=(),
        )
    except SkatMindInvariantError:
        raise
    except Exception as error:
        _raise_export_invariant(
            "Position-ready Session could not produce a validated Request.",
            path="",
            cause=error,
        )


def export_session_position_analysis_request_v1(
    state: SessionStateV1,
    options: SessionPositionExportOptionsV1,
) -> SessionRequestExportV1:
    """Exports one Position-ready Session without executing analysis."""
    if type(state) is not SessionStateV1:
        raise ValueError("state must be a SessionStateV1.")
    if type(options) is not SessionPositionExportOptionsV1:
        raise ValueError("options must be a SessionPositionExportOptionsV1.")
    projection = replay_session_state_v1(state)
    return _export_replayed_session_position_analysis_request_v1(
        state=state,
        projection=projection,
        options=options,
    )
