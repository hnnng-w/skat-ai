from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from skatmind.input_validation import MAX_SAMPLE_COUNT
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

from .form_parsing import (
    FormFieldErrorV1,
    FormValuesV1,
    parse_checkbox_v1,
    parse_form_mapping_v1,
    parse_integer_text_v1,
)
from .historical_form import (
    HISTORICAL_PLAYER_IDS,
    HistoricalFormDraftV1,
    append_historical_play_v1,
    update_historical_deal_v1,
    update_historical_declaration_v1,
    update_historical_discards_v1,
    update_historical_options_v1,
    update_historical_players_v1,
)


@dataclass(frozen=True, slots=True)
class HistoricalFormInputError(ValueError):
    errors: tuple[FormFieldErrorV1, ...]
    draft: HistoricalFormDraftV1 | None = None

    def __post_init__(self) -> None:
        if not self.errors or any(
            type(error) is not FormFieldErrorV1 for error in self.errors
        ):
            raise ValueError("Historical form errors must contain field messages.")
        if self.draft is not None and type(self.draft) is not HistoricalFormDraftV1:
            raise ValueError("Historical form error draft must be exact or None.")
        ValueError.__init__(self, "Historical form validation failed.")


def _values(
    raw: Mapping[str, list[str] | tuple[str, ...]],
    *,
    allowed: tuple[str, ...],
    multi: tuple[str, ...] = (),
) -> FormValuesV1:
    parsed = parse_form_mapping_v1(
        raw,
        allowed_fields=allowed,
        multi_value_fields=multi,
    )
    if parsed.errors:
        raise HistoricalFormInputError(parsed.errors)
    return parsed.values


def _required_text(values: FormValuesV1, field: str) -> str:
    value = values.singular(field)
    if value is None or not value or value != value.strip():
        raise HistoricalFormInputError(
            (FormFieldErrorV1(field, "This field is required without surrounding spaces."),)
        )
    return value


def _optional_text(values: FormValuesV1, field: str) -> str | None:
    value = values.singular(field)
    if value in (None, ""):
        return None
    if value != value.strip():
        raise HistoricalFormInputError(
            (FormFieldErrorV1(field, "This field must not contain surrounding spaces."),)
        )
    return value


