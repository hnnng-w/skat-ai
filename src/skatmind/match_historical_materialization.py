from dataclasses import dataclass
from typing import Any, Final

from skatmind.deck import get_full_deck
from skatmind.errors import SkatMindInvariantError
from skatmind.game_declaration import build_serializable_game_declaration
from skatmind.historical_game import (
    HISTORICAL_GAME_END_REASON,
    HISTORICAL_GAME_SCHEMA_VERSION,
    HistoricalGameRecord,
    build_historical_game_record,
    build_historical_game_summary,
    build_serializable_historical_record,
)
from skatmind.match_observed_reconstruction import (
    MatchObservedGameReconstructionV1,
    build_match_observed_game_reconstruction_v1,
)
from skatmind.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_match_position,
    _validate_match_workspace_with_traces_v1,
)

MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION = 1

MATCH_MATERIALIZATION_ARTIFACT_STATUSES: Final[tuple[str, ...]] = (
    "available",
    "unavailable",
)
MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS: Final[tuple[str, ...]] = (
    "slot_empty",
    "passed_deal",
    "declaration_unavailable",
    "incomplete_play_trace",
    "original_skat_unavailable",
    "discarded_cards_unavailable",
)

MATCH_HISTORICAL_MATERIALIZATION_POLICY = (
    "existing_normal_completion_contract_with_complete_initial_deal"
)
MATCH_MATERIALIZED_PLAYED_AT_POLICY = "retain_match_played_at_without_media_offset_derivation"


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchHistoricalGameMaterializationV1:
    """Available strict Historical Game or normal evidence unavailability."""

    match_historical_game_materialization_version: int = (
        MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION
    )
    status: str
    match_id: str
    match_position: int
    game_id: str | None
    unavailable_reason: str | None
    historical_game: HistoricalGameRecord | None

    def __post_init__(self) -> None:
        if (
            type(self.match_historical_game_materialization_version) is not int
            or self.match_historical_game_materialization_version
            != MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION
        ):
            raise ValueError(
                "match_historical_game_materialization_version must equal "
                f"{MATCH_HISTORICAL_GAME_MATERIALIZATION_VERSION}."
            )
        if self.status not in MATCH_MATERIALIZATION_ARTIFACT_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_MATERIALIZATION_ARTIFACT_STATUSES)}."
            )
        _require_match_position(self.match_position)
        if self.status == "available":
            if (
                self.unavailable_reason is not None
                or type(self.historical_game) is not HistoricalGameRecord
                or self.game_id != self.historical_game.game_id
            ):
                raise ValueError("Available Historical materialization requires exactly one Game.")
        elif (
            self.historical_game is not None
            or self.unavailable_reason not in MATCH_HISTORICAL_MATERIALIZATION_UNAVAILABLE_REASONS
        ):
            raise ValueError(
                "Unavailable Historical materialization requires one canonical reason."
            )
        if self.unavailable_reason in {"slot_empty", "passed_deal"}:
            if self.game_id is not None:
                raise ValueError("A non-Game Slot cannot contain game_id.")
        elif self.status == "unavailable" and self.game_id is None:
            raise ValueError("Unavailable observed-Game materialization requires game_id.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_historical_game_materialization_version": (
                self.match_historical_game_materialization_version
            ),
            "status": self.status,
            "match_id": self.match_id,
            "match_position": self.match_position,
            "game_id": self.game_id,
            "unavailable_reason": self.unavailable_reason,
            "historical_game": (
                None
                if self.historical_game is None
                else build_serializable_historical_record(self.historical_game)
            ),
        }


def _unavailable(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
    game_id: str | None,
    reason: str,
) -> MatchHistoricalGameMaterializationV1:
    return MatchHistoricalGameMaterializationV1(
        status="unavailable",
        match_id=workspace.match_definition.match_id,
        match_position=match_position,
        game_id=game_id,
        unavailable_reason=reason,
        historical_game=None,
    )


def _build_historical_declaration(reconstruction: MatchObservedGameReconstructionV1):
    declaration = reconstruction.observed_game.declaration
    assert declaration is not None
    result = build_serializable_game_declaration(declaration)
    if declaration.game_type == "null":
        result.pop("matadors")
        result.pop("schneider_announced")
        result.pop("schwarz_announced")
    elif declaration.matadors is None:
        result.pop("matadors")
    return result


