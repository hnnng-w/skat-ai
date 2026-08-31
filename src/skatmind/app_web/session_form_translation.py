from __future__ import annotations

import re
from collections.abc import Mapping

import skatmind.api.v1.session as session_api
from skatmind.api.v1 import ExecutionOptionsV1
from skatmind.recommendation_workflow import (
    SEARCH_RECOMMENDATION_METHODS,
    RecommendationMethodConfiguration,
    build_serializable_bounded_search_settings,
)
from skatmind.search_budget_profiles import get_search_budget_profile

_CARD_SPLIT = re.compile(r"[\s,]+")


def _text(
    values: Mapping[str, str],
    name: str,
    *,
    required: bool = False,
) -> str:
    value = values.get(name, "")
    if type(value) is not str:
        raise ValueError(f"{name} must be text.")
    if value and value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace.")
    if required and not value:
        raise ValueError(f"{name} is required as non-padded text.")
    return value


def _require_keys(values: Mapping[str, str], allowed: set[str]) -> None:
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(f"Session form has unsupported fields: {unknown}.")


def _optional_text(values: Mapping[str, str], name: str) -> str | None:
    value = _text(values, name)
    return value or None


def _integer(values: Mapping[str, str], name: str) -> int:
    value = _text(values, name, required=True)
    if not re.fullmatch(r"-?[0-9]+", value):
        raise ValueError(f"{name} must be an integer.")
    return int(value)


def _optional_integer(values: Mapping[str, str], name: str) -> int | None:
    return None if _text(values, name) == "" else _integer(values, name)


def _boolean(values: Mapping[str, str], name: str) -> bool:
    value = _text(values, name, required=True)
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false.")
    return value == "true"


def _cards(values: Mapping[str, str], name: str) -> list[str]:
    return [item for item in _CARD_SPLIT.split(_text(values, name)) if item]


def _response(values: Mapping[str, str], index: int) -> dict[str, object]:
    return {
        "defender_player_id": _text(
            values,
            f"defender_{index}_player_id",
            required=True,
        ),
        "response": _text(values, f"defender_{index}_response", required=True),
        "form": _text(values, f"defender_{index}_form", required=True),
    }


def _exposure(values: Mapping[str, str], *, include_cards: bool) -> dict[str, object]:
    form = _text(values, "exposure_form", required=True)
    result: dict[str, object] = {"form": form}
    if include_cards:
        result["exposed_cards"] = _cards(values, "cards")
    if form == "shown_to_defender":
        result["shown_to_defender_player_id"] = _text(
            values,
            "shown_to_defender_player_id",
            required=True,
        )
    return result


def _event(values: Mapping[str, str]) -> dict[str, object]:
    kind = _text(values, "event_kind", required=True)
    if kind == "defender_open_play_continuation":
        return {
            "schema_version": 1,
            "kind": kind,
            "after_play_count": _integer(values, "after_play_count"),
            "exposing_defender_player_id": _text(
                values,
                "player_id",
                required=True,
            ),
            "exposed_cards": _cards(values, "cards"),
            "declarer_response": "request_continued_play",
        }
    if kind == "declarer_card_exposure_continuation":
        return {
            "schema_version": 1,
            "kind": kind,
            "after_play_count": _integer(values, "after_play_count"),
            "exposure": _exposure(values, include_cards=False),
            "claimed_play_level": _text(
                values,
                "claimed_play_level",
                required=True,
            ),
            "defender_responses": [_response(values, 1), _response(values, 2)],
            "public_declarer_cards": _cards(values, "cards"),
        }
    raise ValueError("event_kind must identify one supported continuation.")


