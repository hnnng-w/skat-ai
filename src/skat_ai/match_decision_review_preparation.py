from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Final, cast

from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalSeat,
    HistoricalSnapshotCompletedTrick,
    HistoricalSnapshotDeclaration,
    HistoricalSnapshotExposedCards,
    HistoricalSnapshotOpponentHandSize,
    HistoricalSnapshotPlay,
    HistoricalSnapshotVisibleState,
    SkatVisibility,
    _build_relative_player_map,
    _infer_visible_matadors,
    build_serializable_historical_decision_snapshot,
)
from skat_ai.match_observed_reconstruction import (
    MatchObservedGameReconstructionV1,
    build_match_observed_game_reconstruction_v1,
)
from skat_ai.match_player_statistics_context import (
    MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES,
    MatchPlayerStatisticsContextV1,
)
from skat_ai.match_player_statistics_preparation import (
    MatchPlayerStatisticsPreparationV1,
    build_match_player_statistics_preparation_v1,
)
from skat_ai.match_workspace_contracts import (
    MatchWorkspaceV1,
    _require_match_position,
)
from skat_ai.rules import get_legal_cards

MATCH_DECISION_REVIEW_PREPARATION_VERSION = 1

MATCH_DECISION_REVIEW_PREPARATION_STATUSES: Final[tuple[str, ...]] = (
    "available",
    "partial",
    "unavailable",
)
MATCH_DECISION_REVIEW_SKIP_REASONS: Final[tuple[str, ...]] = (
    "acting_hand_unavailable",
    "required_public_hand_unavailable",
)

