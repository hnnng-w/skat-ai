from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from skatmind.bounded_search_result import build_serializable_bounded_search_result
from skatmind.historical_information_set_search_review import (
    HistoricalInformationSetSearchDecisionReviewV1,
)
from skatmind.information_set_search_comparison import (
    InformationSetSearchComparisonPreActualAnalysisV1,
    InformationSetSearchComparisonV1,
    attach_actual_card_to_information_set_search_comparison_v1,
    build_information_set_search_comparison_pre_actual_analysis_v1,
)
from skatmind.replay_coaching_evidence import (
    REPLAY_COACHING_ACTING_SEATS,
    REPLAY_COACHING_LOCAL_SIDES,
    REPLAY_COACHING_ROOT_SEATS,
    canonicalize_replay_coaching_cards,
    get_replay_coaching_game_phase,
)
from skatmind.rules import GAME_TYPES

INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION = 1
INFORMATION_SET_REPLAY_COACHING_SOURCE_POLICY = (
    "retained_historical_information_set_search_review_without_rerun"
)
INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY = (
    "decision_time_analysis_then_actual_card_then_outcome_context"
)
INFORMATION_SET_REPLAY_COACHING_PRIMARY_EVIDENCE_POLICY = (
    "information_set_candidates_primary_pimc_and_immediate_diagnostic_only"
)
INFORMATION_SET_REPLAY_COACHING_PUBLIC_POLICY = (
    "safe_report_without_private_policy_world_or_observation"
)


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_value(item) for item in value)
    return value


def _thaw_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json_value(item) for item in value]
    return value