def _game_end(values: Mapping[str, str], reason: str) -> dict[str, object] | None:
    if reason == "normal_completion":
        return None
    if reason == "declarer_concession":
        return {
            "schema_version": 1,
            "kind": reason,
            "declarer_hand_cards_remaining": _integer(
                values,
                "remaining_card_count",
            ),
            "defender_consent": {
                "status": _text(values, "consent_status", required=True),
                "consenting_defender_player_ids": _cards(
                    values,
                    "consenting_player_ids",
                ),
            },
        }
    if reason == "defender_concession":
        return {
            "schema_version": 1,
            "kind": reason,
            "conceding_defender_player_id": _text(
                values,
                "player_id",
                required=True,
            ),
            "concession_form": _text(
                values,
                "concession_form",
                required=True,
            ),
        }
    if reason == "declarer_card_exposure":
        return {
            "schema_version": 1,
            "kind": reason,
            "exposure": _exposure(values, include_cards=True),
            "claimed_play_level": _text(
                values,
                "claimed_play_level",
                required=True,
            ),
            "defender_responses": [_response(values, 1), _response(values, 2)],
        }
    if reason == "defender_open_play":
        return {
            "schema_version": 1,
            "kind": reason,
            "exposing_defender_player_id": _text(
                values,
                "player_id",
                required=True,
            ),
            "exposed_cards": _cards(values, "cards"),
            "declarer_response": "accept_adjudication",
        }
    if reason == "open_card_throw":
        return {
            "schema_version": 1,
            "kind": reason,
            "throwing_player_id": _text(values, "player_id", required=True),
            "thrown_cards": _cards(values, "cards"),
            "statement_classification": _text(
                values,
                "statement_classification",
                required=True,
            ),
        }
    raise ValueError("game_end_reason must identify one supported Session end.")


def build_session_command_from_form_v1(
    values: Mapping[str, str],
    *,
    expected_revision: int,
) -> session_api.SessionCommandV1:
    kind = _text(values, "kind", required=True)
    fields_by_kind = {
        "set_game_metadata": {"kind", "game_id", "played_at"},
        "record_dealt_card": {"kind", "destination", "player_id", "card"},
        "set_declarer": {"kind", "player_id"},
        "set_declaration": {
            "kind",
            "game_type",
            "hand_game",
            "ouvert",
            "schneider_announced",
            "schwarz_announced",
            "matadors",
            "bid_value",
        },
        "record_discard": {"kind", "card"},
        "record_play": {"kind", "player_id", "card"},
        "set_game_event": {
            "kind",
            "event_kind",
            "after_play_count",
            "player_id",
            "cards",
            "exposure_form",
            "shown_to_defender_player_id",
            "claimed_play_level",
            "defender_1_player_id",
            "defender_1_response",
            "defender_1_form",
            "defender_2_player_id",
            "defender_2_response",
            "defender_2_form",
        },
        "set_game_end": {
            "kind",
            "game_end_reason",
            "player_id",
            "cards",
            "remaining_card_count",
            "consent_status",
            "consenting_player_ids",
            "concession_form",
            "statement_classification",
            "exposure_form",
            "shown_to_defender_player_id",
            "claimed_play_level",
            "defender_1_player_id",
            "defender_1_response",
            "defender_1_form",
            "defender_2_player_id",
            "defender_2_response",
            "defender_2_form",
        },
        "promote_to_retrospective": {"kind"},
        "set_public_hand": {"kind", "player_id", "cards"},
    }
    if kind not in fields_by_kind:
        raise ValueError("kind must identify one supported Session Command.")
    _require_keys(values, fields_by_kind[kind])
    document: dict[str, object] = {
        "command_version": 1,
        "kind": kind,
        "expected_revision": expected_revision,
    }
    if kind == "set_game_metadata":
        document.update(
            game_id=_optional_text(values, "game_id"),
            played_at=_optional_text(values, "played_at"),
        )
    elif kind == "record_dealt_card":
        destination = _text(values, "destination", required=True)
        document.update(
            destination=destination,
            player_id=(
                _text(values, "player_id", required=True)
                if destination == "player_hand"
                else None
            ),
            card=_text(values, "card", required=True),
        )
    elif kind == "set_declarer":
        document["declarer_player_id"] = _text(
            values,
            "player_id",
            required=True,
        )
    elif kind == "set_declaration":
        document["declaration"] = {
            "game_type": _text(values, "game_type", required=True),
            "hand_game": _boolean(values, "hand_game"),
            "ouvert": _boolean(values, "ouvert"),
            "schneider_announced": _boolean(values, "schneider_announced"),
            "schwarz_announced": _boolean(values, "schwarz_announced"),
            "matadors": _optional_integer(values, "matadors"),
            "bid_value": _optional_integer(values, "bid_value"),
        }
    elif kind == "record_discard":
        document["card"] = _text(values, "card", required=True)
    elif kind == "record_play":
        document.update(
            player_id=_text(values, "player_id", required=True),
            card=_text(values, "card", required=True),
        )
    elif kind == "set_game_event":
        document["event"] = _event(values)
    elif kind == "set_game_end":
        reason = _text(values, "game_end_reason", required=True)
        document.update(
            game_end_reason=reason,
            game_end=_game_end(values, reason),
        )
    elif kind == "promote_to_retrospective":
        pass
    elif kind == "set_public_hand":
        document.update(
            source="declared_ouvert",
            player_id=_text(values, "player_id", required=True),
            cards=_cards(values, "cards"),
        )
    return session_api.parse_session_command(document)


