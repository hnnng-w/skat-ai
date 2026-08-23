from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from skat_ai.bounded_search_information import (
    SearchInformationView,
    build_historical_search_information_view,
)
from skat_ai.bounded_search_result import (
    WORLD_COVERAGE_VALUES,
    BoundedSearchResult,
    build_serializable_bounded_search_result,
)
from skat_ai.compatible_world_minimax import (
    solve_compatible_world_minimax_on_selection_v1,
)
from skat_ai.effective_opponent_policy import (
    EffectiveOpponentPolicySettings,
    build_effective_opponent_policy_settings,
)
from skat_ai.historical_decision_snapshot import (
    HistoricalDecisionSnapshot,
    HistoricalDecisionSnapshotSummary,
    HistoricalSnapshotVisibleState,
)
from skat_ai.historical_game import HistoricalGameRecord
from skat_ai.historical_opponent_profile_application import (
    resolve_historical_opponent_profiles_for_decision,
)
from skat_ai.historical_opponent_profile_binding import (
    HistoricalOpponentProfileBindings,
)
from skat_ai.historical_snapshot_adapter import (
    HistoricalSnapshotPosition,
    build_position_from_historical_snapshot,
)
from skat_ai.information_set_search_comparison import (
    METHOD_NOT_AVAILABLE,
    InformationSetSearchComparisonPreActualAnalysisV1,
    InformationSetSearchComparisonV1,
    attach_actual_card_to_information_set_search_comparison_v1,
    build_information_set_search_comparison_pre_actual_analysis_v1,
    build_serializable_information_set_search_comparison_v1,
)
from skat_ai.information_set_search_contracts import (
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    INFORMATION_SET_SEARCH_STATUSES,
    InformationSetSearchBudgetV1,
    InformationSetSearchRequestV1,
    InformationSetSearchResultV1,
    build_information_set_search_request_v1,
)
from skat_ai.information_set_search_executor import execute_information_set_search_v1
from skat_ai.information_set_search_preparation import (
    InformationSetSearchPreparationV1,
    prepare_information_set_search_v1,
)
from skat_ai.information_set_search_public import (
    build_nondeterministic_fixed_policy_public_result_v1,
    build_public_information_set_search_result_v1,
)
from skat_ai.information_set_search_workflow import (
    build_information_set_search_policy_settings_v1,
    convert_information_set_search_budget_to_requested_search_budget_v1,
)
from skat_ai.recommender import recommend_card_by_expected_value
from skat_ai.rules import GAME_TYPES
from skat_ai.search_budget_profiles import (
    HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE,
    get_search_budget_profile,
)
from skat_ai.simulation import DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT

HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION = 1
HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD = (
    "information_set_search_with_same_selection_pimc_and_immediate_v1"
)
INFORMATION_SET_SEARCH_HISTORICAL_POLICY = (
    "one_pre_actual_execution_per_observed_decision"
)
INFORMATION_SET_SEARCH_PROFILE_POLICY = (
    "existing_profile_identifier_to_information_set_budget"
)
HISTORICAL_INFORMATION_SET_SEARCH_INFORMATION_POLICY = "decision_time"
HISTORICAL_INFORMATION_SET_SEARCH_DECISION_SEED_DOMAIN = (
    "historical_information_set_search_decision_v1"
)

HISTORICAL_ROLES = ("declarer", "defenders")
HISTORICAL_SEATS = ("forehand", "middlehand", "rearhand")
DECISION_PHASES = ("lead", "response")
RECOMMENDATION_AGREEMENT_VALUES = ("same", "different", "not_available")


