from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from skatmind.api.v1 import ExecutionOptionsV1, RequestDocumentV1, parse_request
from skatmind.deck import get_full_deck
from skatmind.game_declaration import (
    VALID_DECLARATION_GAME_TYPES,
    GameDeclaration,
    normalize_game_declaration_values,
)
from skatmind.input_validation import MAX_SAMPLE_COUNT
from skatmind.observed_game_trace import ObservedPlayV1, validate_observed_game_trace_v1
from skatmind.rules import get_legal_cards
from skatmind.search_budget_profiles import HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
from skatmind.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

HISTORICAL_FORM_STEPS = (
    "players",
    "deal",
    "declaration",
    "discards",
    "play",
    "options",
    "review",
)
HISTORICAL_PLAYER_IDS = (
    "frontend-forehand",
    "frontend-middlehand",
    "frontend-rearhand",
)
HISTORICAL_SEATS = ("forehand", "middlehand", "rearhand")
HISTORICAL_GAME_ID = "frontend-historical-review"
HISTORICAL_GAME_END_REASON = "normal_completion"
HISTORICAL_PLAY_COUNT = 30


@dataclass(frozen=True, slots=True)
class HistoricalFormPlayerV1:
    player_id: str
    seat: str
    player_label: str | None = None
    initial_hand: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HistoricalFormDeclarationV1:
    game_type: str
    declarer_player_id: str
    bid_value: int
    hand_game: bool = False
    ouvert: bool = False
    schneider_announced: bool = False
    schwarz_announced: bool = False


@dataclass(frozen=True, slots=True)
class HistoricalFormPlayV1:
    player_id: str
    card: str


@dataclass(frozen=True, slots=True)
class HistoricalFormCompletedTrickV1:
    trick_number: int
    leader_player_id: str
    plays: tuple[HistoricalFormPlayV1, ...]
    winner_player_id: str
    next_leader_player_id: str


def _validate_search_family_selection(options: HistoricalFormOptionsV1) -> None:
    classic = options.search_review or options.replay_coaching
    information_set = (
        options.information_set_search_review or options.information_set_replay_coaching
    )
    if classic and information_set:
        raise ValueError(
            "Classic Search Review/Replay Coaching cannot be combined with the "
            "Information-set Search family."
        )