MATCH_DECISION_REVIEW_INFORMATION_POLICY = (
    "reconstruct_decision_time_own_hand_without_future_opponent_information"
)
MATCH_PROFILE_BINDING_POLICY = "prepare_eligible_relative_opponents_without_policy_application"


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchSkippedDecisionV1:
    """One retained observed Play that cannot produce a safe snapshot."""

    decision_index: int
    acting_player_id: str
    reason: str

    def __post_init__(self) -> None:
        if type(self.decision_index) is not int or self.decision_index <= 0:
            raise ValueError("decision_index must be a positive integer.")
        if not self.acting_player_id:
            raise ValueError("acting_player_id must be a non-empty string.")
        if self.reason not in MATCH_DECISION_REVIEW_SKIP_REASONS:
            raise ValueError(f"reason must be one of {list(MATCH_DECISION_REVIEW_SKIP_REASONS)}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchDecisionOpponentProfileBindingV1:
    """Eligible relative opponent Profiles prepared without applying a Policy."""

    decision_index: int
    acting_player_id: str
    left_opponent_player_id: str
    right_opponent_player_id: str
    left_temporal_status: str
    right_temporal_status: str
    left_profile_available: bool
    right_profile_available: bool
    left_actionable_policy_preset: str | None
    right_actionable_policy_preset: str | None

    def __post_init__(self) -> None:
        if type(self.decision_index) is not int or self.decision_index <= 0:
            raise ValueError("decision_index must be a positive integer.")
        player_ids = {
            self.acting_player_id,
            self.left_opponent_player_id,
            self.right_opponent_player_id,
        }
        if len(player_ids) != 3:
            raise ValueError("Profile bindings require three distinct Player IDs.")
        for side in ("left", "right"):
            temporal_status = getattr(self, f"{side}_temporal_status")
            available = getattr(self, f"{side}_profile_available")
            preset = getattr(self, f"{side}_actionable_policy_preset")
            if temporal_status not in MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES:
                raise ValueError(
                    f"{side}_temporal_status must be one of "
                    f"{list(MATCH_PLAYER_STATISTICS_TEMPORAL_STATUSES)}."
                )
            if type(available) is not bool:
                raise ValueError(f"{side}_profile_available must be a boolean.")
            if available != (temporal_status == "eligible"):
                raise ValueError(
                    f"{side}_profile_available must be true exactly for eligible status."
                )
            if not available and preset is not None:
                raise ValueError(f"{side}_actionable_policy_preset requires an eligible Profile.")
            if preset not in {None, "aggressive_points", "cautious_defender"}:
                raise ValueError(
                    f"{side}_actionable_policy_preset must be an existing actionable preset."
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_index": self.decision_index,
            "acting_player_id": self.acting_player_id,
            "left_opponent_player_id": self.left_opponent_player_id,
            "right_opponent_player_id": self.right_opponent_player_id,
            "left_temporal_status": self.left_temporal_status,
            "right_temporal_status": self.right_temporal_status,
            "left_profile_available": self.left_profile_available,
            "right_profile_available": self.right_profile_available,
            "left_actionable_policy_preset": self.left_actionable_policy_preset,
            "right_actionable_policy_preset": self.right_actionable_policy_preset,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchDecisionReviewPreparationV1:
    """Information-safe snapshots prepared from one retained observed Game."""

    match_decision_review_preparation_version: int = MATCH_DECISION_REVIEW_PREPARATION_VERSION
    status: str
    match_id: str
    game_id: str
    match_position: int
    source_played_at: str | None
    source_play_count: int
    prepared_decision_count: int
    skipped_decision_count: int
    snapshots: tuple[HistoricalDecisionSnapshot, ...]
    skipped_decisions: tuple[MatchSkippedDecisionV1, ...]
    profile_bindings: tuple[MatchDecisionOpponentProfileBindingV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.match_decision_review_preparation_version) is not int
            or self.match_decision_review_preparation_version
            != MATCH_DECISION_REVIEW_PREPARATION_VERSION
        ):
            raise ValueError(
                "match_decision_review_preparation_version must equal "
                f"{MATCH_DECISION_REVIEW_PREPARATION_VERSION}."
            )
        if self.status not in MATCH_DECISION_REVIEW_PREPARATION_STATUSES:
            raise ValueError(
                f"status must be one of {list(MATCH_DECISION_REVIEW_PREPARATION_STATUSES)}."
            )
        _require_match_position(self.match_position)
        for field_name, value in (
            ("source_play_count", self.source_play_count),
            ("prepared_decision_count", self.prepared_decision_count),
            ("skipped_decision_count", self.skipped_decision_count),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer.")
        if not isinstance(self.snapshots, (list, tuple)) or any(
            type(snapshot) is not HistoricalDecisionSnapshot for snapshot in self.snapshots
        ):
            raise ValueError("snapshots must contain HistoricalDecisionSnapshot values.")
        if not isinstance(self.skipped_decisions, (list, tuple)) or any(
            type(item) is not MatchSkippedDecisionV1 for item in self.skipped_decisions
        ):
            raise ValueError("skipped_decisions must contain MatchSkippedDecisionV1 values.")
        if not isinstance(self.profile_bindings, (list, tuple)) or any(
            type(item) is not MatchDecisionOpponentProfileBindingV1
            for item in self.profile_bindings
        ):
            raise ValueError(
                "profile_bindings must contain MatchDecisionOpponentProfileBindingV1 values."
            )
        snapshots = tuple(
            replace(
                snapshot,
                relative_player_map=MappingProxyType(dict(snapshot.relative_player_map)),
            )
            for snapshot in self.snapshots
        )
        object.__setattr__(self, "snapshots", snapshots)
        object.__setattr__(self, "skipped_decisions", tuple(self.skipped_decisions))
        object.__setattr__(self, "profile_bindings", tuple(self.profile_bindings))
        if self.prepared_decision_count != len(self.snapshots):
            raise ValueError("prepared_decision_count must equal snapshots length.")
        if self.skipped_decision_count != len(self.skipped_decisions):
            raise ValueError("skipped_decision_count must equal skipped_decisions length.")
        if len(self.profile_bindings) != self.prepared_decision_count:
            raise ValueError("profile_bindings must contain one value per snapshot.")
        if self.source_play_count != (self.prepared_decision_count + self.skipped_decision_count):
            raise ValueError("Prepared and skipped Decision counts must reconcile.")
        expected_status = (
            "available"
            if self.source_play_count > 0 and self.prepared_decision_count == self.source_play_count
            else "partial"
            if self.prepared_decision_count > 0
            else "unavailable"
        )
        if self.status != expected_status:
            raise ValueError("status must match prepared Decision coverage.")
        snapshot_indexes = tuple(snapshot.decision_index for snapshot in self.snapshots)
        skipped_indexes = tuple(item.decision_index for item in self.skipped_decisions)
        if snapshot_indexes != tuple(sorted(snapshot_indexes)) or skipped_indexes != tuple(
            sorted(skipped_indexes)
        ):
            raise ValueError("Snapshots and skipped Decisions must preserve source order.")
        if tuple(sorted((*snapshot_indexes, *skipped_indexes))) != tuple(
            range(1, self.source_play_count + 1)
        ):
            raise ValueError("Prepared and skipped Decisions must cover source order exactly.")
        if tuple(binding.decision_index for binding in self.profile_bindings) != (snapshot_indexes):
            raise ValueError("Profile binding order must equal snapshot order.")
        if any(
            snapshot.source_game_id != self.game_id
            or snapshot.source_played_at != self.source_played_at
            for snapshot in self.snapshots
        ):
            raise ValueError("Snapshots must retain the preparation source identity and time.")
        for snapshot, binding in zip(
            self.snapshots,
            self.profile_bindings,
            strict=True,
        ):
            relative_map = snapshot.relative_player_map
            if (
                binding.acting_player_id != snapshot.acting_player_id
                or binding.acting_player_id != relative_map["me"]
                or binding.left_opponent_player_id != relative_map["left"]
                or binding.right_opponent_player_id != relative_map["right"]
            ):
                raise ValueError("Profile bindings must equal each snapshot relative map.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_decision_review_preparation_version": (
                self.match_decision_review_preparation_version
            ),
            "status": self.status,
            "match_id": self.match_id,
            "game_id": self.game_id,
            "match_position": self.match_position,
            "source_played_at": self.source_played_at,
            "source_play_count": self.source_play_count,
            "prepared_decision_count": self.prepared_decision_count,
            "skipped_decision_count": self.skipped_decision_count,
            "snapshots": [
                build_serializable_historical_decision_snapshot(snapshot)
                for snapshot in self.snapshots
            ],
            "skipped_decisions": [item.to_dict() for item in self.skipped_decisions],
            "profile_bindings": [item.to_dict() for item in self.profile_bindings],
        }


def _build_profile_binding(
    snapshot: HistoricalDecisionSnapshot,
    contexts_by_player_id: dict[str, MatchPlayerStatisticsContextV1],
) -> MatchDecisionOpponentProfileBindingV1:
    relative_map = snapshot.relative_player_map
    left = contexts_by_player_id[relative_map["left"]]
    right = contexts_by_player_id[relative_map["right"]]

    def actionable_preset(context: MatchPlayerStatisticsContextV1) -> str | None:
        if not context.eligible_for_match_analysis or context.profile_derivation is None:
            return None
        return context.profile_derivation.actionable_policy_preset

    return MatchDecisionOpponentProfileBindingV1(
        decision_index=snapshot.decision_index,
        acting_player_id=snapshot.acting_player_id,
        left_opponent_player_id=left.player_id,
        right_opponent_player_id=right.player_id,
        left_temporal_status=left.temporal_status,
        right_temporal_status=right.temporal_status,
        left_profile_available=left.eligible_for_match_analysis,
        right_profile_available=right.eligible_for_match_analysis,
        left_actionable_policy_preset=actionable_preset(left),
        right_actionable_policy_preset=actionable_preset(right),
    )


def _build_match_decision_review_preparation_from_reconstruction_v1(
    reconstruction: MatchObservedGameReconstructionV1,
    *,
    source_played_at: str | None,
    statistics_preparation: MatchPlayerStatisticsPreparationV1,
) -> MatchDecisionReviewPreparationV1:
    game = reconstruction.observed_game
    trace = reconstruction.trace
    declaration = game.declaration
    declarer_player_id = game.declarer_player_id
    if trace.plays and (declaration is None or declarer_player_id is None):
        raise ValueError("Observed Plays require Declaration evidence.")
    seat_order_player_ids = [player.player_id for player in game.players]
    seats_by_player_id = {player.player_id: player.seat for player in game.players}
    remaining_hands = {player_id: list(cards) for player_id, cards in reconstruction.playable_hands}
    prior_play_counts = {player_id: 0 for player_id in seat_order_player_ids}
    contexts_by_player_id = {
        context.player_id: context for context in statistics_preparation.participant_contexts
    }
    completed_tricks: list[HistoricalSnapshotCompletedTrick] = []
    current_trick: list[HistoricalSnapshotPlay] = []
    declarer_trick_points = 0
    defender_trick_points = 0
    completed_trick_index = 0
    snapshots: list[HistoricalDecisionSnapshot] = []
    skipped: list[MatchSkippedDecisionV1] = []
    bindings: list[MatchDecisionOpponentProfileBindingV1] = []

    for play in trace.plays:
        acting_hand = remaining_hands.get(play.player_id)
        public_declarer_hand = (
            None
            if declaration is None or not declaration.ouvert
            else remaining_hands.get(declarer_player_id)
        )
        skip_reason = None
        if acting_hand is None:
            skip_reason = "acting_hand_unavailable"
        elif declaration is not None and declaration.ouvert and public_declarer_hand is None:
            skip_reason = "required_public_hand_unavailable"

        if skip_reason is not None:
            skipped.append(
                MatchSkippedDecisionV1(
                    decision_index=play.decision_index,
                    acting_player_id=play.player_id,
                    reason=skip_reason,
                )
            )
        else:
            assert declaration is not None
            assert declarer_player_id is not None
            assert acting_hand is not None
            legal_cards = get_legal_cards(
                acting_hand,
                [item.card for item in current_trick],
                declaration.game_type,
            )
            if play.card not in acting_hand or play.card not in legal_cards:
                raise ValueError(
                    f"Observed decision {play.decision_index} conflicts with its "
                    "reconstructed acting hand."
                )
            relative_map = MappingProxyType(
                _build_relative_player_map(
                    play.player_id,
                    seat_order_player_ids,
                )
            )
            is_declarer = play.player_id == declarer_player_id
            known_skat_cards = (
                list(game.discarded_cards)
                if is_declarer and not declaration.hand_game and game.discarded_cards is not None
                else []
            )
            skat_visibility: SkatVisibility = "known_to_declarer" if known_skat_cards else "unknown"
            public_exposed_cards = (
                (
                    HistoricalSnapshotExposedCards(
                        player_id=declarer_player_id,
                        cards=tuple(public_declarer_hand),
                    ),
                )
                if declaration.ouvert and public_declarer_hand is not None
                else ()
            )
            visible_matadors = (
                None
                if is_declarer and not declaration.hand_game and game.discarded_cards is None
                else _infer_visible_matadors(
                    game_type=declaration.game_type,
                    hand_game=declaration.hand_game,
                    acting_player_id=play.player_id,
                    declarer_player_id=declarer_player_id,
                    own_hand=acting_hand,
                    known_skat_cards=known_skat_cards,
                    completed_tricks=tuple(completed_tricks),
                    current_trick=tuple(current_trick),
                    public_exposed_cards=public_exposed_cards,
                )
            )
            snapshot = HistoricalDecisionSnapshot(
                source_game_id=game.game_id,
                source_played_at=source_played_at,
                decision_index=play.decision_index,
                trick_number=completed_trick_index + 1,
                play_index=len(current_trick) + 1,
                acting_player_id=play.player_id,
                acting_seat=cast(HistoricalSeat, seats_by_player_id[play.player_id]),
                acting_side="declarer" if is_declarer else "defenders",
                actual_card_played=play.card,
                information_cutoff="before_actual_play",
                relative_player_map=relative_map,
                visible_state=HistoricalSnapshotVisibleState(
                    game_type=declaration.game_type,
                    declaration=HistoricalSnapshotDeclaration(
                        hand_game=declaration.hand_game,
                        ouvert=declaration.ouvert,
                        schneider_announced=declaration.schneider_announced,
                        schwarz_announced=declaration.schwarz_announced,
                        matadors=visible_matadors,
                        bid_value=declaration.bid_value,
                    ),
                    own_hand=tuple(acting_hand),
                    legal_cards=tuple(legal_cards),
                    skat_visibility=skat_visibility,
                    known_skat_cards=tuple(known_skat_cards),
                    public_exposed_cards=public_exposed_cards,
                    completed_tricks=tuple(completed_tricks),
                    current_trick=tuple(current_trick),
                    declarer_trick_points=declarer_trick_points,
                    defender_trick_points=defender_trick_points,
                    opponent_hand_sizes=(
                        HistoricalSnapshotOpponentHandSize(
                            relative_player="left",
                            player_id=relative_map["left"],
                            remaining_card_count=10 - prior_play_counts[relative_map["left"]],
                        ),
                        HistoricalSnapshotOpponentHandSize(
                            relative_player="right",
                            player_id=relative_map["right"],
                            remaining_card_count=10 - prior_play_counts[relative_map["right"]],
                        ),
                    ),
                ),
            )
            snapshots.append(snapshot)
            bindings.append(_build_profile_binding(snapshot, contexts_by_player_id))

        if play.player_id in remaining_hands:
            remaining_hands[play.player_id].remove(play.card)
        prior_play_counts[play.player_id] += 1
        current_trick.append(HistoricalSnapshotPlay(player_id=play.player_id, card=play.card))
        if len(current_trick) == 3:
            winner_player_id = trace.winner_player_ids[completed_trick_index]
            trick_points = trace.trick_points[completed_trick_index]
            completed_trick = HistoricalSnapshotCompletedTrick(
                trick_number=completed_trick_index + 1,
                plays=tuple(current_trick),
                winner_player_id=winner_player_id,
                winner_side=("declarer" if winner_player_id == declarer_player_id else "defenders"),
                trick_points=trick_points,
            )
            completed_tricks.append(completed_trick)
            if completed_trick.winner_side == "declarer":
                declarer_trick_points += trick_points
            else:
                defender_trick_points += trick_points
            completed_trick_index += 1
            current_trick = []

    prepared_count = len(snapshots)
    source_count = len(trace.plays)
    status = (
        "available"
        if source_count > 0 and prepared_count == source_count
        else "partial"
        if prepared_count > 0
        else "unavailable"
    )
    return MatchDecisionReviewPreparationV1(
        status=status,
        match_id=game.match_id,
        game_id=game.game_id,
        match_position=game.match_position,
        source_played_at=source_played_at,
        source_play_count=source_count,
        prepared_decision_count=prepared_count,
        skipped_decision_count=len(skipped),
        snapshots=tuple(snapshots),
        skipped_decisions=tuple(skipped),
        profile_bindings=tuple(bindings),
    )


def build_match_decision_review_preparation_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_position: int,
) -> MatchDecisionReviewPreparationV1:
    """Prepares safe retained Decisions without executing an analysis workflow."""
    from skat_ai.match_workspace_contracts import (
        _validate_match_workspace_with_traces_v1,
    )

    validated_traces = dict(_validate_match_workspace_with_traces_v1(workspace))
    _require_match_position(match_position)
    slot = workspace.slots[match_position - 1]
    if slot.observed_game is None:
        raise ValueError("Decision preparation requires an observed_game Slot.")
    statistics_preparation = build_match_player_statistics_preparation_v1(
        workspace.match_definition
    )
    reconstruction = build_match_observed_game_reconstruction_v1(
        slot.observed_game,
        validated_trace=validated_traces[match_position],
    )
    return _build_match_decision_review_preparation_from_reconstruction_v1(
        reconstruction,
        source_played_at=workspace.match_definition.played_at,
        statistics_preparation=statistics_preparation,
    )