def _validate_integer_seed(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer and must not be a boolean.")


def derive_historical_information_set_search_decision_seed(
    base_search_seed: int,
    stable_game_identity: str,
    decision_index: int,
) -> int:
    """Derives one process-stable Search seed from a Game Decision identity."""
    _validate_integer_seed(base_search_seed, "base_search_seed")
    if (
        not isinstance(stable_game_identity, str)
        or not stable_game_identity
        or stable_game_identity != stable_game_identity.strip()
    ):
        raise ValueError("stable_game_identity must be a non-empty, non-padded string.")
    if (
        isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index <= 0
    ):
        raise ValueError("decision_index must be a positive integer.")
    material = (
        f"skat-ai\0{base_search_seed}\0"
        f"{HISTORICAL_INFORMATION_SET_SEARCH_DECISION_SEED_DOMAIN}\0"
        f"{stable_game_identity}\0{decision_index}"
    ).encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def build_information_set_search_budget_from_profile_v1(
    profile_identifier: str,
) -> InformationSetSearchBudgetV1:
    """Maps an existing profile structurally to an Information-set budget."""
    profile = get_search_budget_profile(profile_identifier)
    return InformationSetSearchBudgetV1(
        information_set_search_budget_version=INFORMATION_SET_SEARCH_BUDGET_VERSION,
        max_remaining_tricks=min(3, profile.max_remaining_tricks),
        max_depth_plies=min(9, profile.max_depth_plies),
        max_state_nodes=profile.max_nodes,
        max_information_sets=profile.max_nodes,
        max_selected_worlds=profile.max_selected_worlds,
        max_sampled_worlds=profile.max_sampled_worlds,
        minimum_comparable_worlds=profile.minimum_comparable_worlds,
        wall_clock_timeout_ms=profile.wall_clock_timeout_ms,
    )


def build_historical_information_set_search_effective_policy_settings_v1(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    *,
    opponent_profile_bindings: HistoricalOpponentProfileBindings | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> EffectiveOpponentPolicySettings:
    """Resolves existing Historical profile and explicit-policy precedence."""
    left_profile = None
    right_profile = None
    data: dict[str, Any] = {}
    if opponent_profile_bindings is not None:
        profiles = resolve_historical_opponent_profiles_for_decision(
            historical_record,
            snapshot,
            opponent_profile_bindings.profiles_by_player_id,
        )
        left_profile = (
            profiles.left.profile
            if profiles.left is not None
            and profiles.left.derivation["actionable_policy_preset"] is not None
            else None
        )
        right_profile = (
            profiles.right.profile
            if profiles.right is not None
            and profiles.right.derivation["actionable_policy_preset"] is not None
            else None
        )
        data["use_profile_presets"] = True
    return build_effective_opponent_policy_settings(
        data=data,
        left_player_profile=left_profile,
        right_player_profile=right_profile,
        opponent_policy_preset_override=opponent_policy_preset_override,
        opponent_lead_policy_override=opponent_lead_policy_override,
        opponent_response_policy_override=opponent_response_policy_override,
        left_opponent_lead_policy_override=left_opponent_lead_policy_override,
        left_opponent_response_policy_override=left_opponent_response_policy_override,
        right_opponent_lead_policy_override=right_opponent_lead_policy_override,
        right_opponent_response_policy_override=right_opponent_response_policy_override,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchReviewSettingsV1:
    base_search_seed: int
    search_budget_profile: str = HISTORICAL_REVIEW_SEARCH_BUDGET_PROFILE
    immediate_sample_count: int = DEFAULT_IMMEDIATE_ANALYSIS_SAMPLE_COUNT
    immediate_base_random_seed: int | None = None

    def __post_init__(self) -> None:
        _validate_integer_seed(self.base_search_seed, "base_search_seed")
        if not isinstance(self.search_budget_profile, str) or not (
            self.search_budget_profile
        ):
            raise ValueError("search_budget_profile must be a non-empty string.")
        build_information_set_search_budget_from_profile_v1(
            self.search_budget_profile
        )
        if (
            isinstance(self.immediate_sample_count, bool)
            or not isinstance(self.immediate_sample_count, int)
            or self.immediate_sample_count <= 0
        ):
            raise ValueError("immediate_sample_count must be a positive integer.")
        if self.immediate_base_random_seed is not None:
            _validate_integer_seed(
                self.immediate_base_random_seed,
                "immediate_base_random_seed",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchDecisionInputV1:
    """Decision-time callback input with no observed Card or future Game record."""

    source_game_id: str
    source_played_at: str | None
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    acting_side: str
    information_cutoff: str
    relative_player_map: tuple[tuple[str, str], ...]
    visible_state: HistoricalSnapshotVisibleState
    declarer_player_id: str
    position: HistoricalSnapshotPosition
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings
    search_seed: int
    requested_budget: InformationSetSearchBudgetV1
    immediate_sample_count: int
    immediate_random_seed: int | None

    def __post_init__(self) -> None:
        if tuple(key for key, _value in self.relative_player_map) != (
            "me",
            "left",
            "right",
        ):
            raise ValueError("relative_player_map must use canonical relative order.")
        if self.information_cutoff != "before_actual_play":
            raise ValueError("Historical analysis requires the pre-play cutoff.")
        if self.acting_side not in HISTORICAL_ROLES:
            raise ValueError("Unsupported historical acting side.")
        if self.acting_seat not in HISTORICAL_SEATS:
            raise ValueError("Unsupported historical acting seat.")
        _validate_integer_seed(self.search_seed, "search_seed")
        if not isinstance(self.requested_budget, InformationSetSearchBudgetV1):
            raise ValueError("requested_budget must be InformationSetSearchBudgetV1.")
        if not isinstance(self.position, HistoricalSnapshotPosition):
            raise ValueError("position must be a HistoricalSnapshotPosition.")
        if not isinstance(
            self.effective_opponent_policy_settings,
            EffectiveOpponentPolicySettings,
        ):
            raise ValueError(
                "effective_opponent_policy_settings has the wrong type."
            )


HistoricalInformationSetSearchPreActualBuilder = Callable[
    [HistoricalInformationSetSearchDecisionInputV1],
    InformationSetSearchComparisonPreActualAnalysisV1,
]


@dataclass(frozen=True, slots=True)
class HistoricalInformationSetSearchPreActualDependenciesV1:
    """Focused stage seams for one production pre-actual analysis."""

    build_information_view: Callable[
        [HistoricalSnapshotPosition], SearchInformationView
    ] = build_historical_search_information_view
    build_request: Callable[..., InformationSetSearchRequestV1] = (
        build_information_set_search_request_v1
    )
    prepare_search: Callable[
        [InformationSetSearchRequestV1], InformationSetSearchPreparationV1
    ] = prepare_information_set_search_v1
    execute_search: Callable[
        [InformationSetSearchPreparationV1], InformationSetSearchResultV1
    ] = execute_information_set_search_v1
    solve_same_selection_pimc: Callable[..., BoundedSearchResult] = (
        solve_compatible_world_minimax_on_selection_v1
    )
    recommend_immediate: Callable[
        ..., tuple[str, str, dict[str, dict[str, float]]]
    ] = (
        recommend_card_by_expected_value
    )


_DEFAULT_PRE_ACTUAL_DEPENDENCIES = (
    HistoricalInformationSetSearchPreActualDependenciesV1()
)


def build_historical_information_set_search_pre_actual_analysis_v1(
    decision_input: HistoricalInformationSetSearchDecisionInputV1,
    *,
    dependencies: HistoricalInformationSetSearchPreActualDependenciesV1 = (
        _DEFAULT_PRE_ACTUAL_DEPENDENCIES
    ),
) -> InformationSetSearchComparisonPreActualAnalysisV1:
    """Runs strict Search, retained-selection PIMC, and independent Immediate."""
    if not isinstance(decision_input, HistoricalInformationSetSearchDecisionInputV1):
        raise ValueError("decision_input has the wrong type.")
    if not isinstance(
        dependencies,
        HistoricalInformationSetSearchPreActualDependenciesV1,
    ):
        raise ValueError("dependencies have the wrong type.")

    information_view = dependencies.build_information_view(decision_input.position)
    policy_settings = build_information_set_search_policy_settings_v1(
        decision_input.effective_opponent_policy_settings
    )
    information_set_result = None
    information_set_public_result = None
    pimc_result = None
    same_selected_world_sequence = False
    if policy_settings is not None:
        request = dependencies.build_request(
            information_view=information_view,
            requested_budget=decision_input.requested_budget,
            world_selection_seed=decision_input.search_seed,
            policy_settings=policy_settings,
        )
        preparation = dependencies.prepare_search(request)
        information_set_result = dependencies.execute_search(preparation)
        information_set_public_result = build_public_information_set_search_result_v1(
            information_set_result
        )
        selection = preparation.world_selection
        if selection is not None and selection.available:
            pimc_result = dependencies.solve_same_selection_pimc(
                information_view=information_view,
                requested_budget=(
                    convert_information_set_search_budget_to_requested_search_budget_v1(
                        decision_input.requested_budget
                    )
                ),
                selection=selection,
            )
            same_selected_world_sequence = True
    else:
        information_set_public_result = (
            build_nondeterministic_fixed_policy_public_result_v1(
                game_type=information_view.game_type,
                requested_budget=decision_input.requested_budget,
                effective_policy_settings=(
                    decision_input.effective_opponent_policy_settings
                ),
            )
        )

    immediate_recommended_card, _reason, _values = dependencies.recommend_immediate(
        state=decision_input.position.state,
        left_hand_size=decision_input.position.left_hand_size,
        right_hand_size=decision_input.position.right_hand_size,
        sample_count=decision_input.immediate_sample_count,
        random_seed=decision_input.immediate_random_seed,
        opponent_response_policy_by_player=(
            decision_input.effective_opponent_policy_settings.immediate_response_policy_by_player
        ),
        public_hand_constraints=decision_input.position.public_hand_constraints,
    )
    return build_information_set_search_comparison_pre_actual_analysis_v1(
        information_set_result=information_set_result,
        pimc_result=pimc_result,
        immediate_recommended_card=immediate_recommended_card,
        same_selected_world_sequence=same_selected_world_sequence,
        information_set_public_result=information_set_public_result,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchDecisionReviewV1:
    source_game_id: str
    source_played_at: str | None
    decision_index: int
    trick_number: int
    play_index: int
    acting_player_id: str
    acting_seat: str
    acting_role: str
    contract: str
    decision_phase: str
    remaining_tricks: int
    legal_cards: tuple[str, ...]
    actual_card: str
    effective_immediate_random_seed: int | None
    information_set_result: InformationSetSearchResultV1 | None
    information_set_public_result: Mapping[str, Any] | None
    pimc_result: BoundedSearchResult | None
    immediate_recommended_card: str | None
    comparison: InformationSetSearchComparisonV1

    @property
    def information_set_status(self) -> str:
        if self.information_set_result is None:
            if self.information_set_public_result is None:
                return METHOD_NOT_AVAILABLE
            status = self.information_set_public_result.get("status")
            return status if isinstance(status, str) else METHOD_NOT_AVAILABLE
        return self.information_set_result.status

    @property
    def world_coverage(self) -> str:
        if self.information_set_result is None:
            if self.information_set_public_result is None:
                return "none"
            coverage = self.information_set_public_result.get("world_coverage")
            return coverage if isinstance(coverage, str) else "none"
        return self.information_set_result.world_coverage

    @property
    def recommendation_agreement(self) -> str:
        same = self.comparison.information_set_pimc_same_card
        if same is None:
            return "not_available"
        return "same" if same else "different"


@dataclass(frozen=True, slots=True, kw_only=True)
class AgreementCountsV1:
    comparable_decision_count: int
    same_card_count: int
    different_card_count: int

    def __post_init__(self) -> None:
        if (
            self.same_card_count + self.different_card_count
            != self.comparable_decision_count
        ):
            raise ValueError("Agreement counts do not reconcile.")


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchMetricsV1:
    decision_count: int
    status_counts: tuple[tuple[str, int], ...]
    coverage_counts: tuple[tuple[str, int], ...]
    same_selected_world_sequence_count: int
    selected_world_count_total: int
    sampled_world_count_total: int
    comparison_available_count: int
    comparison_unavailable_count: int
    information_set_recommendation_count: int
    pimc_recommendation_count: int
    immediate_recommendation_count: int
    information_set_pimc_agreement: AgreementCountsV1
    information_set_immediate_agreement: AgreementCountsV1
    pimc_immediate_agreement: AgreementCountsV1
    information_set_actual_agreement: AgreementCountsV1
    pimc_actual_agreement: AgreementCountsV1
    immediate_actual_agreement: AgreementCountsV1

    def __post_init__(self) -> None:
        if sum(count for _value, count in self.status_counts) != self.decision_count:
            raise ValueError("Information-set status counts do not reconcile.")
        if sum(count for _value, count in self.coverage_counts) != self.decision_count:
            raise ValueError("Information-set coverage counts do not reconcile.")
        if (
            self.comparison_available_count + self.comparison_unavailable_count
            != self.decision_count
        ):
            raise ValueError("Comparison availability counts do not reconcile.")


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchBreakdownRowV1:
    value: str
    metrics: HistoricalInformationSetSearchMetricsV1


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchBreakdownV1:
    output_name: str
    field_name: str
    rows: tuple[HistoricalInformationSetSearchBreakdownRowV1, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class HistoricalInformationSetSearchReviewSummaryV1:
    schema_version: int
    review_method: str
    information_policy: str
    source_game_id: str
    game_end_reason: str
    settings: HistoricalInformationSetSearchReviewSettingsV1
    metrics: HistoricalInformationSetSearchMetricsV1
    breakdowns: tuple[HistoricalInformationSetSearchBreakdownV1, ...]
    decisions: tuple[HistoricalInformationSetSearchDecisionReviewV1, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version
            != HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION
        ):
            raise ValueError("Unsupported historical information-set review version.")
        if self.review_method != HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD:
            raise ValueError("Unsupported historical information-set review method.")
        if self.information_policy != (
            HISTORICAL_INFORMATION_SET_SEARCH_INFORMATION_POLICY
        ):
            raise ValueError("Unsupported historical information policy.")
        if self.metrics.decision_count != len(self.decisions):
            raise ValueError("Historical decision count does not reconcile.")


def _decision_input(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    settings: HistoricalInformationSetSearchReviewSettingsV1,
    stable_game_identity: str,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings,
) -> HistoricalInformationSetSearchDecisionInputV1:
    immediate_seed = (
        None
        if settings.immediate_base_random_seed is None
        else settings.immediate_base_random_seed + snapshot.decision_index - 1
    )
    relative_order = ("me", "left", "right")
    return HistoricalInformationSetSearchDecisionInputV1(
        source_game_id=snapshot.source_game_id,
        source_played_at=snapshot.source_played_at,
        decision_index=snapshot.decision_index,
        trick_number=snapshot.trick_number,
        play_index=snapshot.play_index,
        acting_player_id=snapshot.acting_player_id,
        acting_seat=snapshot.acting_seat,
        acting_side=snapshot.acting_side,
        information_cutoff=snapshot.information_cutoff,
        relative_player_map=tuple(
            (key, snapshot.relative_player_map[key]) for key in relative_order
        ),
        visible_state=snapshot.visible_state,
        declarer_player_id=historical_record.declarer_player_id,
        position=build_position_from_historical_snapshot(snapshot, historical_record),
        effective_opponent_policy_settings=effective_opponent_policy_settings,
        search_seed=derive_historical_information_set_search_decision_seed(
            settings.base_search_seed,
            stable_game_identity,
            snapshot.decision_index,
        ),
        requested_budget=build_information_set_search_budget_from_profile_v1(
            settings.search_budget_profile
        ),
        immediate_sample_count=settings.immediate_sample_count,
        immediate_random_seed=immediate_seed,
    )


def build_historical_information_set_search_decision_review_v1(
    snapshot: HistoricalDecisionSnapshot,
    historical_record: HistoricalGameRecord,
    settings: HistoricalInformationSetSearchReviewSettingsV1,
    *,
    pre_actual_analysis_builder: HistoricalInformationSetSearchPreActualBuilder = (
        build_historical_information_set_search_pre_actual_analysis_v1
    ),
    stable_game_identity: str | None = None,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
) -> HistoricalInformationSetSearchDecisionReviewV1:
    """Builds one row by running an isolated callback before Card attachment."""
    if not isinstance(snapshot, HistoricalDecisionSnapshot):
        raise ValueError("snapshot must be a HistoricalDecisionSnapshot.")
    if not isinstance(historical_record, HistoricalGameRecord):
        raise ValueError("historical_record must be a HistoricalGameRecord.")
    if not isinstance(settings, HistoricalInformationSetSearchReviewSettingsV1):
        raise ValueError("settings have the wrong type.")
    if snapshot.source_game_id != historical_record.game_id:
        raise ValueError("Historical snapshot and record game IDs must match.")
    decision_input = _decision_input(
        snapshot,
        historical_record,
        settings,
        stable_game_identity or historical_record.game_id,
        effective_opponent_policy_settings
        or build_historical_information_set_search_effective_policy_settings_v1(
            snapshot,
            historical_record,
        ),
    )
    analysis = pre_actual_analysis_builder(decision_input)
    if not isinstance(
        analysis,
        InformationSetSearchComparisonPreActualAnalysisV1,
    ):
        raise ValueError("The pre-actual builder returned an invalid analysis.")
    comparison = attach_actual_card_to_information_set_search_comparison_v1(
        analysis,
        snapshot.actual_card_played,
    )
    opponent_sizes = tuple(
        item.remaining_card_count
        for item in snapshot.visible_state.opponent_hand_sizes
    )
    remaining_tricks = max(
        len(snapshot.visible_state.own_hand),
        *opponent_sizes,
    )
    return HistoricalInformationSetSearchDecisionReviewV1(
        source_game_id=snapshot.source_game_id,
        source_played_at=snapshot.source_played_at,
        decision_index=snapshot.decision_index,
        trick_number=snapshot.trick_number,
        play_index=snapshot.play_index,
        acting_player_id=snapshot.acting_player_id,
        acting_seat=snapshot.acting_seat,
        acting_role=snapshot.acting_side,
        contract=snapshot.visible_state.game_type,
        decision_phase=(
            "response" if snapshot.visible_state.current_trick else "lead"
        ),
        remaining_tricks=remaining_tricks,
        legal_cards=tuple(snapshot.visible_state.legal_cards),
        actual_card=snapshot.actual_card_played,
        effective_immediate_random_seed=decision_input.immediate_random_seed,
        information_set_result=analysis.information_set_result,
        information_set_public_result=analysis.information_set_public_result,
        pimc_result=analysis.pimc_result,
        immediate_recommended_card=analysis.immediate_recommended_card,
        comparison=comparison,
    )


def _agreement_counts(values: tuple[bool | None, ...]) -> AgreementCountsV1:
    comparable = tuple(value for value in values if value is not None)
    same_count = sum(value is True for value in comparable)
    return AgreementCountsV1(
        comparable_decision_count=len(comparable),
        same_card_count=same_count,
        different_card_count=len(comparable) - same_count,
    )


def _ordered_counts(
    values: tuple[str, ...],
    preferred_order: tuple[str, ...],
) -> tuple[tuple[str, int], ...]:
    extras = tuple(sorted(set(values) - set(preferred_order)))
    order = (*preferred_order, *extras)
    return tuple((value, values.count(value)) for value in order if value in values)


def build_historical_information_set_search_metrics_v1(
    decisions: tuple[HistoricalInformationSetSearchDecisionReviewV1, ...],
) -> HistoricalInformationSetSearchMetricsV1:
    comparisons = tuple(decision.comparison for decision in decisions)
    return HistoricalInformationSetSearchMetricsV1(
        decision_count=len(decisions),
        status_counts=_ordered_counts(
            tuple(decision.information_set_status for decision in decisions),
            (*INFORMATION_SET_SEARCH_STATUSES, METHOD_NOT_AVAILABLE),
        ),
        coverage_counts=_ordered_counts(
            tuple(decision.world_coverage for decision in decisions),
            WORLD_COVERAGE_VALUES,
        ),
        same_selected_world_sequence_count=sum(
            comparison.same_selected_world_sequence for comparison in comparisons
        ),
        selected_world_count_total=sum(
            comparison.selected_world_count for comparison in comparisons
        ),
        sampled_world_count_total=sum(
            comparison.sampled_world_count for comparison in comparisons
        ),
        comparison_available_count=sum(
            comparison.comparison_status == "available"
            for comparison in comparisons
        ),
        comparison_unavailable_count=sum(
            comparison.comparison_status == "unavailable"
            for comparison in comparisons
        ),
        information_set_recommendation_count=sum(
            comparison.information_set_recommended_card is not None
            for comparison in comparisons
        ),
        pimc_recommendation_count=sum(
            comparison.pimc_recommended_card is not None
            for comparison in comparisons
        ),
        immediate_recommendation_count=sum(
            comparison.immediate_recommended_card is not None
            for comparison in comparisons
        ),
        information_set_pimc_agreement=_agreement_counts(
            tuple(
                comparison.information_set_pimc_same_card
                for comparison in comparisons
            )
        ),
        information_set_immediate_agreement=_agreement_counts(
            tuple(
                comparison.information_set_immediate_same_card
                for comparison in comparisons
            )
        ),
        pimc_immediate_agreement=_agreement_counts(
            tuple(comparison.pimc_immediate_same_card for comparison in comparisons)
        ),
        information_set_actual_agreement=_agreement_counts(
            tuple(
                comparison.information_set_actual_same_card
                for comparison in comparisons
            )
        ),
        pimc_actual_agreement=_agreement_counts(
            tuple(comparison.pimc_actual_same_card for comparison in comparisons)
        ),
        immediate_actual_agreement=_agreement_counts(
            tuple(
                comparison.immediate_actual_same_card
                for comparison in comparisons
            )
        ),
    )


def _decision_field(
    decision: HistoricalInformationSetSearchDecisionReviewV1,
    field_name: str,
) -> str:
    if field_name == "information_set_status":
        return decision.information_set_status
    if field_name == "world_coverage":
        return decision.world_coverage
    if field_name == "recommendation_agreement":
        return decision.recommendation_agreement
    value = getattr(decision, field_name)
    if not isinstance(value, str):
        raise ValueError("Historical breakdown fields must be strings.")
    return value


def _breakdown(
    decisions: tuple[HistoricalInformationSetSearchDecisionReviewV1, ...],
    *,
    output_name: str,
    field_name: str,
    preferred_order: tuple[str, ...],
) -> HistoricalInformationSetSearchBreakdownV1:
    observed = tuple(_decision_field(decision, field_name) for decision in decisions)
    extras = tuple(sorted(set(observed) - set(preferred_order)))
    values = tuple(
        value for value in (*preferred_order, *extras) if value in observed
    )
    return HistoricalInformationSetSearchBreakdownV1(
        output_name=output_name,
        field_name=field_name,
        rows=tuple(
            HistoricalInformationSetSearchBreakdownRowV1(
                value=value,
                metrics=build_historical_information_set_search_metrics_v1(
                    tuple(
                        decision
                        for decision in decisions
                        if _decision_field(decision, field_name) == value
                    )
                ),
            )
            for value in values
        ),
    )


def build_historical_information_set_search_breakdowns_v1(
    decisions: tuple[HistoricalInformationSetSearchDecisionReviewV1, ...],
) -> tuple[HistoricalInformationSetSearchBreakdownV1, ...]:
    return (
        _breakdown(
            decisions,
            output_name="by_contract",
            field_name="contract",
            preferred_order=tuple(GAME_TYPES),
        ),
        _breakdown(
            decisions,
            output_name="by_role",
            field_name="acting_role",
            preferred_order=HISTORICAL_ROLES,
        ),
        _breakdown(
            decisions,
            output_name="by_seat",
            field_name="acting_seat",
            preferred_order=HISTORICAL_SEATS,
        ),
        _breakdown(
            decisions,
            output_name="by_phase",
            field_name="decision_phase",
            preferred_order=DECISION_PHASES,
        ),
        _breakdown(
            decisions,
            output_name="by_status",
            field_name="information_set_status",
            preferred_order=(*INFORMATION_SET_SEARCH_STATUSES, METHOD_NOT_AVAILABLE),
        ),
        _breakdown(
            decisions,
            output_name="by_coverage",
            field_name="world_coverage",
            preferred_order=WORLD_COVERAGE_VALUES,
        ),
        _breakdown(
            decisions,
            output_name="by_recommendation_agreement",
            field_name="recommendation_agreement",
            preferred_order=RECOMMENDATION_AGREEMENT_VALUES,
        ),
    )


def build_historical_information_set_search_review_v1(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    settings: HistoricalInformationSetSearchReviewSettingsV1,
    *,
    pre_actual_analysis_builder: HistoricalInformationSetSearchPreActualBuilder = (
        build_historical_information_set_search_pre_actual_analysis_v1
    ),
    effective_policy_settings_by_decision: Mapping[
        int, EffectiveOpponentPolicySettings
    ]
    | None = None,
) -> HistoricalInformationSetSearchReviewSummaryV1:
    """Builds exactly one row per observed Card and no terminal-event row."""
    if not isinstance(snapshot_summary, HistoricalDecisionSnapshotSummary):
        raise ValueError("snapshot_summary has the wrong type.")
    cardinality = snapshot_summary.cardinality
    if historical_record.game_end_reason != cardinality.game_end_reason:
        raise ValueError("Historical information-set review end reasons do not match.")
    if (
        snapshot_summary.snapshot_count
        != cardinality.expected_review_decision_count
        or len(snapshot_summary.snapshots)
        != cardinality.expected_review_decision_count
    ):
        raise ValueError(
            "Historical information-set review snapshot count does not reconcile."
        )
    if effective_policy_settings_by_decision is not None:
        expected_indexes = {
            snapshot.decision_index for snapshot in snapshot_summary.snapshots
        }
        if set(effective_policy_settings_by_decision) != expected_indexes or any(
            not isinstance(settings, EffectiveOpponentPolicySettings)
            for settings in effective_policy_settings_by_decision.values()
        ):
            raise ValueError(
                "Effective policy settings must cover each Historical decision exactly."
            )
    decisions = tuple(
        build_historical_information_set_search_decision_review_v1(
            snapshot,
            historical_record,
            settings,
            pre_actual_analysis_builder=pre_actual_analysis_builder,
            stable_game_identity=historical_record.game_id,
            effective_opponent_policy_settings=(
                effective_policy_settings_by_decision[snapshot.decision_index]
                if effective_policy_settings_by_decision is not None
                else None
            ),
        )
        for snapshot in snapshot_summary.snapshots
    )
    metrics = build_historical_information_set_search_metrics_v1(decisions)
    breakdowns = build_historical_information_set_search_breakdowns_v1(decisions)
    for breakdown in breakdowns:
        if sum(row.metrics.decision_count for row in breakdown.rows) != len(
            decisions
        ):
            raise ValueError(
                f"{breakdown.output_name} decision counts do not reconcile."
            )
    return HistoricalInformationSetSearchReviewSummaryV1(
        schema_version=HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_VERSION,
        review_method=HISTORICAL_INFORMATION_SET_SEARCH_REVIEW_METHOD,
        information_policy=HISTORICAL_INFORMATION_SET_SEARCH_INFORMATION_POLICY,
        source_game_id=historical_record.game_id,
        game_end_reason=historical_record.game_end_reason,
        settings=settings,
        metrics=metrics,
        breakdowns=breakdowns,
        decisions=decisions,
    )


def build_serializable_historical_information_set_search_review_settings_v1(
    settings: HistoricalInformationSetSearchReviewSettingsV1,
) -> dict[str, Any]:
    return {
        "base_search_seed": settings.base_search_seed,
        "search_budget_profile": settings.search_budget_profile,
        "requested_budget": build_information_set_search_budget_from_profile_v1(
            settings.search_budget_profile
        ).to_dict(),
        "immediate_sample_count": settings.immediate_sample_count,
        "immediate_base_random_seed": settings.immediate_base_random_seed,
    }


def _serialize_agreement(value: AgreementCountsV1) -> dict[str, int]:
    return {
        "comparable_decision_count": value.comparable_decision_count,
        "same_card_count": value.same_card_count,
        "different_card_count": value.different_card_count,
    }


def build_serializable_historical_information_set_search_metrics_v1(
    metrics: HistoricalInformationSetSearchMetricsV1,
) -> dict[str, Any]:
    return {
        "decision_count": metrics.decision_count,
        "status_counts": dict(metrics.status_counts),
        "coverage_counts": dict(metrics.coverage_counts),
        "same_selected_world_sequence_count": (
            metrics.same_selected_world_sequence_count
        ),
        "selected_world_count_total": metrics.selected_world_count_total,
        "sampled_world_count_total": metrics.sampled_world_count_total,
        "comparison_available_count": metrics.comparison_available_count,
        "comparison_unavailable_count": metrics.comparison_unavailable_count,
        "information_set_recommendation_count": (
            metrics.information_set_recommendation_count
        ),
        "pimc_recommendation_count": metrics.pimc_recommendation_count,
        "immediate_recommendation_count": metrics.immediate_recommendation_count,
        "information_set_pimc_agreement": _serialize_agreement(
            metrics.information_set_pimc_agreement
        ),
        "information_set_immediate_agreement": _serialize_agreement(
            metrics.information_set_immediate_agreement
        ),
        "pimc_immediate_agreement": _serialize_agreement(
            metrics.pimc_immediate_agreement
        ),
        "information_set_actual_agreement": _serialize_agreement(
            metrics.information_set_actual_agreement
        ),
        "pimc_actual_agreement": _serialize_agreement(
            metrics.pimc_actual_agreement
        ),
        "immediate_actual_agreement": _serialize_agreement(
            metrics.immediate_actual_agreement
        ),
    }


def build_serializable_historical_information_set_search_decision_v1(
    decision: HistoricalInformationSetSearchDecisionReviewV1,
) -> dict[str, Any]:
    result = {
        "source_game_id": decision.source_game_id,
        "decision_index": decision.decision_index,
        "trick_number": decision.trick_number,
        "play_index": decision.play_index,
        "acting_player_id": decision.acting_player_id,
        "acting_seat": decision.acting_seat,
        "acting_role": decision.acting_role,
        "contract": decision.contract,
        "decision_phase": decision.decision_phase,
        "remaining_tricks": decision.remaining_tricks,
        "actual_card": decision.actual_card,
        "information_set_search_result": (
            dict(decision.information_set_public_result)
            if decision.information_set_public_result is not None
            else None
        ),
        "same_selection_pimc_result": (
            build_serializable_bounded_search_result(decision.pimc_result)
            if decision.pimc_result is not None
            else None
        ),
        "immediate_baseline": {
            "effective_random_seed": decision.effective_immediate_random_seed,
            "recommended_card": decision.immediate_recommended_card,
        },
        "comparison": build_serializable_information_set_search_comparison_v1(
            decision.comparison
        ),
    }
    if decision.source_played_at is not None:
        result["source_played_at"] = decision.source_played_at
    return result


def _serialize_breakdowns(
    breakdowns: tuple[HistoricalInformationSetSearchBreakdownV1, ...],
) -> dict[str, list[dict[str, Any]]]:
    return {
        breakdown.output_name: [
            {
                breakdown.field_name: row.value,
                "metrics": (
                    build_serializable_historical_information_set_search_metrics_v1(
                        row.metrics
                    )
                ),
            }
            for row in breakdown.rows
        ]
        for breakdown in breakdowns
    }


def build_serializable_historical_information_set_search_review_v1(
    summary: HistoricalInformationSetSearchReviewSummaryV1,
) -> dict[str, Any]:
    if not isinstance(summary, HistoricalInformationSetSearchReviewSummaryV1):
        raise ValueError("summary has the wrong type.")
    return {
        "schema_version": summary.schema_version,
        "review_method": summary.review_method,
        "information_policy": summary.information_policy,
        "source_game_id": summary.source_game_id,
        "game_end_reason": summary.game_end_reason,
        "settings": (
            build_serializable_historical_information_set_search_review_settings_v1(
                summary.settings
            )
        ),
        **build_serializable_historical_information_set_search_metrics_v1(
            summary.metrics
        ),
        "breakdowns": _serialize_breakdowns(summary.breakdowns),
        "decisions": [
            build_serializable_historical_information_set_search_decision_v1(
                decision
            )
            for decision in summary.decisions
        ],
    }


def build_historical_information_set_search_review_summary_v1(
    snapshot_summary: HistoricalDecisionSnapshotSummary,
    historical_record: HistoricalGameRecord,
    settings: HistoricalInformationSetSearchReviewSettingsV1,
    *,
    pre_actual_analysis_builder: HistoricalInformationSetSearchPreActualBuilder = (
        build_historical_information_set_search_pre_actual_analysis_v1
    ),
    effective_policy_settings_by_decision: Mapping[
        int, EffectiveOpponentPolicySettings
    ]
    | None = None,
) -> dict[str, Any]:
    """Application-friendly immutable-build plus fresh-serialization entry point."""
    summary = build_historical_information_set_search_review_v1(
        snapshot_summary,
        historical_record,
        settings,
        pre_actual_analysis_builder=pre_actual_analysis_builder,
        effective_policy_settings_by_decision=effective_policy_settings_by_decision,
    )
    return build_serializable_historical_information_set_search_review_v1(summary)
