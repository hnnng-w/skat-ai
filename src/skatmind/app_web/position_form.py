from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from types import MappingProxyType

from skatmind.api.v1 import ExecutionOptionsV1, RequestDocumentV1, parse_request
from skatmind.card_selection import VALID_MULTI_STEP_POLICIES
from skatmind.errors import SkatMindError
from skatmind.game_declaration import normalize_game_declaration_values
from skatmind.game_history import (
    get_players_for_trick_leader,
    validate_completed_trick_sequence,
)
from skatmind.input_loader import build_position_from_document
from skatmind.opponent_policy import VALID_OPPONENT_CARD_POLICIES
from skatmind.opponent_policy_preset import VALID_OPPONENT_POLICY_PRESETS
from skatmind.rules import GAME_TYPES, get_trick_winner
from skatmind.search_budget_profiles import (
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
    convert_requested_search_budget_to_information_set_search_budget_v1,
    get_search_budget_profile,
)
from skatmind.side_ownership import get_winner_role
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
from skatmind.turn_phase import CONCRETE_PLAYERS, normalize_turn_phase_for_position

from .card_form import (
    CardZoneSelectionV1,
    find_card_zone_conflicts_v1,
    is_canonical_card_code_v1,
)
from .form_parsing import (
    FormFieldErrorV1,
    FormValuesV1,
    parse_checkbox_v1,
    parse_form_mapping_v1,
    parse_integer_text_v1,
)
from .guided_contracts import GUIDED_POSITION_FORM_VERSION

DEFAULT_POSITION_SAMPLE_COUNT_V1 = 1000
DEFAULT_POSITION_RANDOM_SEED_V1 = 42
DEFAULT_POSITION_SEARCH_SEED_V1 = 42
POSITION_COMPLETED_TRICK_ROW_COUNT_V1 = 9

POSITION_COMPLETED_TRICK_SELECTOR_FIELDS_V1 = tuple(
    field
    for trick_number in range(1, POSITION_COMPLETED_TRICK_ROW_COUNT_V1 + 1)
    for field in (
        f"completed_trick_{trick_number}_leader",
        f"completed_trick_{trick_number}_card_1",
        f"completed_trick_{trick_number}_card_2",
        f"completed_trick_{trick_number}_card_3",
    )
)

POSITION_FORM_FIELDS_V1 = (
    "analysis_mode",
    "game_type",
    "player_role",
    "player_position",
    "declarer_player",
    "hand_game",
    "schneider_announced",
    "schwarz_announced",
    "ouvert",
    "bid_value",
    "matadors",
    "hand",
    "skat",
    "public_declarer_cards",
    "completed_tricks",
    "current_trick",
    "trick_leader",
    "declarer_points",
    "defender_points",
    "left_hand_size",
    "right_hand_size",
    "actual_card_played",
    "analysis_method",
    "sample_count",
    "random_seed",
    "search_seed",
    "opponent_strategy",
    "opponent_policy_preset",
    "opponent_lead_policy",
    "opponent_response_policy",
    "left_opponent_lead_policy",
    "left_opponent_response_policy",
    "right_opponent_lead_policy",
    "right_opponent_response_policy",
    "use_profile_presets",
    "multi_step_count",
    "card_selection_policy",
    "expected_value_sample_count",
    "strict_context",
    "compare_policies",
    "comparison_only",
    "include_provenance",
) + POSITION_COMPLETED_TRICK_SELECTOR_FIELDS_V1
POSITION_FORM_CARD_FIELDS_V1 = (
    "hand",
    "skat",
    "public_declarer_cards",
    "current_trick",
)


@dataclass(frozen=True, slots=True)
class PositionAnalysisMethodV1:
    form_value: str
    label: str
    recommendation_method: str | None


