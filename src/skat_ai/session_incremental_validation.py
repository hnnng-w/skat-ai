from __future__ import annotations

from dataclasses import dataclass, replace

from skat_ai.deck import get_full_deck
from skat_ai.historical_declarer_card_exposure_continuation import (
    build_historical_declarer_card_exposure_continuation_event,
)
from skat_ai.historical_defender_open_play_continuation import (
    HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND,
    HistoricalDefenderOpenPlayContinuationEvent,
    build_historical_defender_open_play_continuation_event,
)
from skat_ai.historical_game_end import (
    HISTORICAL_NORMAL_COMPLETION,
    HistoricalDeclarerCardExposure,
    HistoricalDeclarerConcession,
    HistoricalDefenderOpenPlay,
    HistoricalGameEnd,
    HistoricalOpenCardThrow,
    build_historical_game_end,
)
from skat_ai.historical_game_event import HistoricalGameEvent
from skat_ai.historical_play_prefix import (
    HistoricalDerivedCompletedTrick,
    HistoricalIncompleteTrick,
)
from skat_ai.matador_inference import infer_matadors_from_known_ownership
from skat_ai.public_hand_constraint import canonicalize_cards
from skat_ai.rules import get_legal_cards, get_trick_points, get_trick_winner
from skat_ai.session_commands import (
    SESSION_COMMAND_ALLOWED_PHASES,
    PromoteSessionToRetrospectiveCommandV1,
    RecordSessionDealtCardCommandV1,
    RecordSessionDiscardCommandV1,
    RecordSessionPlayCommandV1,
    SessionCommandV1,
    SetSessionDeclarationCommandV1,
    SetSessionDeclarerCommandV1,
    SetSessionGameEndCommandV1,
    SetSessionGameEventCommandV1,
    SetSessionGameMetadataCommandV1,
    SetSessionPublicHandCommandV1,
    is_session_command_v1,
)
from skat_ai.session_projection import (
    SessionProjectedHandV1,
    SessionProjectionV1,
)
from skat_ai.session_validation import (
    SessionExportReadinessV1,
    SessionValidationDiagnosticV1,
    SessionValidationResultV1,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class SessionProjectionApplicationV1:
    """One candidate projection update or deterministic rejection diagnostics."""

    projection: SessionProjectionV1 | None
    diagnostics: tuple[SessionValidationDiagnosticV1, ...]

    def __post_init__(self) -> None:
        if (self.projection is None) == (not self.diagnostics):
            raise ValueError(
                "A projection application must contain either a projection or diagnostics."
            )
        if any(not diagnostic.blocks_command for diagnostic in self.diagnostics):
            raise ValueError("Projection rejection diagnostics must block the Command.")
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))


def _command_diagnostic(
    code: str,
    path: str,
    message: str,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code=code,
        path=path,
        message=message,
        severity="error",
        blocks_command=True,
        blocks_position_export=False,
        blocks_historical_export=False,
    )


def _rejected(
    code: str,
    path: str,
    message: str,
) -> SessionProjectionApplicationV1:
    return SessionProjectionApplicationV1(
        projection=None,
        diagnostics=(_command_diagnostic(code, path, message),),
    )


def _rejected_diagnostics(
    diagnostics: tuple[SessionValidationDiagnosticV1, ...],
) -> SessionProjectionApplicationV1:
    return SessionProjectionApplicationV1(
        projection=None,
        diagnostics=diagnostics,
    )


def _applied(projection: SessionProjectionV1) -> SessionProjectionApplicationV1:
    return SessionProjectionApplicationV1(projection=projection, diagnostics=())


def _hands_to_dict(
    hands: tuple[SessionProjectedHandV1, ...],
) -> dict[str, list[str]]:
    return {player_id: list(cards) for player_id, cards in hands}


def _ordered_hands(
    projection: SessionProjectionV1,
    hands: dict[str, list[str]],
) -> tuple[SessionProjectedHandV1, ...]:
    return tuple(
        (player_id, canonicalize_cards(tuple(hands[player_id])))
        for player_id in projection.player_ids
        if player_id in hands
    )


def _derive_remaining_known_hands(
    projection: SessionProjectionV1,
) -> tuple[SessionProjectedHandV1, ...]:
    hands = _hands_to_dict(projection.initial_known_hands)
    if (
        projection.declaration is not None
        and not projection.declaration.hand_game
        and projection.declarer_player_id in hands
    ):
        hands[projection.declarer_player_id].extend(projection.known_skat)
    for card in projection.discarded_cards:
        for hand in hands.values():
            if card in hand:
                hand.remove(card)
                break
    for player_id, card in projection.plays:
        hand = hands.get(player_id)
        if hand is not None and card in hand:
            hand.remove(card)
    return _ordered_hands(projection, hands)


def _refresh_remaining_hands(
    projection: SessionProjectionV1,
) -> SessionProjectionV1:
    return replace(
        projection,
        remaining_known_hands=_derive_remaining_known_hands(projection),
    )


def _is_complete_retrospective_deal(projection: SessionProjectionV1) -> bool:
    hands = _hands_to_dict(projection.initial_known_hands)
    if set(hands) != set(projection.player_ids):
        return False
    if any(len(cards) != 10 for cards in hands.values()):
        return False
    if len(projection.known_skat) != 2:
        return False
    assigned_cards = [
        *(card for cards in hands.values() for card in cards),
        *projection.known_skat,
    ]
    return len(assigned_cards) == 32 and set(assigned_cards) == set(get_full_deck())