def build_session_edit_from_form_v1(
    values: Mapping[str, str],
    *,
    current_revision: int,
) -> session_api.SessionCommandV1 | session_api.SessionCommandCorrectionV1:
    raw_target = _text(values, "target_revision")
    command_values = dict(values)
    command_values.pop("target_revision", None)
    if raw_target == "":
        return build_session_command_from_form_v1(
            command_values,
            expected_revision=current_revision,
        )
    if not raw_target.isdecimal() or raw_target.startswith("0"):
        raise ValueError("target_revision must be a positive integer without leading zeroes.")
    target_revision = int(raw_target)
    replacement = build_session_command_from_form_v1(
        command_values,
        expected_revision=target_revision - 1,
    )
    return session_api.SessionCommandCorrectionV1(
        expected_revision=current_revision,
        target_revision=target_revision,
        replacement_command=replacement,
    )


def build_session_position_options_from_form_v1(
    values: Mapping[str, str],
) -> session_api.SessionPositionExportOptionsV1:
    _require_keys(
        values,
        {
            "sample_count",
            "random_seed",
            "opponent_strategy",
            "recommendation_method",
            "search_budget_profile",
        },
    )
    method = _optional_text(values, "recommendation_method")
    seed = _integer(values, "random_seed")
    bounded = None
    if method in SEARCH_RECOMMENDATION_METHODS:
        bounded = build_serializable_bounded_search_settings(
            RecommendationMethodConfiguration(
                explicitly_supplied=True,
                requested_method=method,
                search_random_seed=seed,
                requested_search_budget=get_search_budget_profile(
                    _text(values, "search_budget_profile", required=True)
                ),
            )
        )
    opponent_strategy = _text(values, "opponent_strategy", required=True)
    if opponent_strategy not in {"basic", "random"}:
        raise ValueError("opponent_strategy must be basic or random.")
    return session_api.SessionPositionExportOptionsV1(
        sample_count=_integer(values, "sample_count"),
        random_seed=seed,
        use_basic_opponent_strategy=opponent_strategy == "basic",
        recommendation_method=method,
        bounded_search_settings=bounded,
    )


def build_session_historical_execution_options_from_form_v1(
    values: Mapping[str, str],
) -> ExecutionOptionsV1:
    option_names = (
        "decision_snapshots",
        "immediate_review",
        "search_review",
        "information_set_search_review",
        "replay_coaching",
        "information_set_replay_coaching",
        "historical_tactical_motif_review",
    )
    _require_keys(
        values,
        {
            *option_names,
            "sample_count",
            "random_seed",
            "search_seed",
            "search_budget_profile",
        },
    )
    workflow_options: dict[str, object] = {
        name: _boolean(values, name) for name in option_names
    }
    workflow_options.update(
        immediate_sample_count=_integer(values, "sample_count"),
        immediate_base_random_seed=_integer(values, "random_seed"),
        search_seed=_integer(values, "search_seed"),
        search_budget_profile=_text(
            values,
            "search_budget_profile",
            required=True,
        ),
    )
    return ExecutionOptionsV1(workflow_options=workflow_options)