def _integer(
    values: FormValuesV1,
    field: str,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    value = values.singular(field)
    if value in (None, ""):
        return default
    try:
        return parse_integer_text_v1(
            value,
            field=field,
            minimum=minimum,
            maximum=maximum,
        )
    except ValueError as error:
        raise HistoricalFormInputError((FormFieldErrorV1(field, str(error)),)) from error


def _checkbox(values: FormValuesV1, field: str) -> bool:
    try:
        return parse_checkbox_v1(values, field)
    except ValueError as error:
        raise HistoricalFormInputError((FormFieldErrorV1(field, str(error)),)) from error


def parse_historical_players_form_v1(
    draft: HistoricalFormDraftV1,
    raw: Mapping[str, list[str] | tuple[str, ...]],
) -> HistoricalFormDraftV1:
    fields = ("forehand_label", "middlehand_label", "rearhand_label")
    values = _values(raw, allowed=fields)
    return update_historical_players_v1(
        draft,
        forehand_label=_optional_text(values, fields[0]),
        middlehand_label=_optional_text(values, fields[1]),
        rearhand_label=_optional_text(values, fields[2]),
    )


def parse_historical_deal_form_v1(
    draft: HistoricalFormDraftV1,
    raw: Mapping[str, list[str] | tuple[str, ...]],
) -> HistoricalFormDraftV1:
    fields = ("forehand_hand", "middlehand_hand", "rearhand_hand", "skat")
    values = _values(raw, allowed=fields, multi=fields)
    hands = tuple(values.all(field) for field in fields[:3])
    skat = values.all(fields[3])
    retained = replace(
        draft,
        players=tuple(
            replace(player, initial_hand=hand)
            for player, hand in zip(draft.players, hands, strict=True)
        ),
        skat=skat,
    )
    try:
        return update_historical_deal_v1(
            draft,
            forehand_hand=hands[0],
            middlehand_hand=hands[1],
            rearhand_hand=hands[2],
            skat=skat,
        )
    except ValueError as error:
        raise HistoricalFormInputError(
            (FormFieldErrorV1("_form", str(error)),),
            retained,
        ) from error


def parse_historical_declaration_form_v1(
    draft: HistoricalFormDraftV1,
    raw: Mapping[str, list[str] | tuple[str, ...]],
) -> HistoricalFormDraftV1:
    fields = (
        "declarer_player_id",
        "game_type",
        "bid_value",
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
    )
    values = _values(raw, allowed=fields)
    bid_value = _integer(values, "bid_value", default=0, minimum=1)
    return update_historical_declaration_v1(
        draft,
        declarer_player_id=_required_text(values, "declarer_player_id"),
        game_type=_required_text(values, "game_type"),
        bid_value=bid_value,
        hand_game=_checkbox(values, "hand_game"),
        ouvert=_checkbox(values, "ouvert"),
        schneider_announced=_checkbox(values, "schneider_announced"),
        schwarz_announced=_checkbox(values, "schwarz_announced"),
    )


def parse_historical_discards_form_v1(
    draft: HistoricalFormDraftV1,
    raw: Mapping[str, list[str] | tuple[str, ...]],
) -> HistoricalFormDraftV1:
    values = _values(raw, allowed=("discarded_cards",), multi=("discarded_cards",))
    return update_historical_discards_v1(draft, values.all("discarded_cards"))


def parse_historical_play_form_v1(
    draft: HistoricalFormDraftV1,
    raw: Mapping[str, list[str] | tuple[str, ...]],
) -> HistoricalFormDraftV1:
    if draft.step != 5:
        raise ValueError("Historical form step 5 (play) is required.")
    if len(draft.plays) == 30 and not raw:
        return HistoricalFormDraftV1(
            step=6,
            players=draft.players,
            skat=draft.skat,
            declaration=draft.declaration,
            discarded_cards=draft.discarded_cards,
            plays=draft.plays,
            options=draft.options,
        )
    values = _values(raw, allowed=("card",))
    return append_historical_play_v1(draft, _required_text(values, "card"))


def parse_historical_options_form_v1(
    draft: HistoricalFormDraftV1,
    raw: Mapping[str, list[str] | tuple[str, ...]],
) -> HistoricalFormDraftV1:
    fields = (
        "decision_snapshots",
        "immediate_review",
        "search_review",
        "information_set_search_review",
        "replay_coaching",
        "information_set_replay_coaching",
        "tactical",
        "include_provenance",
        "search_seed",
        "immediate_sample_count",
        "immediate_base_random_seed",
    )
    values = _values(raw, allowed=fields)
    return update_historical_options_v1(
        draft,
        decision_snapshots=_checkbox(values, "decision_snapshots"),
        immediate_review=_checkbox(values, "immediate_review"),
        search_review=_checkbox(values, "search_review"),
        information_set_search_review=_checkbox(
            values, "information_set_search_review"
        ),
        replay_coaching=_checkbox(values, "replay_coaching"),
        information_set_replay_coaching=_checkbox(
            values, "information_set_replay_coaching"
        ),
        tactical=_checkbox(values, "tactical"),
        include_provenance=_checkbox(values, "include_provenance"),
        search_seed=_integer(values, "search_seed", default=0),
        immediate_sample_count=_integer(
            values,
            "immediate_sample_count",
            default=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
            minimum=1,
            maximum=MAX_SAMPLE_COUNT,
        ),
        immediate_base_random_seed=_integer(
            values,
            "immediate_base_random_seed",
            default=0,
        ),
    )


def historical_player_label_v1(draft: HistoricalFormDraftV1, player_id: str) -> str:
    if player_id not in HISTORICAL_PLAYER_IDS:
        raise ValueError("player_id must identify one guided Historical Player.")
    player = next(player for player in draft.players if player.player_id == player_id)
    return player.player_label or player.seat.title()