def _is_mode_deal_complete(projection: SessionProjectionV1) -> bool:
    if projection.capture_mode == "retrospective":
        return _is_complete_retrospective_deal(projection)
    local_hand = projection.initial_hand_for(projection.local_player_id or "")
    return local_hand is not None and len(local_hand) == 10


def _advance_after_deal(projection: SessionProjectionV1) -> SessionProjectionV1:
    if projection.phase not in {"setup", "deal"}:
        return projection
    phase = "declaration" if _is_mode_deal_complete(projection) else "deal"
    return replace(projection, phase=phase)


def _advance_after_declaration(
    projection: SessionProjectionV1,
) -> SessionProjectionV1:
    if projection.declarer_player_id is None or projection.declaration is None:
        return projection
    if projection.declaration.hand_game or (
        projection.capture_mode == "live"
        and projection.declarer_player_id != projection.local_player_id
    ):
        return replace(
            projection,
            phase="play",
            next_player_id=projection.player_ids[0],
        )
    return replace(projection, phase="skat_and_discard")


def _validate_supplied_matadors(
    projection: SessionProjectionV1,
) -> SessionValidationDiagnosticV1 | None:
    declaration = projection.declaration
    if declaration is None or declaration.matadors is None:
        return None
    if declaration.game_type == "null":
        return _command_diagnostic(
            "information_policy_violation",
            "/command/declaration/matadors",
            "Concrete Matadors require a known Declarer and verifiable ownership.",
        )
    if projection.declarer_player_id is None:
        if projection.capture_mode == "retrospective" and _is_complete_retrospective_deal(
            projection
        ):
            return None
        return _command_diagnostic(
            "information_policy_violation",
            "/command/declaration/matadors",
            "Concrete Matadors require a known Declarer and verifiable ownership.",
        )

    declarer_player_id = projection.declarer_player_id
    if projection.capture_mode == "retrospective":
        if not _is_complete_retrospective_deal(projection):
            return _command_diagnostic(
                "missing_required_value",
                "/command/declaration/matadors",
                "Retrospective Matador validation requires the exact complete Deal.",
            )
        declarer_owned = [
            *(projection.initial_hand_for(declarer_player_id) or ()),
            *projection.known_skat,
        ]
        non_declarer_owned = [
            card
            for player_id, cards in projection.initial_known_hands
            if player_id != declarer_player_id
            for card in cards
        ]
    else:
        if declarer_player_id != projection.local_player_id:
            return _command_diagnostic(
                "information_policy_violation",
                "/command/declaration/matadors",
                "A Live Defender cannot supply unverifiable concrete Matadors.",
            )
        declarer_owned = list(projection.initial_hand_for(declarer_player_id) or ())
        declarer_owned.extend(projection.known_skat)
        non_declarer_owned = [
            card
            for player_id, cards in projection.initial_known_hands
            if player_id != declarer_player_id
            for card in cards
        ]

    inferred = infer_matadors_from_known_ownership(
        game_type=declaration.game_type,
        declarer_owned_cards=declarer_owned,
        non_declarer_owned_cards=non_declarer_owned,
    )
    if inferred is None:
        return _command_diagnostic(
            "information_policy_violation",
            "/command/declaration/matadors",
            "The supplied Matadors cannot be verified from available ownership facts.",
        )
    if inferred != declaration.matadors:
        return _command_diagnostic(
            "declaration_violation",
            "/command/declaration/matadors",
            "The supplied Matadors conflict with exact known ownership.",
        )
    return None


def _apply_metadata(
    projection: SessionProjectionV1,
    command: SetSessionGameMetadataCommandV1,
) -> SessionProjectionApplicationV1:
    diagnostics = []
    if command.game_id is not None and projection.game_id is not None:
        diagnostics.append(
            _command_diagnostic(
                "invalid_value",
                "/command/game_id",
                "game_id may be recorded only once.",
            )
        )
    if command.played_at is not None and projection.played_at is not None:
        diagnostics.append(
            _command_diagnostic(
                "invalid_value",
                "/command/played_at",
                "played_at may be recorded only once.",
            )
        )
    if diagnostics:
        return _rejected_diagnostics(tuple(diagnostics))
    return _applied(
        replace(
            projection,
            game_id=command.game_id or projection.game_id,
            played_at=command.played_at or projection.played_at,
        )
    )