POSITION_ANALYSIS_METHODS_V1 = (
    PositionAnalysisMethodV1("immediate", "Standard immediate analysis", None),
    PositionAnalysisMethodV1("bounded_search", "Bounded Search", "bounded_search"),
    PositionAnalysisMethodV1(
        "auto",
        "Automatic Search with Immediate fallback",
        "auto",
    ),
    PositionAnalysisMethodV1(
        "information_set_search",
        "Information-set Search",
        "information_set_search",
    ),
)
POSITION_OPPONENT_POLICIES_V1 = tuple(VALID_OPPONENT_CARD_POLICIES)
POSITION_POLICY_PRESETS_V1 = tuple(VALID_OPPONENT_POLICY_PRESETS)
POSITION_MULTI_STEP_POLICIES_V1 = tuple(VALID_MULTI_STEP_POLICIES)


@dataclass(frozen=True, slots=True)
class CompletedTrickFormValueV1:
    leader: str
    cards: tuple[str, str, str]
    players: tuple[str, str, str]
    winner_player: str
    winner_side: str


@dataclass(frozen=True, slots=True)
class PositionFormDraftV1:
    """Immutable process-local guided Position form draft."""

    form_version: int
    form_values: FormValuesV1
    analysis_mode: str
    game_type: str
    player_role: str
    player_position: str
    declarer_player: str
    hand_game: bool
    schneider_announced: bool
    schwarz_announced: bool
    ouvert: bool
    bid_value: int | None
    matadors: int | None
    hand: tuple[str, ...]
    skat: tuple[str, ...]
    public_declarer_cards: tuple[str, ...]
    completed_tricks: tuple[CompletedTrickFormValueV1, ...]
    current_trick: tuple[str, ...]
    trick_leader: str
    declarer_points: int
    defender_points: int
    left_hand_size: int | None
    right_hand_size: int | None
    actual_card_played: str | None
    analysis_method: str
    sample_count: int
    random_seed: int
    search_seed: int
    opponent_strategy: str | None
    opponent_policy_preset: str | None
    opponent_lead_policy: str | None
    opponent_response_policy: str | None
    left_opponent_lead_policy: str | None
    left_opponent_response_policy: str | None
    right_opponent_lead_policy: str | None
    right_opponent_response_policy: str | None
    use_profile_presets: bool
    multi_step_count: int | None
    card_selection_policy: str | None
    expected_value_sample_count: int
    strict_context: bool
    compare_policies: bool
    comparison_only: bool
    include_provenance: bool

    def __post_init__(self) -> None:
        if type(self.form_version) is not int or self.form_version != GUIDED_POSITION_FORM_VERSION:
            raise ValueError(f"form_version must equal {GUIDED_POSITION_FORM_VERSION}.")
        if type(self.form_values) is not FormValuesV1:
            raise ValueError("form_values must be exact FormValuesV1 values.")
        for field in (
            "hand",
            "skat",
            "public_declarer_cards",
            "completed_tricks",
            "current_trick",
        ):
            object.__setattr__(self, field, tuple(getattr(self, field)))


