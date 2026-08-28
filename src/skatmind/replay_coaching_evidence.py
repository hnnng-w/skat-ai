import math
from dataclasses import dataclass
from typing import Any

from skatmind.bounded_search_result import (
    BoundedSearchResult,
    build_serializable_bounded_search_result,
)
from skatmind.deck import get_full_deck
from skatmind.objective_utility import calculate_expected_objective_utility
from skatmind.retrospective_search_comparison import (
    SearchVsImmediateComparison,
    build_search_vs_immediate_comparison,
    build_serializable_search_vs_immediate_comparison,
)
from skatmind.rules import GAME_TYPES

REPLAY_COACHING_CONTRACT_VERSION = 1
REPLAY_COACHING_INFORMATION_POLICY = (
    "decision_time_then_retrospective_attachment"
)

REPLAY_COACHING_GAME_PHASES = ("opening", "middle", "endgame")
REPLAY_COACHING_ROOT_SEATS = ("lead", "second", "third")
REPLAY_COACHING_LOCAL_SIDES = ("declarer", "defenders")
REPLAY_COACHING_ACTING_SEATS = ("forehand", "middlehand", "rearhand")


def get_replay_coaching_game_phase(trick_number: int) -> str:
    """Returns the version-1 product phase for one normal trick number."""
    if isinstance(trick_number, bool) or not isinstance(trick_number, int):
        raise ValueError("trick_number must be an integer from 1 through 10.")
    if 1 <= trick_number <= 3:
        return "opening"
    if 4 <= trick_number <= 7:
        return "middle"
    if 8 <= trick_number <= 10:
        return "endgame"
    raise ValueError("trick_number must be an integer from 1 through 10.")