def _validate_positive_integer(value: object, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class InformationSetReplayCoachingDecisionTimeEvidenceV1:
    """Decision-time retained analysis without the observed Card or outcome."""

    information_set_replay_coaching_evidence_version: int
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
    remaining_tricks: int
    legal_cards: tuple[str, ...]
    information_set_pre_actual_analysis: (
        InformationSetSearchComparisonPreActualAnalysisV1
    )

    def __post_init__(self) -> None:
        if (
            isinstance(self.information_set_replay_coaching_evidence_version, bool)
            or not isinstance(
                self.information_set_replay_coaching_evidence_version, int
            )
            or self.information_set_replay_coaching_evidence_version
            != INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION
        ):
            raise ValueError("Unsupported information-set coaching evidence version.")
        if self.information_policy != INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY:
            raise ValueError("Unsupported information-set coaching information policy.")
        for field_name in ("source_game_id", "acting_player_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ValueError(f"{field_name} must be a non-empty, non-padded string.")
        for field_name in (
            "decision_index",
            "trick_number",
            "play_index",
            "remaining_tricks",
        ):
            _validate_positive_integer(getattr(self, field_name), field_name)
        if self.play_index not in (1, 2, 3):
            raise ValueError("play_index must be 1, 2, or 3.")
        if self.decision_index != (self.trick_number - 1) * 3 + self.play_index:
            raise ValueError("decision_index must match trick_number and play_index.")
        if self.acting_seat not in REPLAY_COACHING_ACTING_SEATS:
            raise ValueError("acting_seat is unsupported.")
        if self.local_side not in REPLAY_COACHING_LOCAL_SIDES:
            raise ValueError("local_side is unsupported.")
        if self.game_type not in GAME_TYPES:
            raise ValueError("game_type is unsupported.")
        if self.root_seat != REPLAY_COACHING_ROOT_SEATS[self.play_index - 1]:
            raise ValueError("root_seat must match play_index.")
        if self.game_phase != get_replay_coaching_game_phase(self.trick_number):
            raise ValueError("game_phase must match trick_number.")
        if not isinstance(self.legal_cards, tuple) or not self.legal_cards:
            raise ValueError("legal_cards must be a non-empty tuple.")
        if self.legal_cards != canonicalize_replay_coaching_cards(self.legal_cards):
            raise ValueError("legal_cards must be unique and in canonical deck order.")
        analysis = self.information_set_pre_actual_analysis
        if not isinstance(
            analysis,
            InformationSetSearchComparisonPreActualAnalysisV1,
        ):
            raise ValueError("information_set_pre_actual_analysis has the wrong type.")
        if (
            analysis.information_set_result is not None
            and analysis.information_set_result.game_type != self.game_type
        ):
            raise ValueError("Information-set Result game type must match the evidence.")
        if analysis.pimc_result is not None and (
            analysis.pimc_result.game_type != self.game_type
        ):
            raise ValueError("PIMC Result game type must match the evidence.")


def build_information_set_replay_coaching_decision_time_evidence_v1(
    decision: HistoricalInformationSetSearchDecisionReviewV1,
) -> InformationSetReplayCoachingDecisionTimeEvidenceV1:
    """Rebuilds retained pre-actual evidence without running any analysis."""
    if not isinstance(decision, HistoricalInformationSetSearchDecisionReviewV1):
        raise ValueError("decision has the wrong type.")
    analysis = build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=decision.information_set_result,
        information_set_public_result=decision.information_set_public_result,
        pimc_result=decision.pimc_result,
        immediate_recommended_card=decision.immediate_recommended_card,
        same_selected_world_sequence=(
            decision.comparison.same_selected_world_sequence
        ),
    )
    if analysis.information_set_public_result is not None:
        object.__setattr__(
            analysis,
            "information_set_public_result",
            _freeze_json_value(dict(analysis.information_set_public_result)),
        )
    return InformationSetReplayCoachingDecisionTimeEvidenceV1(
        information_set_replay_coaching_evidence_version=(
            INFORMATION_SET_REPLAY_COACHING_EVIDENCE_VERSION
        ),
        information_policy=INFORMATION_SET_REPLAY_COACHING_INFORMATION_POLICY,
        source_game_id=decision.source_game_id,
        decision_index=decision.decision_index,
        trick_number=decision.trick_number,
        play_index=decision.play_index,
        acting_player_id=decision.acting_player_id,
        acting_seat=decision.acting_seat,
        local_side=decision.acting_role,
        game_type=decision.contract,
        root_seat=REPLAY_COACHING_ROOT_SEATS[decision.play_index - 1],
        game_phase=get_replay_coaching_game_phase(decision.trick_number),
        remaining_tricks=decision.remaining_tricks,
        legal_cards=canonicalize_replay_coaching_cards(decision.legal_cards),
        information_set_pre_actual_analysis=analysis,
    )


def attach_retained_actual_card_to_information_set_replay_coaching_evidence_v1(
    evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1,
    *,
    actual_card: str,
    retained_comparison: InformationSetSearchComparisonV1,
) -> InformationSetSearchComparisonV1:
    """Attaches one legal observed Card and requires the retained comparison exactly."""
    if not isinstance(evidence, InformationSetReplayCoachingDecisionTimeEvidenceV1):
        raise ValueError("evidence has the wrong type.")
    if actual_card not in evidence.legal_cards:
        raise ValueError("actual_card must be legal at decision time.")
    comparison = attach_actual_card_to_information_set_search_comparison_v1(
        evidence.information_set_pre_actual_analysis,
        actual_card,
    )
    if comparison != retained_comparison:
        raise ValueError("The rebuilt comparison must equal the retained review comparison.")
    return comparison


def build_serializable_information_set_replay_coaching_decision_time_evidence_v1(
    evidence: InformationSetReplayCoachingDecisionTimeEvidenceV1,
) -> dict[str, Any]:
    """Serializes safe aggregates without the actual Card or private Search state."""
    if not isinstance(evidence, InformationSetReplayCoachingDecisionTimeEvidenceV1):
        raise ValueError("evidence has the wrong type.")
    analysis = evidence.information_set_pre_actual_analysis
    return {
        "information_set_replay_coaching_evidence_version": (
            evidence.information_set_replay_coaching_evidence_version
        ),
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
        "remaining_tricks": evidence.remaining_tricks,
        "legal_cards": list(evidence.legal_cards),
        "information_set_pre_actual_analysis": {
            "information_set_search_result": (
                _thaw_json_value(analysis.information_set_public_result)
                if analysis.information_set_public_result is not None
                else None
            ),
            "same_selection_pimc_result": (
                build_serializable_bounded_search_result(analysis.pimc_result)
                if analysis.pimc_result is not None
                else None
            ),
            "immediate_recommended_card": analysis.immediate_recommended_card,
            "same_selected_world_sequence": analysis.same_selected_world_sequence,
        },
    }