@dataclass(frozen=True, slots=True)
class HistoricalFormOptionsV1:
    decision_snapshots: bool = False
    immediate_review: bool = False
    search_review: bool = False
    information_set_search_review: bool = False
    replay_coaching: bool = False
    information_set_replay_coaching: bool = False
    tactical: bool = False
    include_provenance: bool = False
    search_seed: int = 0
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    immediate_base_random_seed: int = 0

    def __post_init__(self) -> None:
        for name in (
            "decision_snapshots",
            "immediate_review",
            "search_review",
            "information_set_search_review",
            "replay_coaching",
            "information_set_replay_coaching",
            "tactical",
            "include_provenance",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean.")
        for name in ("search_seed", "immediate_base_random_seed"):
            if type(getattr(self, name)) is not int:
                raise ValueError(f"{name} must be an integer.")
        if (
            type(self.immediate_sample_count) is not int
            or not 1 <= self.immediate_sample_count <= MAX_SAMPLE_COUNT
        ):
            raise ValueError(
                f"immediate_sample_count must be from 1 through {MAX_SAMPLE_COUNT}."
            )
        _validate_search_family_selection(self)


@dataclass(frozen=True, slots=True)
class HistoricalFormDraftV1:
    step: int
    players: tuple[HistoricalFormPlayerV1, ...]
    skat: tuple[str, ...] = ()
    declaration: HistoricalFormDeclarationV1 | None = None
    discarded_cards: tuple[str, ...] = ()
    plays: tuple[HistoricalFormPlayV1, ...] = ()
    options: HistoricalFormOptionsV1 = HistoricalFormOptionsV1()

    def __post_init__(self) -> None:
        if type(self.step) is not int or not 1 <= self.step <= len(HISTORICAL_FORM_STEPS):
            raise ValueError("step must identify one of the seven Historical form steps.")
        if type(self.players) is not tuple or len(self.players) != 3:
            raise ValueError("players must contain exactly three immutable form players.")
        if any(type(player) is not HistoricalFormPlayerV1 for player in self.players):
            raise ValueError("players must contain exact Historical form players.")
        if tuple(player.player_id for player in self.players) != HISTORICAL_PLAYER_IDS:
            raise ValueError("players must use the deterministic frontend player IDs.")
        if tuple(player.seat for player in self.players) != HISTORICAL_SEATS:
            raise ValueError("players must use canonical seat order.")
        if type(self.skat) is not tuple or type(self.discarded_cards) is not tuple:
            raise ValueError("Card collections must be immutable tuples.")
        if type(self.plays) is not tuple or any(
            type(play) is not HistoricalFormPlayV1 for play in self.plays
        ):
            raise ValueError("plays must contain immutable Historical form plays.")
        if (
            self.declaration is not None
            and type(self.declaration) is not HistoricalFormDeclarationV1
        ):
            raise ValueError("declaration must be an exact Historical form declaration.")
        if type(self.options) is not HistoricalFormOptionsV1:
            raise ValueError("options must be exact Historical form options.")

    @property
    def step_name(self) -> str:
        return HISTORICAL_FORM_STEPS[self.step - 1]


@dataclass(frozen=True, slots=True)
class HistoricalPlayViewV1:
    played_card_count: int
    trick_number: int
    acting_player_id: str | None
    legal_cards: tuple[str, ...]
    current_trick_leader_player_id: str
    current_trick_plays: tuple[HistoricalFormPlayV1, ...]
    completed_tricks: tuple[HistoricalFormCompletedTrickV1, ...]
    last_trick_winner_player_id: str | None
    next_leader_player_id: str | None
    is_complete: bool


@dataclass(frozen=True, slots=True)
class HistoricalOptionsSummaryV1:
    always_included: tuple[str, ...]
    selected_outputs: tuple[str, ...]
    implied_prerequisites: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _DerivedPlayState:
    remaining_hands: tuple[tuple[str, tuple[str, ...]], ...]
    current_leader_player_id: str
    next_player_id: str
    current_trick: tuple[HistoricalFormPlayV1, ...]
    completed_tricks: tuple[HistoricalFormCompletedTrickV1, ...]


def create_historical_form_draft_v1() -> HistoricalFormDraftV1:
    """Creates the immutable first step of one guided Historical form."""

    players = tuple(
        HistoricalFormPlayerV1(player_id=player_id, seat=seat)
        for player_id, seat in zip(HISTORICAL_PLAYER_IDS, HISTORICAL_SEATS, strict=True)
    )
    return HistoricalFormDraftV1(step=1, players=players)


def _require_step(draft: HistoricalFormDraftV1, expected: int) -> None:
    if type(draft) is not HistoricalFormDraftV1:
        raise ValueError("draft must be an exact Historical form draft.")
    if draft.step != expected:
        raise ValueError(
            f"Historical form step {expected} ({HISTORICAL_FORM_STEPS[expected - 1]}) "
            f"is required; current step is {draft.step} ({draft.step_name})."
        )


def _optional_label(value: object, name: str) -> str | None:
    if value in (None, ""):
        return None
    if type(value) is not str or value != value.strip():
        raise ValueError(f"{name} must be non-padded text or omitted.")
    return value


def update_historical_players_v1(
    draft: HistoricalFormDraftV1,
    *,
    forehand_label: str | None = None,
    middlehand_label: str | None = None,
    rearhand_label: str | None = None,
) -> HistoricalFormDraftV1:
    """Stores optional labels without changing deterministic player identity."""

    _require_step(draft, 1)
    labels = (
        _optional_label(forehand_label, "forehand_label"),
        _optional_label(middlehand_label, "middlehand_label"),
        _optional_label(rearhand_label, "rearhand_label"),
    )
    supplied_labels = tuple(label for label in labels if label is not None)
    if len(supplied_labels) != len(set(supplied_labels)):
        raise ValueError("Non-empty Player display labels must be unique.")
    players = tuple(
        replace(player, player_label=label)
        for player, label in zip(draft.players, labels, strict=True)
    )
    return replace(draft, step=2, players=players)


def _card_tuple(value: object, name: str, expected_count: int) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{name} must be a Card list or tuple.")
    cards = tuple(value)
    if len(cards) != expected_count:
        raise ValueError(f"{name} must contain exactly {expected_count} cards.")
    if any(type(card) is not str for card in cards):
        raise ValueError(f"{name} must contain only Card strings.")
    invalid = tuple(card for card in cards if card not in get_full_deck())
    if invalid:
        raise ValueError(f"{name} contains invalid cards: {list(invalid)}.")
    if len(cards) != len(set(cards)):
        raise ValueError(f"{name} contains duplicate cards.")
    return cards


def update_historical_deal_v1(
    draft: HistoricalFormDraftV1,
    *,
    forehand_hand: Sequence[str],
    middlehand_hand: Sequence[str],
    rearhand_hand: Sequence[str],
    skat: Sequence[str],
) -> HistoricalFormDraftV1:
    """Stores one exact 10/10/10/2 deal over the canonical 32-card deck."""

    _require_step(draft, 2)
    hands = (
        _card_tuple(forehand_hand, "forehand_hand", 10),
        _card_tuple(middlehand_hand, "middlehand_hand", 10),
        _card_tuple(rearhand_hand, "rearhand_hand", 10),
    )
    skat_cards = _card_tuple(skat, "skat", 2)
    dealt_cards = tuple(card for hand in hands for card in hand) + skat_cards
    if len(dealt_cards) != len(set(dealt_cards)):
        raise ValueError("The initial hands and skat contain duplicate cards.")
    if set(dealt_cards) != set(get_full_deck()):
        missing = sorted(set(get_full_deck()).difference(dealt_cards))
        raise ValueError(
            f"The initial hands and skat must form the canonical deck; missing={missing}."
        )
    players = tuple(
        replace(player, initial_hand=hand)
        for player, hand in zip(draft.players, hands, strict=True)
    )
    unchanged = (
        tuple(player.initial_hand for player in draft.players) == hands
        and draft.skat == skat_cards
    )
    return replace(
        draft,
        step=3,
        players=players,
        skat=skat_cards,
        declaration=draft.declaration if unchanged else None,
        discarded_cards=draft.discarded_cards if unchanged else (),
        plays=draft.plays if unchanged else (),
    )


def update_historical_declaration_v1(
    draft: HistoricalFormDraftV1,
    *,
    declarer_player_id: str,
    game_type: str,
    bid_value: int,
    hand_game: bool = False,
    ouvert: bool = False,
    schneider_announced: bool = False,
    schwarz_announced: bool = False,
) -> HistoricalFormDraftV1:
    """Stores declaration input; final dependency validation stays at the public boundary."""

    _require_step(draft, 3)
    if declarer_player_id not in HISTORICAL_PLAYER_IDS:
        raise ValueError("declarer_player_id must reference one deterministic form player.")
    if game_type not in VALID_DECLARATION_GAME_TYPES:
        raise ValueError(f"game_type must be one of {VALID_DECLARATION_GAME_TYPES}.")
    if type(bid_value) is not int or bid_value <= 0:
        raise ValueError("bid_value must be a positive integer.")
    boolean_values = {
        "hand_game": hand_game,
        "ouvert": ouvert,
        "schneider_announced": schneider_announced,
        "schwarz_announced": schwarz_announced,
    }
    for name, value in boolean_values.items():
        if type(value) is not bool:
            raise ValueError(f"{name} must be a boolean.")
    normalized = normalize_game_declaration_values(
        game_type=game_type,
        bid_value=bid_value,
        **boolean_values,
    )
    declaration = HistoricalFormDeclarationV1(
        game_type=str(normalized["game_type"]),
        declarer_player_id=declarer_player_id,
        bid_value=bid_value,
        hand_game=bool(normalized["hand_game"]),
        ouvert=bool(normalized["ouvert"]),
        schneider_announced=bool(normalized["schneider_announced"]),
        schwarz_announced=bool(normalized["schwarz_announced"]),
    )
    unchanged = declaration == draft.declaration
    return replace(
        draft,
        step=4,
        declaration=declaration,
        discarded_cards=draft.discarded_cards if unchanged else (),
        plays=draft.plays if unchanged else (),
    )


def update_historical_discards_v1(
    draft: HistoricalFormDraftV1,
    discarded_cards: Sequence[str],
) -> HistoricalFormDraftV1:
    """Stores zero Hand-game discards or exactly two pickup-game discards."""

    _require_step(draft, 4)
    declaration = draft.declaration
    if declaration is None:
        raise ValueError("A declaration is required before discards.")
    expected_count = 0 if declaration.hand_game else 2
    cards = _card_tuple(discarded_cards, "discarded_cards", expected_count)
    if not declaration.hand_game:
        declarer = next(
            player for player in draft.players if player.player_id == declaration.declarer_player_id
        )
        available_cards = set((*declarer.initial_hand, *draft.skat))
        unavailable = sorted(set(cards).difference(available_cards))
        if unavailable:
            raise ValueError(
                "discarded_cards must belong to the declarer after pickup; "
                f"unavailable={unavailable}."
            )
    unchanged = cards == draft.discarded_cards
    return replace(
        draft,
        step=6 if unchanged and len(draft.plays) == HISTORICAL_PLAY_COUNT else 5,
        discarded_cards=cards,
        plays=draft.plays if unchanged else (),
    )


def _playable_hands(draft: HistoricalFormDraftV1) -> dict[str, list[str]]:
    declaration = draft.declaration
    if declaration is None:
        raise ValueError("A declaration is required before play.")
    hands = {player.player_id: list(player.initial_hand) for player in draft.players}
    if not declaration.hand_game:
        declarer_hand = hands[declaration.declarer_player_id]
        declarer_hand.extend(draft.skat)
        for card in draft.discarded_cards:
            declarer_hand.remove(card)
    return hands


def _derive_play_state(draft: HistoricalFormDraftV1) -> _DerivedPlayState:
    declaration = draft.declaration
    if declaration is None:
        raise ValueError("A declaration is required before play.")
    declaration_value = GameDeclaration(
        declaration.game_type,
        hand_game=declaration.hand_game,
        ouvert=declaration.ouvert,
        schneider_announced=declaration.schneider_announced,
        schwarz_announced=declaration.schwarz_announced,
        bid_value=declaration.bid_value,
    )
    observed_plays = tuple(
        ObservedPlayV1(
            decision_index=index,
            player_id=play.player_id,
            card=play.card,
            decision_timecode=None,
        )
        for index, play in enumerate(draft.plays, start=1)
    )
    initial_hands = _playable_hands(draft)
    trace = None
    for player in draft.players:
        trace = validate_observed_game_trace_v1(
            plays=observed_plays,
            seat_order_player_ids=HISTORICAL_PLAYER_IDS,
            perspective_player_id=player.player_id,
            perspective_initial_hand=player.initial_hand,
            perspective_playable_hand=tuple(initial_hands[player.player_id]),
            declarer_player_id=declaration.declarer_player_id,
            declaration=declaration_value,
            original_skat=draft.skat,
            discarded_cards=draft.discarded_cards,
            game_timecode=None,
        )
    assert trace is not None

    hands = initial_hands
    for play in draft.plays:
        hands[play.player_id].remove(play.card)
    completed_tricks = tuple(
        HistoricalFormCompletedTrickV1(
            trick_number=index + 1,
            leader_player_id=draft.plays[index * 3].player_id,
            plays=draft.plays[index * 3 : index * 3 + 3],
            winner_player_id=trace.winner_player_ids[index],
            next_leader_player_id=trace.winner_player_ids[index],
        )
        for index in range(trace.completed_trick_count)
    )
    current_trick = (
        draft.plays[-trace.current_trick_play_count :]
        if trace.current_trick_play_count
        else ()
    )
    leader_player_id = (
        current_trick[0].player_id if current_trick else trace.next_player_id
    )
    return _DerivedPlayState(
        remaining_hands=tuple(
            (player_id, tuple(hands[player_id])) for player_id in HISTORICAL_PLAYER_IDS
        ),
        current_leader_player_id=leader_player_id,
        next_player_id=trace.next_player_id,
        current_trick=tuple(current_trick),
        completed_tricks=completed_tricks,
    )


def build_historical_play_view_v1(draft: HistoricalFormDraftV1) -> HistoricalPlayViewV1:
    """Derives the current actor, legal cards, winners, and next leader."""

    if type(draft) is not HistoricalFormDraftV1 or draft.step < 5:
        raise ValueError("The Historical form must reach the play step first.")
    state = _derive_play_state(draft)
    is_complete = len(draft.plays) == HISTORICAL_PLAY_COUNT
    if is_complete:
        acting_player_id = None
        legal_cards: tuple[str, ...] = ()
    else:
        acting_player_id = state.next_player_id
        hand = dict(state.remaining_hands)[acting_player_id]
        legal_cards = tuple(
            get_legal_cards(
                list(hand),
                [play.card for play in state.current_trick],
                draft.declaration.game_type,
            )
        )
    last_winner = state.completed_tricks[-1].winner_player_id if state.completed_tricks else None
    return HistoricalPlayViewV1(
        played_card_count=len(draft.plays),
        trick_number=min(len(state.completed_tricks) + 1, 10),
        acting_player_id=acting_player_id,
        legal_cards=legal_cards,
        current_trick_leader_player_id=state.current_leader_player_id,
        current_trick_plays=state.current_trick,
        completed_tricks=state.completed_tricks,
        last_trick_winner_player_id=last_winner,
        next_leader_player_id=(state.current_leader_player_id if not state.current_trick else None),
        is_complete=is_complete,
    )


def append_historical_play_v1(
    draft: HistoricalFormDraftV1,
    card: str,
) -> HistoricalFormDraftV1:
    """Appends exactly one legal Card for the derived acting player."""

    _require_step(draft, 5)
    if len(draft.plays) >= HISTORICAL_PLAY_COUNT:
        raise ValueError("A normal-completion game contains exactly 30 plays.")
    view = build_historical_play_view_v1(draft)
    if type(card) is not str or card not in view.legal_cards:
        raise ValueError(
            f"Card {card!r} is illegal for {view.acting_player_id}; "
            f"legal cards are {list(view.legal_cards)}."
        )
    plays = (*draft.plays, HistoricalFormPlayV1(view.acting_player_id, card))
    next_step = 6 if len(plays) == HISTORICAL_PLAY_COUNT else 5
    return replace(draft, step=next_step, plays=plays)


def undo_historical_play_v1(draft: HistoricalFormDraftV1) -> HistoricalFormDraftV1:
    """Removes only the final chronological Card play."""

    if type(draft) is not HistoricalFormDraftV1 or draft.step < 5:
        raise ValueError("The Historical form must reach the play step first.")
    if not draft.plays:
        raise ValueError("There is no Historical play to undo.")
    return replace(draft, step=5, plays=draft.plays[:-1])


def update_historical_options_v1(
    draft: HistoricalFormDraftV1,
    *,
    decision_snapshots: bool = False,
    immediate_review: bool = False,
    search_review: bool = False,
    information_set_search_review: bool = False,
    replay_coaching: bool = False,
    information_set_replay_coaching: bool = False,
    tactical: bool = False,
    include_provenance: bool = False,
    search_seed: int = 0,
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT,
    immediate_base_random_seed: int = 0,
) -> HistoricalFormDraftV1:
    """Stores optional review output and deterministic advanced settings."""

    _require_step(draft, 6)
    options = HistoricalFormOptionsV1(
        decision_snapshots=decision_snapshots,
        immediate_review=immediate_review,
        search_review=search_review,
        information_set_search_review=information_set_search_review,
        replay_coaching=replay_coaching,
        information_set_replay_coaching=information_set_replay_coaching,
        tactical=tactical,
        include_provenance=include_provenance,
        search_seed=search_seed,
        immediate_sample_count=immediate_sample_count,
        immediate_base_random_seed=immediate_base_random_seed,
    )
    return replace(draft, step=7, options=options)


def go_back_historical_form_v1(draft: HistoricalFormDraftV1) -> HistoricalFormDraftV1:
    """Returns a new draft at the preceding one of exactly seven steps."""

    if type(draft) is not HistoricalFormDraftV1:
        raise ValueError("draft must be an exact Historical form draft.")
    if draft.step == 1:
        raise ValueError("The first Historical form step has no preceding step.")
    return replace(draft, step=draft.step - 1)


def _declaration_document(declaration: HistoricalFormDeclarationV1) -> dict[str, object]:
    document: dict[str, object] = {
        "game_type": declaration.game_type,
        "hand_game": declaration.hand_game,
        "ouvert": declaration.ouvert,
        "bid_value": declaration.bid_value,
    }
    if declaration.game_type != "null":
        document.update(
            schneider_announced=declaration.schneider_announced,
            schwarz_announced=declaration.schwarz_announced,
        )
    else:
        if declaration.schneider_announced:
            document["schneider_announced"] = True
        if declaration.schwarz_announced:
            document["schwarz_announced"] = True
    return document


def build_historical_request_v1(draft: HistoricalFormDraftV1) -> RequestDocumentV1:
    """Builds one timestamp-free normal-completion Root through public validation."""

    if type(draft) is not HistoricalFormDraftV1:
        raise ValueError("draft must be an exact Historical form draft.")
    if len(draft.plays) != HISTORICAL_PLAY_COUNT:
        raise ValueError("A Historical normal-completion request requires exactly 30 plays.")
    declaration = draft.declaration
    if declaration is None:
        raise ValueError("A declaration is required.")
    state = _derive_play_state(draft)
    if state.current_trick or len(state.completed_tricks) != 10:
        raise ValueError("A Historical normal-completion request requires exactly ten tricks.")
    if any(cards for _player_id, cards in state.remaining_hands):
        raise ValueError("A Historical normal-completion request must use every playable Card.")
    players = []
    for player in draft.players:
        player_document: dict[str, object] = {
            "player_id": player.player_id,
            "seat": player.seat,
            "initial_hand": list(player.initial_hand),
        }
        if player.player_label is not None:
            player_document["player_label"] = player.player_label
        players.append(player_document)
    historical_document = {
        "schema_version": 1,
        "game_id": HISTORICAL_GAME_ID,
        "players": players,
        "skat": list(draft.skat),
        "declarer_player_id": declaration.declarer_player_id,
        "declaration": _declaration_document(declaration),
        "discarded_cards": list(draft.discarded_cards),
        "game_end_reason": HISTORICAL_GAME_END_REASON,
        "tricks": [
            {
                "trick_number": trick.trick_number,
                "leader_player_id": trick.leader_player_id,
                "plays": [{"player_id": play.player_id, "card": play.card} for play in trick.plays],
            }
            for trick in state.completed_tricks
        ],
    }
    return parse_request({"historical_game_input": historical_document})


def build_historical_execution_options_v1(
    draft: HistoricalFormDraftV1,
) -> ExecutionOptionsV1:
    """Translates selected review outputs into public Historical execution options."""

    if type(draft) is not HistoricalFormDraftV1:
        raise ValueError("draft must be an exact Historical form draft.")
    options = draft.options
    _validate_search_family_selection(options)
    workflow_options: dict[str, object] = {}
    for field_name, selected in (
        ("decision_snapshots", options.decision_snapshots),
        ("immediate_review", options.immediate_review),
        ("search_review", options.search_review),
        ("information_set_search_review", options.information_set_search_review),
        ("replay_coaching", options.replay_coaching),
        (
            "information_set_replay_coaching",
            options.information_set_replay_coaching,
        ),
        ("historical_tactical_motif_review", options.tactical),
    ):
        if selected:
            workflow_options[field_name] = True
    needs_search = (
        options.search_review
        or options.information_set_search_review
        or options.replay_coaching
        or options.information_set_replay_coaching
    )
    has_review = options.immediate_review or needs_search
    if needs_search:
        workflow_options["search_seed"] = options.search_seed
        workflow_options["search_budget_profile"] = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    if has_review:
        workflow_options["immediate_sample_count"] = options.immediate_sample_count
        workflow_options["immediate_base_random_seed"] = options.immediate_base_random_seed
    return ExecutionOptionsV1(
        include_provenance=options.include_provenance,
        workflow_options=workflow_options,
    )


def build_historical_options_summary_v1(
    draft: HistoricalFormDraftV1,
) -> HistoricalOptionsSummaryV1:
    """Returns a card-, player-, timestamp-, and seed-free option summary."""

    if type(draft) is not HistoricalFormDraftV1:
        raise ValueError("draft must be an exact Historical form draft.")
    options = draft.options
    _validate_search_family_selection(options)
    selected = tuple(
        name
        for name, enabled in (
            ("decision_snapshots", options.decision_snapshots),
            ("immediate_review", options.immediate_review),
            ("search_review", options.search_review),
            ("information_set_search_review", options.information_set_search_review),
            ("replay_coaching", options.replay_coaching),
            (
                "information_set_replay_coaching",
                options.information_set_replay_coaching,
            ),
            ("tactical", options.tactical),
            ("field_provenance", options.include_provenance),
        )
        if enabled
    )
    implied: list[str] = []
    needs_snapshots = any(
        (
            options.immediate_review,
            options.search_review,
            options.information_set_search_review,
            options.replay_coaching,
            options.information_set_replay_coaching,
            options.tactical,
        )
    )
    if needs_snapshots and not options.decision_snapshots:
        implied.append("decision_snapshots_prepared_internally")
    needs_search = (
        options.search_review
        or options.information_set_search_review
        or options.replay_coaching
        or options.information_set_replay_coaching
    )
    if needs_search:
        implied.append("immediate_comparison_prepared_internally")
    if options.replay_coaching and not options.search_review:
        implied.append("classic_search_review_prepared_for_replay_coaching")
    if options.information_set_replay_coaching and not options.information_set_search_review:
        implied.append("information_set_search_review_prepared_for_replay_coaching")
    return HistoricalOptionsSummaryV1(
        always_included=("game_result", "final_settlement"),
        selected_outputs=selected,
        implied_prerequisites=tuple(implied),
    )