def _apply_dealt_card(
    projection: SessionProjectionV1,
    command: RecordSessionDealtCardCommandV1,
) -> SessionProjectionApplicationV1:
    if command.destination == "player_hand" and command.player_id not in projection.player_ids:
        return _rejected(
            "player_reference_violation",
            "/command/player_id",
            "player_id must reference a Session Player.",
        )
    assigned_cards = {
        *(card for _, cards in projection.initial_known_hands for card in cards),
        *projection.known_skat,
    }
    if command.card in assigned_cards:
        return _rejected(
            "card_identity_violation",
            "/command/card",
            "The Card is already assigned in the initial Deal.",
        )

    if projection.capture_mode == "live":
        if command.destination == "player_hand":
            if command.player_id != projection.local_player_id:
                return _rejected(
                    "information_policy_violation",
                    "/command/player_id",
                    "A Live Session may record only the local Player's concrete hand.",
                )
        elif not (
            projection.phase == "skat_and_discard"
            and projection.declarer_player_id == projection.local_player_id
            and projection.declaration is not None
            and not projection.declaration.hand_game
        ):
            return _rejected(
                "information_policy_violation",
                "/command/destination",
                "A Live Session may record the Skat only for the local Declarer "
                "during Skat and Discard capture.",
            )

    candidate = projection
    if command.destination == "player_hand":
        hands = _hands_to_dict(candidate.initial_known_hands)
        hand = hands.setdefault(command.player_id or "", [])
        if len(hand) >= 10:
            return _rejected(
                "card_identity_violation",
                "/command/card",
                "A Player's initial hand cannot contain more than ten Cards.",
            )
        hand.append(command.card)
        candidate = replace(
            candidate,
            initial_known_hands=_ordered_hands(candidate, hands),
        )
    else:
        if len(candidate.known_skat) >= 2:
            return _rejected(
                "card_identity_violation",
                "/command/card",
                "The Skat cannot contain more than two Cards.",
            )
        candidate = replace(
            candidate,
            known_skat=(*candidate.known_skat, command.card),
        )
    candidate = _refresh_remaining_hands(candidate)

    if (
        candidate.capture_mode == "retrospective"
        and _is_complete_retrospective_deal(candidate)
        and candidate.declaration is not None
        and candidate.declaration.matadors is not None
    ):
        diagnostic = _validate_supplied_matadors(candidate)
        if diagnostic is not None:
            return SessionProjectionApplicationV1(
                projection=None,
                diagnostics=(diagnostic,),
            )
    return _applied(_advance_after_deal(candidate))


def _require_retrospective_deal_before_declaration(
    projection: SessionProjectionV1,
) -> SessionProjectionApplicationV1 | None:
    if projection.capture_mode == "retrospective" and not _is_complete_retrospective_deal(
        projection
    ):
        return _rejected(
            "missing_required_value",
            "/command",
            "Retrospective Declaration capture requires the exact complete Deal.",
        )
    return None