def _materialize_match_observed_game_historical_from_reconstruction_v1(
    workspace: MatchWorkspaceV1,
    *,
    reconstruction: MatchObservedGameReconstructionV1,
) -> MatchHistoricalGameMaterializationV1:
    game = reconstruction.observed_game
    if (
        game.declaration is None
        or game.declarer_player_id is None
        or game.declaration.bid_value is None
    ):
        return _unavailable(
            workspace,
            match_position=game.match_position,
            game_id=game.game_id,
            reason="declaration_unavailable",
        )
    if not reconstruction.trace.complete_play_trace:
        return _unavailable(
            workspace,
            match_position=game.match_position,
            game_id=game.game_id,
            reason="incomplete_play_trace",
        )
    if game.original_skat is None:
        return _unavailable(
            workspace,
            match_position=game.match_position,
            game_id=game.game_id,
            reason="original_skat_unavailable",
        )
    if game.discarded_cards is None:
        return _unavailable(
            workspace,
            match_position=game.match_position,
            game_id=game.game_id,
            reason="discarded_cards_unavailable",
        )

    playable_hands = dict(reconstruction.playable_hands)
    deck = tuple(get_full_deck())
    initial_hands = {}
    for player in game.players:
        playable_hand = playable_hands[player.player_id]
        if player.player_id != game.declarer_player_id or game.declaration.hand_game:
            initial_hands[player.player_id] = playable_hand
            continue
        original_cards = (set(playable_hand) | set(game.discarded_cards)) - set(game.original_skat)
        initial_hand = tuple(card for card in deck if card in original_cards)
        if len(initial_hand) != 10:
            raise SkatMindInvariantError(
                "Complete non-Hand evidence must reconstruct ten Declarer dealt Cards."
            )
        initial_hands[player.player_id] = initial_hand

    labels_by_player_id = {
        participant.player_id: participant.player_label
        for participant in workspace.match_definition.participants
    }
    players = []
    for player in game.players:
        value: dict[str, Any] = {
            "player_id": player.player_id,
            "seat": player.seat,
            "initial_hand": list(initial_hands[player.player_id]),
        }
        label = labels_by_player_id[player.player_id]
        if label is not None:
            value["player_label"] = label
        players.append(value)

    tricks = []
    for offset in range(0, len(reconstruction.trace.plays), 3):
        trick_plays = reconstruction.trace.plays[offset : offset + 3]
        tricks.append(
            {
                "trick_number": (offset // 3) + 1,
                "leader_player_id": trick_plays[0].player_id,
                "plays": [{"player_id": play.player_id, "card": play.card} for play in trick_plays],
            }
        )
    raw_record = {
        "schema_version": HISTORICAL_GAME_SCHEMA_VERSION,
        "game_id": game.game_id,
        "players": players,
        "skat": list(game.original_skat),
        "declarer_player_id": game.declarer_player_id,
        "declaration": _build_historical_declaration(reconstruction),
        "discarded_cards": list(game.discarded_cards),
        "game_end_reason": HISTORICAL_GAME_END_REASON,
        "tricks": tricks,
    }
    if workspace.match_definition.played_at is not None:
        raw_record["played_at"] = workspace.match_definition.played_at
    try:
        historical_game = build_historical_game_record(raw_record)
        canonical_record = build_serializable_historical_record(historical_game)
        rebuilt = build_historical_game_record(canonical_record)
        if rebuilt != historical_game:
            raise SkatMindInvariantError(
                "Materialized Historical Game did not round trip canonically."
            )
        summary = build_historical_game_summary(historical_game)
        if (
            summary.get("status") != "complete"
            or summary.get("final_settlement_summary", {}).get("is_complete") is not True
        ):
            raise SkatMindInvariantError(
                "Materialized Historical Game must have complete Settlement."
            )
    except SkatMindInvariantError:
        raise
    except ValueError as error:
        raise SkatMindInvariantError(
            "Complete exact Match evidence did not build the existing Historical Game."
        ) from error
    return MatchHistoricalGameMaterializationV1(
        status="available",
        match_id=game.match_id,
        match_position=game.match_position,
        game_id=game.game_id,
        unavailable_reason=None,
        historical_game=historical_game,
    )


def materialize_match_observed_game_historical_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> MatchHistoricalGameMaterializationV1:
    """Materializes one strict normal-completion Historical Game when possible."""
    validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
    _require_match_position(match_position)
    slot = workspace.slots[match_position - 1]
    if slot.slot_kind == "empty":
        return _unavailable(
            workspace,
            match_position=match_position,
            game_id=None,
            reason="slot_empty",
        )
    if slot.slot_kind == "passed_deal":
        return _unavailable(
            workspace,
            match_position=match_position,
            game_id=None,
            reason="passed_deal",
        )
    assert slot.observed_game is not None
    reconstruction = build_match_observed_game_reconstruction_v1(
        slot.observed_game,
        validated_trace=validated_traces[match_position],
    )
    return _materialize_match_observed_game_historical_from_reconstruction_v1(
        workspace,
        reconstruction=reconstruction,
    )