class PositionFormError(ValueError):
    """Private validation failure retaining the safe immutable form draft."""

    __slots__ = ("_draft", "_errors")

    def __init__(
        self,
        draft: PositionFormDraftV1,
        errors: tuple[FormFieldErrorV1, ...],
    ) -> None:
        if type(draft) is not PositionFormDraftV1:
            raise TypeError("draft must be an exact PositionFormDraftV1.")
        errors = tuple(errors)
        if not errors or any(type(error) is not FormFieldErrorV1 for error in errors):
            raise TypeError("errors must contain exact FormFieldErrorV1 values.")
        self._draft = draft
        self._errors = errors
        super().__init__("Position form validation failed.")

    @property
    def draft(self) -> PositionFormDraftV1:
        return self._draft

    @property
    def errors(self) -> tuple[FormFieldErrorV1, ...]:
        return self._errors

    @property
    def field_messages(self) -> Mapping[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {}
        for error in self.errors:
            grouped.setdefault(error.field, []).append(error.message)
        return MappingProxyType({field: tuple(messages) for field, messages in grouped.items()})


def _has_error(errors: list[FormFieldErrorV1], field: str) -> bool:
    return any(error.field == field for error in errors)


def _add_error(errors: list[FormFieldErrorV1], field: str, message: str) -> None:
    error = FormFieldErrorV1(field=field, message=message)
    if error not in errors:
        errors.append(error)


def _text(
    values: FormValuesV1,
    errors: list[FormFieldErrorV1],
    field: str,
    *,
    default: str = "",
    required: bool = False,
    choices: tuple[str, ...] | None = None,
) -> str:
    if _has_error(errors, field):
        return default
    value = values.singular(field)
    if value is None or value == "":
        if required:
            _add_error(errors, field, "This field is required.")
        return default
    if value != value.strip():
        _add_error(errors, field, "This field must not contain surrounding whitespace.")
        return default
    if choices is not None and value not in choices:
        _add_error(
            errors,
            field,
            f"This field must be one of: {', '.join(choices)}.",
        )
        return default
    return value


def _integer(
    values: FormValuesV1,
    errors: list[FormFieldErrorV1],
    field: str,
    *,
    default: int | None,
    minimum: int | None = None,
    maximum: int | None = None,
    required: bool = False,
) -> int | None:
    if _has_error(errors, field):
        return default
    value = values.singular(field)
    if value is None or value == "":
        if required:
            _add_error(errors, field, "This field is required.")
        return default
    try:
        return parse_integer_text_v1(
            value,
            field=field,
            minimum=minimum,
            maximum=maximum,
        )
    except ValueError as error:
        _add_error(errors, field, str(error))
        return default


def _checkbox(
    values: FormValuesV1,
    errors: list[FormFieldErrorV1],
    field: str,
) -> bool:
    if _has_error(errors, field):
        return False
    try:
        return parse_checkbox_v1(values, field)
    except ValueError as error:
        _add_error(errors, field, str(error))
        return False


def _cards(
    values: FormValuesV1,
    errors: list[FormFieldErrorV1],
    field: str,
    *,
    minimum: int = 0,
    maximum: int,
) -> tuple[str, ...]:
    cards = tuple(card for card in values.all(field) if card)
    if _has_error(errors, field):
        return ()
    if len(cards) < minimum or len(cards) > maximum:
        if minimum == maximum:
            message = f"Select exactly {minimum} Cards."
        else:
            message = f"Select from {minimum} through {maximum} Cards."
        _add_error(errors, field, message)
    invalid = tuple(card for card in cards if not is_canonical_card_code_v1(card))
    if invalid:
        _add_error(errors, field, f"Unknown Card codes: {', '.join(invalid)}.")
    return cards


def _parse_completed_tricks(
    text: str,
    *,
    game_type: str,
    declarer_player: str,
    errors: list[FormFieldErrorV1],
) -> tuple[CompletedTrickFormValueV1, ...]:
    if not text:
        return ()
    parsed: list[CompletedTrickFormValueV1] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            _add_error(
                errors,
                "completed_tricks",
                f"Line {line_number} is empty; remove blank lines.",
            )
            continue
        if line.count("|") != 1:
            _add_error(
                errors,
                "completed_tricks",
                f"Line {line_number} must use leader|CARD,CARD,CARD.",
            )
            continue
        leader, card_text = line.split("|")
        cards = tuple(card_text.split(","))
        if leader not in CONCRETE_PLAYERS or len(cards) != 3:
            _add_error(
                errors,
                "completed_tricks",
                f"Line {line_number} must use leader|CARD,CARD,CARD.",
            )
            continue
        if any(not is_canonical_card_code_v1(card) for card in cards):
            _add_error(
                errors,
                "completed_tricks",
                f"Line {line_number} contains an unknown Card code.",
            )
            continue
        if game_type not in GAME_TYPES or declarer_player not in CONCRETE_PLAYERS:
            continue
        players_list = get_players_for_trick_leader(leader)
        winner_index = get_trick_winner(list(cards), game_type)
        winner_player = players_list[winner_index]
        winner_side = get_winner_role(winner_player, declarer_player)
        if winner_side is None:
            continue
        parsed.append(
            CompletedTrickFormValueV1(
                leader=leader,
                cards=(cards[0], cards[1], cards[2]),
                players=(players_list[0], players_list[1], players_list[2]),
                winner_player=winner_player,
                winner_side=winner_side,
            )
        )
    return tuple(parsed)


def _completed_trick_selector_text(
    values: FormValuesV1,
    errors: list[FormFieldErrorV1],
) -> str:
    lines = []
    for trick_number in range(1, POSITION_COMPLETED_TRICK_ROW_COUNT_V1 + 1):
        leader = values.singular(f"completed_trick_{trick_number}_leader") or ""
        cards = tuple(
            values.singular(f"completed_trick_{trick_number}_card_{card_number}") or ""
            for card_number in range(1, 4)
        )
        supplied = tuple(value for value in (leader, *cards) if value)
        if not supplied:
            continue
        if len(supplied) != 4:
            _add_error(
                errors,
                "completed_tricks",
                f"Completed Trick {trick_number} requires one leader and three Cards.",
            )
            continue
        lines.append(f"{leader}|{','.join(cards)}")
    return "\n".join(lines)


def parse_position_form_v1(
    values: Mapping[str, list[str] | tuple[str, ...]],
) -> PositionFormDraftV1:
    """Parses one strict browser form into an immutable guided Position draft."""

    mapping_result = parse_form_mapping_v1(
        values,
        allowed_fields=POSITION_FORM_FIELDS_V1,
        multi_value_fields=POSITION_FORM_CARD_FIELDS_V1,
    )
    form_values = mapping_result.values
    errors = list(mapping_result.errors)
    analysis_mode = _text(
        form_values,
        errors,
        "analysis_mode",
        default="live_decision",
        choices=("live_decision", "post_game_review"),
    )
    game_type = _text(
        form_values,
        errors,
        "game_type",
        required=True,
        choices=tuple(GAME_TYPES),
    )
    player_role = _text(
        form_values,
        errors,
        "player_role",
        required=True,
        choices=("declarer", "defender"),
    )
    player_position = _text(
        form_values,
        errors,
        "player_position",
        required=True,
        choices=("forehand", "middlehand", "rearhand"),
    )
    supplied_declarer = _text(
        form_values,
        errors,
        "declarer_player",
        choices=("me", "left", "right"),
    )
    if player_role == "declarer":
        if supplied_declarer not in ("", "me"):
            _add_error(
                errors,
                "declarer_player",
                "A local Declarer requires declarer_player=me.",
            )
        declarer_player = "me"
    elif player_role == "defender":
        declarer_player = supplied_declarer
        if declarer_player not in ("left", "right"):
            _add_error(
                errors,
                "declarer_player",
                "Choose whether the Declarer is the left or right opponent.",
            )
    else:
        declarer_player = supplied_declarer

    hand_game = _checkbox(form_values, errors, "hand_game")
    schneider_announced = _checkbox(form_values, errors, "schneider_announced")
    schwarz_announced = _checkbox(form_values, errors, "schwarz_announced")
    ouvert = _checkbox(form_values, errors, "ouvert")
    bid_value = _integer(
        form_values,
        errors,
        "bid_value",
        default=None,
        minimum=1,
    )
    matador_maximum = 4 if game_type == "grand" else 11
    matadors = _integer(
        form_values,
        errors,
        "matadors",
        default=None,
        minimum=1,
        maximum=matador_maximum,
    )
    if game_type == "null" and matadors is not None:
        _add_error(errors, "matadors", "Null contracts do not use Matadors.")
        matadors = None

    hand = _cards(form_values, errors, "hand", minimum=1, maximum=10)
    skat = _cards(form_values, errors, "skat", maximum=2)
    if len(skat) == 1:
        _add_error(errors, "skat", "Select either zero or exactly two visible Skat Cards.")
    if skat and analysis_mode == "live_decision":
        if declarer_player != "me":
            _add_error(
                errors,
                "skat",
                "Visible Skat Cards are private to the local Declarer during live play.",
            )
        if hand_game:
            _add_error(
                errors,
                "skat",
                "A live Hand contract cannot expose the Skat to the Declarer.",
            )
    public_declarer_cards = _cards(
        form_values,
        errors,
        "public_declarer_cards",
        maximum=10,
    )
    current_trick = _cards(form_values, errors, "current_trick", maximum=2)
    completed_text = _text(form_values, errors, "completed_tricks")
    selector_text = _completed_trick_selector_text(form_values, errors)
    if completed_text and selector_text:
        _add_error(
            errors,
            "completed_tricks",
            "Use either guided completed-Trick selectors or the internal text value, not both.",
        )
    if selector_text:
        completed_text = selector_text
    completed_tricks = _parse_completed_tricks(
        completed_text,
        game_type=game_type,
        declarer_player=declarer_player,
        errors=errors,
    )
    trick_leader = _text(
        form_values,
        errors,
        "trick_leader",
        required=True,
        choices=tuple(CONCRETE_PLAYERS),
    )
    declarer_points_value = _integer(
        form_values,
        errors,
        "declarer_points",
        default=0,
        minimum=0,
        maximum=120,
    )
    defender_points_value = _integer(
        form_values,
        errors,
        "defender_points",
        default=0,
        minimum=0,
        maximum=120,
    )
    left_hand_size = _integer(
        form_values,
        errors,
        "left_hand_size",
        default=None,
        minimum=0,
        maximum=10,
    )
    right_hand_size = _integer(
        form_values,
        errors,
        "right_hand_size",
        default=None,
        minimum=0,
        maximum=10,
    )
    actual_card_played = _text(form_values, errors, "actual_card_played") or None
    if actual_card_played is not None and not is_canonical_card_code_v1(actual_card_played):
        _add_error(errors, "actual_card_played", "Choose one canonical Card.")
        actual_card_played = None
    if analysis_mode == "post_game_review" and actual_card_played is None:
        _add_error(
            errors,
            "actual_card_played",
            "Choose the Card that was actually played for retrospective review.",
        )
    if analysis_mode == "live_decision" and actual_card_played is not None:
        _add_error(
            errors,
            "actual_card_played",
            "An actual Card is accepted only for retrospective review.",
        )

    method_values = tuple(method.form_value for method in POSITION_ANALYSIS_METHODS_V1)
    analysis_method = _text(
        form_values,
        errors,
        "analysis_method",
        default="immediate",
        choices=method_values,
    )
    sample_count_value = _integer(
        form_values,
        errors,
        "sample_count",
        default=DEFAULT_POSITION_SAMPLE_COUNT_V1,
        minimum=1,
        maximum=100_000,
    )
    random_seed_value = _integer(
        form_values,
        errors,
        "random_seed",
        default=DEFAULT_POSITION_RANDOM_SEED_V1,
    )
    search_seed_value = _integer(
        form_values,
        errors,
        "search_seed",
        default=DEFAULT_POSITION_SEARCH_SEED_V1,
    )
    opponent_strategy = (
        _text(
            form_values,
            errors,
            "opponent_strategy",
            choices=("basic", "random"),
        )
        or None
    )
    opponent_policy_preset = (
        _text(
            form_values,
            errors,
            "opponent_policy_preset",
            choices=tuple(VALID_OPPONENT_POLICY_PRESETS),
        )
        or None
    )

    policy_values: dict[str, str | None] = {}
    for field in (
        "opponent_lead_policy",
        "opponent_response_policy",
        "left_opponent_lead_policy",
        "left_opponent_response_policy",
        "right_opponent_lead_policy",
        "right_opponent_response_policy",
    ):
        policy_values[field] = (
            _text(
                form_values,
                errors,
                field,
                choices=tuple(VALID_OPPONENT_CARD_POLICIES),
            )
            or None
        )

    use_profile_presets = _checkbox(form_values, errors, "use_profile_presets")
    multi_step_count = _integer(
        form_values,
        errors,
        "multi_step_count",
        default=None,
        minimum=1,
    )
    card_selection_policy = (
        _text(
            form_values,
            errors,
            "card_selection_policy",
            choices=tuple(VALID_MULTI_STEP_POLICIES),
        )
        or None
    )
    expected_value_sample_count_value = _integer(
        form_values,
        errors,
        "expected_value_sample_count",
        default=DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
        minimum=1,
        maximum=100_000,
    )
    strict_context = _checkbox(form_values, errors, "strict_context")
    compare_policies = _checkbox(form_values, errors, "compare_policies")
    comparison_only = _checkbox(form_values, errors, "comparison_only")
    include_provenance = _checkbox(form_values, errors, "include_provenance")
    if compare_policies and multi_step_count is None:
        _add_error(
            errors,
            "compare_policies",
            "Policy Comparison requires a Multi-Step count.",
        )
    if comparison_only and not compare_policies:
        _add_error(
            errors,
            "comparison_only",
            "Comparison-only presentation requires Policy Comparison.",
        )

    completed_cards = tuple(card for trick in completed_tricks for card in trick.cards)
    exclusive_zones = [
        CardZoneSelectionV1("hand", hand),
        CardZoneSelectionV1("skat", skat),
        CardZoneSelectionV1("completed_tricks", completed_cards),
        CardZoneSelectionV1("current_trick", current_trick),
    ]
    if declarer_player != "me":
        exclusive_zones.append(
            CardZoneSelectionV1(
                "public_declarer_cards",
                public_declarer_cards,
            )
        )
    for conflict in find_card_zone_conflicts_v1(tuple(exclusive_zones)):
        fields = ", ".join(conflict.fields)
        for field in conflict.fields:
            _add_error(
                errors,
                field,
                f"Card {conflict.card} is selected more than once across: {fields}.",
            )
    if (
        declarer_player == "me"
        and public_declarer_cards
        and set(public_declarer_cards) != set(hand)
    ):
        _add_error(
            errors,
            "public_declarer_cards",
            "The local Declarer's public Cards must exactly match the local hand.",
        )

    draft = PositionFormDraftV1(
        form_version=GUIDED_POSITION_FORM_VERSION,
        form_values=form_values,
        analysis_mode=analysis_mode,
        game_type=game_type,
        player_role=player_role,
        player_position=player_position,
        declarer_player=declarer_player,
        hand_game=hand_game,
        schneider_announced=schneider_announced,
        schwarz_announced=schwarz_announced,
        ouvert=ouvert,
        bid_value=bid_value,
        matadors=matadors,
        hand=hand,
        skat=skat,
        public_declarer_cards=public_declarer_cards,
        completed_tricks=completed_tricks,
        current_trick=current_trick,
        trick_leader=trick_leader,
        declarer_points=declarer_points_value or 0,
        defender_points=defender_points_value or 0,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        actual_card_played=actual_card_played,
        analysis_method=analysis_method,
        sample_count=sample_count_value or DEFAULT_POSITION_SAMPLE_COUNT_V1,
        random_seed=(
            random_seed_value if random_seed_value is not None else DEFAULT_POSITION_RANDOM_SEED_V1
        ),
        search_seed=(
            search_seed_value if search_seed_value is not None else DEFAULT_POSITION_SEARCH_SEED_V1
        ),
        opponent_strategy=opponent_strategy,
        opponent_policy_preset=opponent_policy_preset,
        opponent_lead_policy=policy_values["opponent_lead_policy"],
        opponent_response_policy=policy_values["opponent_response_policy"],
        left_opponent_lead_policy=policy_values["left_opponent_lead_policy"],
        left_opponent_response_policy=policy_values["left_opponent_response_policy"],
        right_opponent_lead_policy=policy_values["right_opponent_lead_policy"],
        right_opponent_response_policy=policy_values["right_opponent_response_policy"],
        use_profile_presets=use_profile_presets,
        multi_step_count=multi_step_count,
        card_selection_policy=card_selection_policy,
        expected_value_sample_count=(
            expected_value_sample_count_value or DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
        ),
        strict_context=strict_context,
        compare_policies=compare_policies,
        comparison_only=comparison_only,
        include_provenance=include_provenance,
    )
    if errors:
        raise PositionFormError(draft, tuple(errors))
    return draft


def _completed_trick_document(
    trick: CompletedTrickFormValueV1,
) -> dict[str, object]:
    return {
        "cards": list(trick.cards),
        "players": list(trick.players),
        "winner_role": trick.winner_side,
        "winner_player": trick.winner_player,
    }


def _derived_hand_sizes(
    completed_tricks: list[dict[str, object]],
    current_trick: list[str],
    trick_leader: str,
) -> dict[str, int]:
    played_counts = dict.fromkeys(CONCRETE_PLAYERS, 0)
    for trick in completed_tricks:
        players = trick["players"]
        if not isinstance(players, list):
            raise ValueError("Completed Trick players are unavailable.")
        for player in players:
            played_counts[player] += 1
    for player in get_players_for_trick_leader(trick_leader)[: len(current_trick)]:
        played_counts[player] += 1
    return {player: 10 - count for player, count in played_counts.items()}


def _search_settings(draft: PositionFormDraftV1) -> dict[str, object] | None:
    if draft.analysis_method == "immediate":
        return None
    requested = get_search_budget_profile(INTERACTIVE_SEARCH_BUDGET_PROFILE)
    if draft.analysis_method in ("bounded_search", "auto"):
        return {"random_seed": draft.search_seed, **asdict(requested)}
    converted = convert_requested_search_budget_to_information_set_search_budget_v1(requested)
    settings = asdict(converted)
    settings.pop("information_set_search_budget_version")
    return {"random_seed": draft.search_seed, **settings}


def _workflow_options(draft: PositionFormDraftV1) -> dict[str, object]:
    options: dict[str, object] = {}
    optional_overrides = (
        ("opponent_strategy_override", draft.opponent_strategy),
        ("opponent_policy_preset_override", draft.opponent_policy_preset),
        ("opponent_lead_policy_override", draft.opponent_lead_policy),
        ("opponent_response_policy_override", draft.opponent_response_policy),
        ("left_opponent_lead_policy_override", draft.left_opponent_lead_policy),
        ("left_opponent_response_policy_override", draft.left_opponent_response_policy),
        ("right_opponent_lead_policy_override", draft.right_opponent_lead_policy),
        ("right_opponent_response_policy_override", draft.right_opponent_response_policy),
        ("multi_step_count", draft.multi_step_count),
        ("card_selection_policy", draft.card_selection_policy),
    )
    options.update((name, value) for name, value in optional_overrides if value is not None)
    if draft.use_profile_presets:
        options["use_profile_presets_override"] = True
    if draft.multi_step_count is not None:
        options["expected_value_sample_count"] = draft.expected_value_sample_count
    if draft.strict_context:
        options["strict_context"] = True
    if draft.compare_policies:
        options["compare_policies"] = True
    if draft.comparison_only:
        options["comparison_only"] = True
    return options


def _error_field(message: str, path: str | None = None) -> str:
    if path:
        token = path.lstrip("/").partition("/")[0]
        if token in POSITION_FORM_FIELDS_V1:
            return token
    for field in sorted(POSITION_FORM_FIELDS_V1, key=len, reverse=True):
        if field in message:
            return field
    if "Duplicate known cards" in message:
        return "hand"
    if "turn phase" in message or "next_player" in message:
        return "trick_leader"
    return "_form"


def build_guided_position_execution_v1(
    draft: PositionFormDraftV1,
) -> tuple[RequestDocumentV1, ExecutionOptionsV1]:
    """Builds one canonical Position Request and exact public execution options."""

    if type(draft) is not PositionFormDraftV1:
        raise TypeError("draft must be an exact PositionFormDraftV1.")
    try:
        declaration_kwargs = {
            field: True
            for field in (
                "hand_game",
                "schneider_announced",
                "schwarz_announced",
                "ouvert",
            )
            if getattr(draft, field)
        }
        declaration = normalize_game_declaration_values(
            game_type=draft.game_type,
            matadors=draft.matadors,
            bid_value=draft.bid_value,
            **declaration_kwargs,
        )
        completed_tricks = [_completed_trick_document(trick) for trick in draft.completed_tricks]
        current_trick = list(draft.current_trick)
        phase = normalize_turn_phase_for_position(
            trick_leader=draft.trick_leader,
            next_player=None,
            current_trick=current_trick,
            completed_tricks=completed_tricks,
        )
        validate_completed_trick_sequence(
            completed_tricks=completed_tricks,
            current_trick=current_trick,
            trick_leader=phase.trick_leader,
            player_role=draft.player_role,
            declarer_player=draft.declarer_player,
            game_type=draft.game_type,
            require_verifiable_winner_role=(draft.analysis_mode == "live_decision"),
        )
        derived_hand_sizes = _derived_hand_sizes(
            completed_tricks,
            current_trick,
            phase.trick_leader,
        )
        if len(draft.hand) != derived_hand_sizes["me"]:
            raise ValueError(
                "hand contradicts attributed play: expected "
                f"{derived_hand_sizes['me']} Cards, got {len(draft.hand)}."
            )
        left_hand_size = derived_hand_sizes["left"]
        right_hand_size = derived_hand_sizes["right"]
        for field, supplied, derived in (
            ("left_hand_size", draft.left_hand_size, left_hand_size),
            ("right_hand_size", draft.right_hand_size, right_hand_size),
        ):
            if supplied is not None and supplied != derived:
                raise ValueError(
                    f"{field} contradicts attributed play: expected {derived}, got {supplied}."
                )

        skat_visibility = "unknown"
        if draft.skat:
            skat_visibility = (
                "known_post_game"
                if draft.analysis_mode == "post_game_review"
                else "known_to_declarer"
            )
        root: dict[str, object] = {
            "game_type": draft.game_type,
            "player_role": draft.player_role,
            "declarer_player": draft.declarer_player,
            "player_position": draft.player_position,
            "trick_leader": phase.trick_leader,
            "hand": list(draft.hand),
            "current_trick": current_trick,
            "played_cards": [],
            "completed_tricks": completed_tricks,
            "declarer_points": draft.declarer_points,
            "defender_points": draft.defender_points,
            "next_player": phase.next_player,
            "skat": list(draft.skat),
            "left_hand_size": left_hand_size,
            "right_hand_size": right_hand_size,
            "sample_count": draft.sample_count,
            "random_seed": draft.random_seed,
            "use_basic_opponent_strategy": True,
            "analysis_mode": draft.analysis_mode,
            "skat_visibility": skat_visibility,
            "game_end_reason": "not_ended",
            "hand_game": declaration["hand_game"],
            "ouvert": declaration["ouvert"],
            "schneider_announced": declaration["schneider_announced"],
            "schwarz_announced": declaration["schwarz_announced"],
        }
        if draft.matadors is not None:
            root["matadors"] = draft.matadors
        if draft.bid_value is not None:
            root["bid_value"] = draft.bid_value
        if draft.public_declarer_cards:
            root["public_declarer_cards"] = list(draft.public_declarer_cards)
        if draft.actual_card_played is not None:
            root["actual_card_played"] = draft.actual_card_played

        method = next(
            method
            for method in POSITION_ANALYSIS_METHODS_V1
            if method.form_value == draft.analysis_method
        )
        search_settings = _search_settings(draft)
        if method.recommendation_method is not None:
            root["recommendation_method"] = method.recommendation_method
        if draft.analysis_method in ("bounded_search", "auto"):
            root["bounded_search_settings"] = search_settings
        elif draft.analysis_method == "information_set_search":
            root["information_set_search_settings"] = search_settings

        # The Product validator remains authoritative for legality and policy.
        build_position_from_document(root)
        request = parse_request(root)
        execution_options = ExecutionOptionsV1(
            validate_output=True,
            include_provenance=draft.include_provenance,
            workflow_options=_workflow_options(draft),
        )
        return request, execution_options
    except PositionFormError:
        raise
    except SkatMindError as error:
        field = _error_field(error.message, error.path)
        raise PositionFormError(
            draft,
            (FormFieldErrorV1(field=field, message=error.message),),
        ) from error
    except ValueError as error:
        message = str(error)
        field = _error_field(message)
        raise PositionFormError(
            draft,
            (FormFieldErrorV1(field=field, message=message),),
        ) from error