def canonicalize_replay_coaching_cards(cards: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Copies unique valid cards into canonical deck order."""
    if isinstance(cards, (str, bytes)):
        raise ValueError("cards must be a card collection.")
    copied = tuple(cards)
    deck = get_full_deck()
    deck_set = set(deck)
    if len(copied) != len(set(copied)):
        raise ValueError("cards must be unique.")
    invalid = sorted(set(copied) - deck_set)
    if invalid:
        raise ValueError(f"Invalid cards: {invalid}")
    copied_set = set(copied)
    return tuple(card for card in deck if card in copied_set)


def _validate_finite_number(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{field_name} must be a finite number.")


@dataclass(frozen=True)
class ImmediateReplayCoachingCandidate:
    """One immutable Immediate candidate normalized for replay coaching."""

    card: str
    rank: int
    is_recommended: bool
    expected_point_swing: float
    objective_utility: float

    def __post_init__(self) -> None:
        if self.card not in get_full_deck():
            raise ValueError(f"Invalid Immediate candidate card: {self.card}")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank <= 0:
            raise ValueError("Immediate candidate rank must be a positive integer.")
        if not isinstance(self.is_recommended, bool):
            raise ValueError("Immediate candidate is_recommended must be a boolean.")
        _validate_finite_number(self.expected_point_swing, "expected_point_swing")
        _validate_finite_number(self.objective_utility, "objective_utility")


@dataclass(frozen=True)
class ImmediateReplayCoachingEvidence:
    """Immutable normalized evidence from one already completed Immediate analysis."""

    is_available: bool
    unavailable_reason: str | None
    recommended_card: str | None
    candidate_count: int
    candidates: tuple[ImmediateReplayCoachingCandidate, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.is_available, bool):
            raise ValueError("Immediate evidence is_available must be a boolean.")
        if not isinstance(self.candidates, tuple):
            raise TypeError("Immediate evidence candidates must be a tuple.")
        if (
            isinstance(self.candidate_count, bool)
            or not isinstance(self.candidate_count, int)
            or self.candidate_count < 0
        ):
            raise ValueError("Immediate candidate_count must be a non-negative integer.")
        if self.candidate_count != len(self.candidates):
            raise ValueError("Immediate candidate_count must match candidates.")
        cards = [candidate.card for candidate in self.candidates]
        if len(cards) != len(set(cards)):
            raise ValueError("Immediate candidate cards must be unique.")
        if [candidate.rank for candidate in self.candidates] != list(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("Immediate candidates must have contiguous ordered ranks.")
        if any(
            first.objective_utility < second.objective_utility
            for first, second in zip(self.candidates, self.candidates[1:], strict=False)
        ):
            raise ValueError("Immediate candidates must preserve existing objective ranking.")
        recommended = [candidate for candidate in self.candidates if candidate.is_recommended]
        if self.is_available:
            if self.unavailable_reason is not None:
                raise ValueError("Available Immediate evidence cannot have an unavailable reason.")
            if self.recommended_card is None or self.candidate_count == 0:
                raise ValueError("Available Immediate evidence requires candidates and a card.")
            if (
                len(recommended) != 1
                or recommended[0].card != self.recommended_card
                or recommended[0].rank != 1
            ):
                raise ValueError("Immediate evidence requires one rank-1 recommendation.")
        elif (
            not isinstance(self.unavailable_reason, str)
            or not self.unavailable_reason
            or self.recommended_card is not None
            or self.candidate_count != 0
            or self.candidates
        ):
            raise ValueError("Unavailable Immediate evidence cannot contain candidates or a card.")


def build_immediate_replay_coaching_evidence(
    *,
    legal_cards: list[str] | tuple[str, ...],
    analysis_report: list[dict[str, Any]],
    recommended_card: str | None,
    unavailable_reason: str | None,
    game_type: str,
    player_role: str,
    objective_values: dict[str, dict[str, float]] | None = None,
) -> ImmediateReplayCoachingEvidence:
    """Normalizes existing Immediate values without rerunning Immediate analysis."""
    canonical_legal_cards = canonicalize_replay_coaching_cards(legal_cards)
    report = [dict(row) for row in analysis_report]
    if recommended_card is None:
        if report:
            raise ValueError("Unavailable Immediate evidence cannot have an analysis report.")
        return ImmediateReplayCoachingEvidence(
            is_available=False,
            unavailable_reason=unavailable_reason or "immediate_analysis_unavailable",
            recommended_card=None,
            candidate_count=0,
            candidates=(),
        )
    if unavailable_reason is not None:
        raise ValueError("Available Immediate evidence cannot have an unavailable reason.")
    if game_type not in GAME_TYPES:
        raise ValueError(f"Invalid Immediate evidence game type: {game_type}")
    report_cards = [str(row.get("card")) for row in report]
    if set(report_cards) != set(canonical_legal_cards) or len(report_cards) != len(
        canonical_legal_cards
    ):
        raise ValueError("Immediate report cards must match the legal cards exactly.")
    marked_cards = [
        str(row["card"]) for row in report if row.get("is_recommended") is True
    ]
    if marked_cards != [recommended_card]:
        raise ValueError("Immediate report and recommendation are inconsistent.")

    copied_objective_values = (
        {card: dict(value) for card, value in objective_values.items()}
        if objective_values is not None
        else None
    )
    if copied_objective_values is not None and set(copied_objective_values) != set(
        canonical_legal_cards
    ):
        raise ValueError("Immediate objective values must match the legal cards exactly.")
    normalized_values = []
    for row in report:
        card = str(row["card"])
        expected_point_swing = float(row["expected_point_swing"])
        objective_utility = calculate_expected_objective_utility(
            game_type=game_type,
            player_role=player_role,
            value=(
                copied_objective_values[card]
                if copied_objective_values is not None
                else row
            ),
        )
        _validate_finite_number(expected_point_swing, "expected_point_swing")
        _validate_finite_number(objective_utility, "objective_utility")
        normalized_values.append((card, expected_point_swing, objective_utility))
    candidates = tuple(
        ImmediateReplayCoachingCandidate(
            card=card,
            rank=rank,
            is_recommended=card == recommended_card,
            expected_point_swing=expected_point_swing,
            objective_utility=objective_utility,
        )
        for rank, (card, expected_point_swing, objective_utility) in enumerate(
            normalized_values, start=1
        )
    )
    return ImmediateReplayCoachingEvidence(
        is_available=True,
        unavailable_reason=None,
        recommended_card=recommended_card,
        candidate_count=len(candidates),
        candidates=candidates,
    )


@dataclass(frozen=True)
class DecisionTimeReplayCoachingEvidence:
    """Version-1 evidence available before the observed card is attached."""

    contract_version: int
    information_policy: str
    source_game_id: str
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    local_side: str
    game_type: str
    root_seat: str
    game_phase: str
    legal_cards: tuple[str, ...]
    immediate_evidence: ImmediateReplayCoachingEvidence
    bounded_search_result: BoundedSearchResult
    search_vs_immediate_comparison: SearchVsImmediateComparison

    def __post_init__(self) -> None:
        if self.contract_version != REPLAY_COACHING_CONTRACT_VERSION:
            raise ValueError("Unsupported replay-coaching contract version.")
        if self.information_policy != REPLAY_COACHING_INFORMATION_POLICY:
            raise ValueError("Invalid replay-coaching information policy.")
        if (
            not isinstance(self.source_game_id, str)
            or not self.source_game_id
            or self.source_game_id != self.source_game_id.strip()
        ):
            raise ValueError("source_game_id must be a non-empty, non-padded string.")
        for field_name, value in (
            ("decision_index", self.decision_index),
            ("play_index", self.play_index),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer.")
        expected_phase = get_replay_coaching_game_phase(self.trick_number)
        if self.game_phase != expected_phase:
            raise ValueError("game_phase must match trick_number.")
        if self.play_index not in (1, 2, 3):
            raise ValueError("play_index must be 1, 2, or 3.")
        if self.decision_index != (self.trick_number - 1) * 3 + self.play_index:
            raise ValueError("decision_index must match trick_number and play_index.")
        if (
            not isinstance(self.acting_player_id, str)
            or not self.acting_player_id
            or self.acting_player_id != self.acting_player_id.strip()
        ):
            raise ValueError("acting_player_id must be a non-empty, non-padded string.")
        if self.acting_seat not in REPLAY_COACHING_ACTING_SEATS:
            raise ValueError(f"Invalid acting_seat: {self.acting_seat}")
        if self.local_side not in REPLAY_COACHING_LOCAL_SIDES:
            raise ValueError(f"Invalid local_side: {self.local_side}")
        if self.game_type not in GAME_TYPES:
            raise ValueError(f"Invalid replay-coaching game_type: {self.game_type}")
        if self.root_seat != REPLAY_COACHING_ROOT_SEATS[self.play_index - 1]:
            raise ValueError("root_seat must match play_index.")
        if not isinstance(self.legal_cards, tuple):
            raise TypeError("legal_cards must be a tuple.")
        if not self.legal_cards:
            raise ValueError("Replay-coaching evidence requires at least one legal card.")
        if self.legal_cards != canonicalize_replay_coaching_cards(self.legal_cards):
            raise ValueError("legal_cards must be unique and in canonical deck order.")
        if not isinstance(self.immediate_evidence, ImmediateReplayCoachingEvidence):
            raise ValueError("immediate_evidence must be ImmediateReplayCoachingEvidence.")
        if not isinstance(self.bounded_search_result, BoundedSearchResult):
            raise ValueError("bounded_search_result must be BoundedSearchResult.")
        if self.bounded_search_result.game_type != self.game_type:
            raise ValueError("Search and replay-coaching game types must match.")
        if self.bounded_search_result.status == "unavailable":
            if self.bounded_search_result.candidate_results:
                raise ValueError("Unavailable Search cannot contain candidates.")
        elif {candidate.card for candidate in self.bounded_search_result.candidate_results} != set(
            self.legal_cards
        ):
            raise ValueError("Search candidates must align with legal_cards.")
        immediate = self.immediate_evidence
        if immediate.is_available and {candidate.card for candidate in immediate.candidates} != set(
            self.legal_cards
        ):
            raise ValueError("Immediate candidates must align with legal_cards.")
        comparison = self.search_vs_immediate_comparison
        if not isinstance(comparison, SearchVsImmediateComparison):
            raise ValueError(
                "search_vs_immediate_comparison must be SearchVsImmediateComparison."
            )
        if comparison.search_card != self.bounded_search_result.recommended_card:
            raise ValueError("Search comparison card must match the Search recommendation.")
        if comparison.immediate_card != immediate.recommended_card:
            raise ValueError("Search comparison card must match the Immediate recommendation.")
        if comparison.is_available and not immediate.is_available:
            raise ValueError("Available Search comparison requires Immediate evidence.")
        if comparison.is_available and (
            self.bounded_search_result.consumed_budget.completed_world_count == 0
            or self.bounded_search_result.recommended_card is None
        ):
            raise ValueError("Available Search comparison requires completed aggregates.")
        immediate_report = [
            {
                "card": candidate.card,
                "win_rate": 1.0 - candidate.objective_utility,
                "average_points_won": candidate.expected_point_swing,
                "average_points_lost": 0.0,
                "expected_point_swing": candidate.expected_point_swing,
                "expected_objective_utility": candidate.objective_utility,
                "is_recommended": candidate.is_recommended,
            }
            for candidate in immediate.candidates
        ]
        expected_comparison = build_search_vs_immediate_comparison(
            self.bounded_search_result,
            immediate.recommended_card,
            immediate_report,
            self.game_type,
            "declarer" if self.local_side == "declarer" else "defender",
        )
        if comparison != expected_comparison:
            raise ValueError(
                "Search-versus-Immediate comparison must match the stored evidence."
            )


def build_decision_time_replay_coaching_evidence(
    *,
    source_game_id: str,
    decision_index: int,
    trick_number: int,
    play_index: int,
    acting_player_id: str,
    acting_seat: str,
    local_side: str,
    game_type: str,
    legal_cards: list[str] | tuple[str, ...],
    immediate_evidence: ImmediateReplayCoachingEvidence,
    bounded_search_result: BoundedSearchResult,
    search_vs_immediate_comparison: SearchVsImmediateComparison,
) -> DecisionTimeReplayCoachingEvidence:
    """Builds the immutable evidence contract without accepting an actual card."""
    return DecisionTimeReplayCoachingEvidence(
        contract_version=REPLAY_COACHING_CONTRACT_VERSION,
        information_policy=REPLAY_COACHING_INFORMATION_POLICY,
        source_game_id=source_game_id,
        decision_index=decision_index,
        trick_number=trick_number,
        play_index=play_index,
        acting_player_id=acting_player_id,
        acting_seat=acting_seat,
        local_side=local_side,
        game_type=game_type,
        root_seat=REPLAY_COACHING_ROOT_SEATS[play_index - 1] if play_index in (1, 2, 3) else "",
        game_phase=get_replay_coaching_game_phase(trick_number),
        legal_cards=canonicalize_replay_coaching_cards(legal_cards),
        immediate_evidence=immediate_evidence,
        bounded_search_result=bounded_search_result,
        search_vs_immediate_comparison=search_vs_immediate_comparison,
    )


def build_serializable_immediate_replay_coaching_evidence(
    evidence: ImmediateReplayCoachingEvidence,
) -> dict[str, Any]:
    return {
        "is_available": evidence.is_available,
        "unavailable_reason": evidence.unavailable_reason,
        "recommended_card": evidence.recommended_card,
        "candidate_count": evidence.candidate_count,
        "candidates": [
            {
                "card": candidate.card,
                "rank": candidate.rank,
                "is_recommended": candidate.is_recommended,
                "expected_point_swing": candidate.expected_point_swing,
                "objective_utility": candidate.objective_utility,
            }
            for candidate in evidence.candidates
        ],
    }


def build_serializable_decision_time_replay_coaching_evidence(
    evidence: DecisionTimeReplayCoachingEvidence,
) -> dict[str, Any]:
    """Serializes only decision-time evidence and aggregate Search diagnostics."""
    return {
        "contract_version": evidence.contract_version,
        "information_policy": evidence.information_policy,
        "source_game_id": evidence.source_game_id,
        "decision_index": evidence.decision_index,
        "trick_number": evidence.trick_number,
        "play_index": evidence.play_index,
        "acting_player_id": evidence.acting_player_id,
        "acting_seat": evidence.acting_seat,
        "local_side": evidence.local_side,
        "game_type": evidence.game_type,
        "root_seat": evidence.root_seat,
        "game_phase": evidence.game_phase,
        "legal_cards": list(evidence.legal_cards),
        "immediate_evidence": build_serializable_immediate_replay_coaching_evidence(
            evidence.immediate_evidence
        ),
        "bounded_search_result": build_serializable_bounded_search_result(
            evidence.bounded_search_result
        ),
        "search_vs_immediate_comparison": (
            build_serializable_search_vs_immediate_comparison(
                evidence.search_vs_immediate_comparison
            )
        ),
    }