def _apply_declarer(
    projection: SessionProjectionV1,
    command: SetSessionDeclarerCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.declarer_player_id is not None:
        return _rejected(
            "declaration_violation",
            "/command/declarer_player_id",
            "The Declarer may be recorded only once.",
        )
    if command.declarer_player_id not in projection.player_ids:
        return _rejected(
            "player_reference_violation",
            "/command/declarer_player_id",
            "declarer_player_id must reference a Session Player.",
        )
    deal_rejection = _require_retrospective_deal_before_declaration(projection)
    if deal_rejection is not None:
        return deal_rejection
    candidate = replace(
        projection,
        declarer_player_id=command.declarer_player_id,
    )
    diagnostic = _validate_supplied_matadors(candidate)
    if diagnostic is not None:
        return SessionProjectionApplicationV1(
            projection=None,
            diagnostics=(diagnostic,),
        )
    return _applied(_advance_after_declaration(_refresh_remaining_hands(candidate)))


def _apply_declaration(
    projection: SessionProjectionV1,
    command: SetSessionDeclarationCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.declaration is not None:
        return _rejected(
            "declaration_violation",
            "/command/declaration",
            "The Declaration may be recorded only once.",
        )
    deal_rejection = _require_retrospective_deal_before_declaration(projection)
    if deal_rejection is not None:
        return deal_rejection
    candidate = replace(projection, declaration=command.declaration)
    diagnostic = _validate_supplied_matadors(candidate)
    if diagnostic is not None:
        return SessionProjectionApplicationV1(
            projection=None,
            diagnostics=(diagnostic,),
        )
    return _applied(_advance_after_declaration(_refresh_remaining_hands(candidate)))


def _apply_discard(
    projection: SessionProjectionV1,
    command: RecordSessionDiscardCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.declarer_player_id is None or projection.declaration is None:
        return _rejected(
            "missing_required_value",
            "/command/card",
            "Discard capture requires a complete Declarer and Declaration.",
        )
    if projection.declaration.hand_game:
        return _rejected(
            "declaration_violation",
            "/command/card",
            "Hand Games do not allow Discards.",
        )
    if (
        projection.capture_mode == "live"
        and projection.declarer_player_id != projection.local_player_id
    ):
        return _rejected(
            "information_policy_violation",
            "/command/card",
            "A Live Defender cannot record the Declarer's Discards.",
        )
    if projection.capture_mode == "retrospective" and not _is_complete_retrospective_deal(
        projection
    ):
        return _rejected(
            "missing_required_value",
            "/command/card",
            "Retrospective Discard capture requires the exact complete Deal.",
        )
    if len(projection.known_skat) != 2:
        return _rejected(
            "missing_required_value",
            "/command/card",
            "Discard capture requires the exact two-card Skat.",
        )
    if len(projection.discarded_cards) >= 2:
        return _rejected(
            "declaration_violation",
            "/command/card",
            "Exactly two Discards may be recorded.",
        )
    if command.card in projection.discarded_cards:
        return _rejected(
            "card_identity_violation",
            "/command/card",
            "The same Card cannot be discarded twice.",
        )
    if command.card in {card for _, card in projection.plays}:
        return _rejected(
            "card_identity_violation",
            "/command/card",
            "An already played Card cannot be discarded.",
        )
    declarer_cards = {
        *(projection.initial_hand_for(projection.declarer_player_id) or ()),
        *projection.known_skat,
    }
    if command.card not in declarer_cards:
        return _rejected(
            "card_ownership_violation",
            "/command/card",
            "A Discard must belong to the Declarer's hand plus Skat.",
        )

    candidate = replace(
        projection,
        discarded_cards=(*projection.discarded_cards, command.card),
    )
    candidate = _refresh_remaining_hands(candidate)
    if len(candidate.discarded_cards) == 2:
        declarer_hand = candidate.remaining_hand_for(candidate.declarer_player_id)
        if declarer_hand is None or len(declarer_hand) != 10:
            return _rejected(
                "card_ownership_violation",
                "/command/card",
                "Two Discards must derive the exact ten-card playable Declarer hand.",
            )
        candidate = replace(
            candidate,
            phase="play",
            next_player_id=candidate.player_ids[0],
        )
    return _applied(candidate)


def _next_seat_player(
    projection: SessionProjectionV1,
    player_id: str,
) -> str:
    index = projection.player_ids.index(player_id)
    return projection.player_ids[(index + 1) % 3]


def _unplayable_cards(projection: SessionProjectionV1) -> set[str]:
    cards = set(projection.discarded_cards)
    if projection.declaration is not None and projection.declaration.hand_game:
        cards.update(projection.known_skat)
    return cards


def _validate_card_owner_conflicts(
    projection: SessionProjectionV1,
    *,
    player_id: str,
    card: str,
    require_owner_membership: bool,
) -> SessionValidationDiagnosticV1 | None:
    owner_hand = projection.remaining_hand_for(player_id)
    owner_public_hand = projection.public_hand_for(player_id)
    if require_owner_membership and owner_hand is not None and card not in owner_hand:
        return _command_diagnostic(
            "card_ownership_violation",
            "/command/card",
            "The Card is not in the Player's exact remaining hand.",
        )
    if owner_public_hand is not None and card not in owner_public_hand:
        return _command_diagnostic(
            "card_ownership_violation",
            "/command/card",
            "The Card is not in the Player's exact public hand.",
        )
    for other_player_id, cards in projection.remaining_known_hands:
        if other_player_id != player_id and card in cards:
            return _command_diagnostic(
                "card_ownership_violation",
                "/command/card",
                "The Card belongs to another exact known hand.",
            )
    for other_player_id, cards in projection.exact_public_hands:
        if other_player_id != player_id and card in cards:
            return _command_diagnostic(
                "card_ownership_violation",
                "/command/card",
                "The Card belongs to another exact public hand.",
            )
    return None


def _apply_play(
    projection: SessionProjectionV1,
    command: RecordSessionPlayCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.declarer_player_id is None or projection.declaration is None:
        return _rejected(
            "missing_required_value",
            "/command",
            "Play capture requires a complete Declarer and Declaration.",
        )
    if command.player_id not in projection.player_ids:
        return _rejected(
            "player_reference_violation",
            "/command/player_id",
            "player_id must reference a Session Player.",
        )
    if command.player_id != projection.next_player_id:
        return _rejected(
            "turn_order_violation",
            "/command/player_id",
            "The Play actor does not match the derived next Player.",
        )
    if projection.played_card_count >= 30:
        return _rejected(
            "turn_order_violation",
            "/command/card",
            "A Session cannot record more than 30 Plays.",
        )
    player_play_count = sum(player_id == command.player_id for player_id, _ in projection.plays)
    if player_play_count >= 10:
        return _rejected(
            "turn_order_violation",
            "/command/player_id",
            "A Player cannot record more than ten Plays.",
        )
    if command.card in {card for _, card in projection.plays}:
        return _rejected(
            "card_identity_violation",
            "/command/card",
            "A Card cannot be played more than once.",
        )
    if command.card in _unplayable_cards(projection):
        return _rejected(
            "card_identity_violation",
            "/command/card",
            "A discarded or unplayed Hand-Skat Card cannot be played.",
        )

    exact_hand = projection.remaining_hand_for(command.player_id)
    public_hand = projection.public_hand_for(command.player_id)
    owner_diagnostic = _validate_card_owner_conflicts(
        projection,
        player_id=command.player_id,
        card=command.card,
        require_owner_membership=exact_hand is not None,
    )
    if owner_diagnostic is not None:
        return SessionProjectionApplicationV1(
            projection=None,
            diagnostics=(owner_diagnostic,),
        )
    legal_hand = exact_hand if exact_hand is not None else public_hand
    current_cards = (
        []
        if projection.incomplete_trick is None
        else [card for _, card in projection.incomplete_trick.plays]
    )
    if legal_hand is not None:
        legal_cards = get_legal_cards(
            hand=list(legal_hand),
            current_trick=current_cards,
            game_type=projection.declaration.game_type,
        )
        if command.card not in legal_cards:
            return _rejected(
                "card_ownership_violation",
                "/command/card",
                "The Play violates the existing legal-card rule.",
            )

    candidate = replace(
        projection,
        plays=(*projection.plays, (command.player_id, command.card)),
        played_card_count=projection.played_card_count + 1,
    )
    public_hands = _hands_to_dict(candidate.exact_public_hands)
    if command.player_id in public_hands:
        public_hands[command.player_id].remove(command.card)
        candidate = replace(
            candidate,
            exact_public_hands=_ordered_hands(candidate, public_hands),
        )
    candidate = _refresh_remaining_hands(candidate)

    if projection.incomplete_trick is None:
        trick_number = len(projection.completed_tricks) + 1
        leader_player_id = command.player_id
        trick_plays = ((command.player_id, command.card),)
    else:
        trick_number = projection.incomplete_trick.trick_number
        leader_player_id = projection.incomplete_trick.leader_player_id
        trick_plays = (
            *projection.incomplete_trick.plays,
            (command.player_id, command.card),
        )
    if len(trick_plays) < 3:
        next_player_id = _next_seat_player(candidate, command.player_id)
        return _applied(
            replace(
                candidate,
                incomplete_trick=HistoricalIncompleteTrick(
                    trick_number=trick_number,
                    leader_player_id=leader_player_id,
                    plays=trick_plays,
                    next_player_id=next_player_id,
                ),
                next_player_id=next_player_id,
            )
        )

    trick_cards = [card for _, card in trick_plays]
    winner_index = get_trick_winner(
        trick_cards,
        projection.declaration.game_type,
    )
    winner_player_id = trick_plays[winner_index][0]
    completed_trick = HistoricalDerivedCompletedTrick(
        trick_number=trick_number,
        leader_player_id=leader_player_id,
        plays=trick_plays,
        winner_player_id=winner_player_id,
        winner_side=(
            "declarer" if winner_player_id == projection.declarer_player_id else "defenders"
        ),
        trick_points=get_trick_points(trick_cards),
    )
    return _applied(
        replace(
            candidate,
            completed_tricks=(*candidate.completed_tricks, completed_trick),
            incomplete_trick=None,
            next_player_id=winner_player_id,
        )
    )


def _event_owner_and_cards(
    projection: SessionProjectionV1,
    event: HistoricalGameEvent,
) -> tuple[str, tuple[str, ...]]:
    if isinstance(event, HistoricalDefenderOpenPlayContinuationEvent):
        return event.exposing_defender_player_id, event.exposed_cards
    return projection.declarer_player_id or "", event.public_declarer_cards


def _validate_complete_current_hand(
    projection: SessionProjectionV1,
    *,
    owner_player_id: str,
    cards: tuple[str, ...],
    path: str,
    require_count: bool,
) -> SessionValidationDiagnosticV1 | None:
    expected_count = 10 - sum(player_id == owner_player_id for player_id, _ in projection.plays)
    if require_count and len(cards) != expected_count:
        return _command_diagnostic(
            "card_ownership_violation",
            path,
            "The supplied Cards must equal the owner's current remaining-card count.",
        )
    if set(cards).intersection(_unplayable_cards(projection)):
        return _command_diagnostic(
            "card_identity_violation",
            path,
            "The supplied Cards conflict with unplayable Skat or Discard Cards.",
        )
    if set(cards).intersection(card for _, card in projection.plays):
        return _command_diagnostic(
            "card_identity_violation",
            path,
            "The supplied Cards contain an already played Card.",
        )
    exact_hand = projection.remaining_hand_for(owner_player_id)
    if exact_hand is not None and set(cards) != set(exact_hand):
        return _command_diagnostic(
            "card_ownership_violation",
            path,
            "The supplied Cards must equal the owner's exact known remaining hand.",
        )
    public_hand = projection.public_hand_for(owner_player_id)
    if public_hand is not None and set(cards) != set(public_hand):
        return _command_diagnostic(
            "card_ownership_violation",
            path,
            "The supplied Cards must equal the owner's exact public remaining hand.",
        )
    for other_player_id, other_cards in (
        *projection.remaining_known_hands,
        *projection.exact_public_hands,
    ):
        if other_player_id != owner_player_id and set(cards).intersection(other_cards):
            return _command_diagnostic(
                "card_ownership_violation",
                path,
                "The supplied Cards conflict with another exact hand.",
            )
    return None


def _merge_exact_public_hand(
    projection: SessionProjectionV1,
    *,
    owner_player_id: str,
    cards: tuple[str, ...],
) -> tuple[SessionProjectedHandV1, ...]:
    public_hands = _hands_to_dict(projection.exact_public_hands)
    public_hands[owner_player_id] = list(cards)
    return _ordered_hands(projection, public_hands)


def _apply_public_hand(
    projection: SessionProjectionV1,
    command: SetSessionPublicHandCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.declared_ouvert_public_hand_set:
        return _rejected(
            "event_sequence_violation",
            "/command/source",
            "A Session may accept at most one declared-Ouvert public-hand Command.",
        )
    if command.player_id not in projection.player_ids:
        return _rejected(
            "player_reference_violation",
            "/command/player_id",
            "player_id must reference a Session Player.",
        )
    if projection.declarer_player_id is None or projection.declaration is None:
        return _rejected(
            "missing_required_value",
            "/command/cards",
            "A public hand requires a complete Declarer and Declaration.",
        )
    if not projection.declaration.ouvert:
        return _rejected(
            "declaration_violation",
            "/command/source",
            "declared_ouvert requires an ongoing Ouvert Declaration.",
        )
    if command.player_id != projection.declarer_player_id:
        return _rejected(
            "player_reference_violation",
            "/command/player_id",
            "The declared-Ouvert public hand must belong to the stable Declarer.",
        )
    if projection.game_end_reason is not None:
        return _rejected(
            "game_end_violation",
            "/command/cards",
            "A public hand cannot be recorded after Game End.",
        )
    diagnostic = _validate_complete_current_hand(
        projection,
        owner_player_id=command.player_id,
        cards=command.cards,
        path="/command/cards",
        require_count=True,
    )
    if diagnostic is not None:
        return SessionProjectionApplicationV1(
            projection=None,
            diagnostics=(diagnostic,),
        )
    return _applied(
        replace(
            projection,
            exact_public_hands=_merge_exact_public_hand(
                projection,
                owner_player_id=command.player_id,
                cards=command.cards,
            ),
            declared_ouvert_public_hand_set=True,
        )
    )


def _apply_game_event(
    projection: SessionProjectionV1,
    command: SetSessionGameEventCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.continuation_event is not None:
        return _rejected(
            "event_sequence_violation",
            "/command/event",
            "A Session may record at most one continuation event.",
        )
    if projection.game_end_reason is not None:
        return _rejected(
            "event_sequence_violation",
            "/command/event",
            "A continuation event cannot follow a Game End.",
        )
    if projection.declarer_player_id is None or projection.declaration is None:
        return _rejected(
            "missing_required_value",
            "/command/event",
            "A continuation event requires a complete Declarer and Declaration.",
        )
    event_value = command.to_dict()["event"]
    try:
        if event_value["kind"] == HISTORICAL_DEFENDER_OPEN_PLAY_CONTINUATION_KIND:
            event: HistoricalGameEvent = build_historical_defender_open_play_continuation_event(
                event_value,
                player_ids=projection.player_ids,
                declarer_player_id=projection.declarer_player_id,
                game_id=projection.game_id or projection.session_id,
            )
        else:
            event = build_historical_declarer_card_exposure_continuation_event(
                event_value,
                seat_order_player_ids=projection.player_ids,
                declarer_player_id=projection.declarer_player_id,
                game_type=projection.declaration.game_type,
                game_id=projection.game_id or projection.session_id,
            )
    except ValueError as error:
        return _rejected(
            "event_sequence_violation",
            "/command/event",
            str(error),
        )
    if event.after_play_count != projection.played_card_count:
        return _rejected(
            "event_sequence_violation",
            "/command/event/after_play_count",
            "The continuation boundary must equal the current Play count.",
        )
    owner_player_id, cards = _event_owner_and_cards(projection, event)
    diagnostic = _validate_complete_current_hand(
        projection,
        owner_player_id=owner_player_id,
        cards=cards,
        path="/command/event",
        require_count=True,
    )
    if diagnostic is not None:
        return SessionProjectionApplicationV1(
            projection=None,
            diagnostics=(diagnostic,),
        )
    return _applied(
        replace(
            projection,
            continuation_event=event,
            exact_public_hands=_merge_exact_public_hand(
                projection,
                owner_player_id=owner_player_id,
                cards=cards,
            ),
        )
    )


def _game_end_owner_and_cards(
    projection: SessionProjectionV1,
    game_end: HistoricalGameEnd,
) -> tuple[str, tuple[str, ...]] | None:
    if isinstance(game_end, HistoricalDeclarerCardExposure):
        return (
            projection.declarer_player_id or "",
            game_end.exposure.exposed_cards,
        )
    if isinstance(game_end, HistoricalDefenderOpenPlay):
        return game_end.exposing_defender_player_id, game_end.exposed_cards
    if isinstance(game_end, HistoricalOpenCardThrow):
        return game_end.throwing_player_id, game_end.thrown_cards
    return None


def _apply_game_end(
    projection: SessionProjectionV1,
    command: SetSessionGameEndCommandV1,
) -> SessionProjectionApplicationV1:
    if projection.game_end_reason is not None:
        return _rejected(
            "game_end_violation",
            "/command/game_end_reason",
            "A Session may record Game End only once.",
        )
    if projection.declarer_player_id is None or projection.declaration is None:
        return _rejected(
            "missing_required_value",
            "/command/game_end",
            "Game End capture requires a complete Declarer and Declaration.",
        )
    try:
        game_end = build_historical_game_end(
            command.to_dict()["game_end"],
            game_end_reason=command.game_end_reason,
            declarer_player_id=projection.declarer_player_id,
            seat_order_player_ids=projection.player_ids,
            game_id=projection.game_id or projection.session_id,
        )
    except ValueError as error:
        return _rejected(
            "game_end_violation",
            "/command/game_end",
            str(error),
        )

    if command.game_end_reason == HISTORICAL_NORMAL_COMPLETION:
        if projection.played_card_count != 30 or projection.incomplete_trick is not None:
            return _rejected(
                "game_end_violation",
                "/command/game_end_reason",
                "Normal completion requires exactly 30 Plays and no incomplete trick.",
            )
        if any(cards for _, cards in projection.exact_public_hands):
            return _rejected(
                "game_end_violation",
                "/command/game_end_reason",
                "Normal completion requires every continuation public hand to be empty.",
            )
    else:
        if projection.played_card_count >= 30:
            return _rejected(
                "game_end_violation",
                "/command/game_end_reason",
                "A terminal shortened Game End must occur before 30 Plays.",
            )
        if isinstance(game_end, HistoricalDeclarerConcession):
            expected_count = 10 - sum(
                player_id == projection.declarer_player_id for player_id, _ in projection.plays
            )
            if game_end.declarer_hand_cards_remaining != expected_count:
                return _rejected(
                    "game_end_violation",
                    "/command/game_end/declarer_hand_cards_remaining",
                    "The declarer hand count conflicts with the current Play boundary.",
                )
        if (
            isinstance(game_end, HistoricalDeclarerCardExposure)
            and projection.declaration.game_type == "null"
            and game_end.claimed_play_level != "simple"
        ):
            return _rejected(
                "game_end_violation",
                "/command/game_end/claimed_play_level",
                "Historical Null declarer-card exposure requires claimed_play_level='simple'.",
            )
        if (
            isinstance(game_end, HistoricalDefenderOpenPlay)
            and len(projection.completed_tricks) < 5
        ):
            return _rejected(
                "game_end_violation",
                "/command/game_end",
                "Historical defender open play requires at least five completed tricks.",
            )
        owner_and_cards = (
            None if game_end is None else _game_end_owner_and_cards(projection, game_end)
        )
        if owner_and_cards is not None:
            owner_player_id, cards = owner_and_cards
            diagnostic = _validate_complete_current_hand(
                projection,
                owner_player_id=owner_player_id,
                cards=cards,
                path="/command/game_end",
                require_count=True,
            )
            if diagnostic is not None:
                return SessionProjectionApplicationV1(
                    projection=None,
                    diagnostics=(diagnostic,),
                )

    return _applied(
        replace(
            projection,
            phase="ended",
            game_end_reason=command.game_end_reason,
            game_end=game_end,
        )
    )


def _apply_promotion(
    projection: SessionProjectionV1,
    command: PromoteSessionToRetrospectiveCommandV1,
) -> SessionProjectionApplicationV1:
    del command
    if projection.capture_mode != "live":
        return _rejected(
            "information_policy_violation",
            "/command/kind",
            "Only a Live Session may be promoted to Retrospective Mode.",
        )
    return _applied(replace(projection, capture_mode="retrospective"))


def apply_session_command_to_projection_v1(
    projection: SessionProjectionV1,
    command: SessionCommandV1,
) -> SessionProjectionApplicationV1:
    """Validates and applies exactly one candidate Command to one projection."""
    if not isinstance(projection, SessionProjectionV1):
        raise ValueError("projection must be a SessionProjectionV1.")
    if not is_session_command_v1(command):
        raise ValueError("command must be one SessionCommandV1 member.")
    if projection.phase not in SESSION_COMMAND_ALLOWED_PHASES[command.kind]:
        return _rejected(
            "phase_violation",
            "/command/kind",
            f"Command '{command.kind}' is not allowed during phase '{projection.phase}'.",
        )

    if isinstance(command, SetSessionGameMetadataCommandV1):
        return _apply_metadata(projection, command)
    if isinstance(command, RecordSessionDealtCardCommandV1):
        return _apply_dealt_card(projection, command)
    if isinstance(command, SetSessionDeclarerCommandV1):
        return _apply_declarer(projection, command)
    if isinstance(command, SetSessionDeclarationCommandV1):
        return _apply_declaration(projection, command)
    if isinstance(command, RecordSessionDiscardCommandV1):
        return _apply_discard(projection, command)
    if isinstance(command, RecordSessionPlayCommandV1):
        return _apply_play(projection, command)
    if isinstance(command, SetSessionGameEventCommandV1):
        return _apply_game_event(projection, command)
    if isinstance(command, SetSessionGameEndCommandV1):
        return _apply_game_end(projection, command)
    if isinstance(command, PromoteSessionToRetrospectiveCommandV1):
        return _apply_promotion(projection, command)
    return _apply_public_hand(projection, command)


def _export_diagnostic(
    code: str,
    path: str,
    message: str,
    *,
    position: bool = False,
    historical: bool = False,
) -> SessionValidationDiagnosticV1:
    return SessionValidationDiagnosticV1(
        code=code,
        path=path,
        message=message,
        severity="info",
        blocks_command=False,
        blocks_position_export=position,
        blocks_historical_export=historical,
    )


def _has_exact_playable_hand(
    projection: SessionProjectionV1,
    player_id: str,
) -> bool:
    initial_hand = projection.initial_hand_for(player_id)
    remaining_hand = projection.remaining_hand_for(player_id)
    if initial_hand is None or len(initial_hand) != 10 or remaining_hand is None:
        return False
    if (
        player_id == projection.declarer_player_id
        and projection.declaration is not None
        and not projection.declaration.hand_game
    ):
        return len(projection.known_skat) == 2 and len(projection.discarded_cards) == 2
    return True


def _valid_discard_state(projection: SessionProjectionV1) -> bool:
    if projection.declaration is None or projection.declarer_player_id is None:
        return False
    if projection.declaration.hand_game:
        return not projection.discarded_cards
    if len(projection.known_skat) != 2 or len(projection.discarded_cards) != 2:
        return False
    available = {
        *(projection.initial_hand_for(projection.declarer_player_id) or ()),
        *projection.known_skat,
    }
    return set(projection.discarded_cards) <= available


def _historical_end_is_ready(projection: SessionProjectionV1) -> bool:
    if projection.game_end_reason == HISTORICAL_NORMAL_COMPLETION:
        return (
            projection.game_end is None
            and projection.played_card_count == 30
            and projection.incomplete_trick is None
            and not any(cards for _, cards in projection.exact_public_hands)
        )
    return (
        projection.game_end_reason is not None
        and projection.game_end is not None
        and projection.played_card_count < 30
    )


def _build_readiness(
    target: str,
    diagnostics: list[SessionValidationDiagnosticV1],
    *,
    blocker_field: str,
) -> SessionExportReadinessV1:
    reason_codes = tuple(
        {diagnostic.code for diagnostic in diagnostics if getattr(diagnostic, blocker_field)}
    )
    return SessionExportReadinessV1(
        target=target,
        status="unavailable" if reason_codes else "available",
        reason_codes=reason_codes,
    )


def build_session_validation_result_v1(
    projection: SessionProjectionV1,
    *,
    revision: int,
) -> SessionValidationResultV1:
    """Recomputes current export blockers from one accepted projection."""
    diagnostics: list[SessionValidationDiagnosticV1] = []

    if projection.phase != "play":
        diagnostics.append(
            _export_diagnostic(
                "phase_violation",
                "/phase",
                "Position export requires phase 'play'.",
                position=True,
            )
        )
    if projection.local_player_id is None:
        diagnostics.append(
            _export_diagnostic(
                "missing_required_value",
                "/local_player_id",
                "Position export requires a local Player.",
                position=True,
            )
        )
    elif projection.next_player_id != projection.local_player_id:
        diagnostics.append(
            _export_diagnostic(
                "turn_order_violation",
                "/next_player_id",
                "Position export requires the local Player to be next.",
                position=True,
            )
        )
    if projection.declarer_player_id is None:
        diagnostics.append(
            _export_diagnostic(
                "missing_required_value",
                "/declarer_player_id",
                "Position export requires the Declarer.",
                position=True,
            )
        )
    if projection.declaration is None:
        diagnostics.append(
            _export_diagnostic(
                "missing_required_value",
                "/declaration",
                "Position export requires the Declaration.",
                position=True,
            )
        )
    if projection.local_player_id is not None:
        local_hand = projection.remaining_hand_for(projection.local_player_id)
        if not _has_exact_playable_hand(projection, projection.local_player_id) or not local_hand:
            diagnostics.append(
                _export_diagnostic(
                    "missing_required_value",
                    "/remaining_known_hands",
                    "Position export requires an exact non-empty local playable hand.",
                    position=True,
                )
            )
    if projection.game_end_reason is not None:
        diagnostics.append(
            _export_diagnostic(
                "game_end_violation",
                "/game_end_reason",
                "Position export is unavailable after Game End.",
                position=True,
            )
        )
    if (
        projection.local_player_id is not None
        and projection.declarer_player_id is not None
        and projection.declaration is not None
        and projection.declaration.ouvert
        and projection.declarer_player_id != projection.local_player_id
    ):
        declarer_cards = projection.public_hand_for(projection.declarer_player_id)
        if declarer_cards is None:
            declarer_cards = projection.remaining_hand_for(
                projection.declarer_player_id
            )
        expected_count = 10 - sum(
            player_id == projection.declarer_player_id
            for player_id, _ in projection.plays
        )
        if declarer_cards is None or len(declarer_cards) != expected_count:
            diagnostics.append(
                _export_diagnostic(
                    "missing_required_value",
                    "/exact_public_hands",
                    "Opponent-declarer Ouvert Position export requires the exact "
                    "current public Declarer hand.",
                    position=True,
                )
            )

    if projection.capture_mode != "retrospective":
        diagnostics.append(
            _export_diagnostic(
                "information_policy_violation",
                "/capture_mode",
                "Historical export requires Retrospective Mode.",
                historical=True,
            )
        )
    if projection.phase != "ended":
        diagnostics.append(
            _export_diagnostic(
                "phase_violation",
                "/phase",
                "Historical export requires phase 'ended'.",
                historical=True,
            )
        )
    if projection.game_id is None:
        diagnostics.append(
            _export_diagnostic(
                "missing_required_value",
                "/game_id",
                "Historical export requires a stable Game ID.",
                historical=True,
            )
        )
    if not _is_complete_retrospective_deal(projection):
        diagnostics.append(
            _export_diagnostic(
                "card_identity_violation",
                "/initial_known_hands",
                "Historical export requires one exact complete 32-card Deal.",
                historical=True,
            )
        )
    if projection.declarer_player_id is None or projection.declaration is None:
        diagnostics.append(
            _export_diagnostic(
                "missing_required_value",
                "/declaration",
                "Historical export requires a complete Declarer and Declaration.",
                historical=True,
            )
        )
    elif not _valid_discard_state(projection):
        diagnostics.append(
            _export_diagnostic(
                "declaration_violation",
                "/discarded_cards",
                "Historical export requires a valid Hand or two-Discard state.",
                historical=True,
            )
        )
    if not _historical_end_is_ready(projection):
        diagnostics.append(
            _export_diagnostic(
                "game_end_violation",
                "/game_end_reason",
                "Historical export requires a valid normal or supported terminal ending.",
                historical=True,
            )
        )

    position_export = _build_readiness(
        "position_analysis",
        diagnostics,
        blocker_field="blocks_position_export",
    )
    historical_export = _build_readiness(
        "historical_game",
        diagnostics,
        blocker_field="blocks_historical_export",
    )
    return SessionValidationResultV1(
        revision=revision,
        phase=projection.phase,
        structurally_valid=True,
        valid_incomplete=projection.phase != "ended",
        game_complete=projection.phase == "ended",
        position_export=position_export,
        historical_export=historical_export,
        diagnostics=tuple(diagnostics),
    )
