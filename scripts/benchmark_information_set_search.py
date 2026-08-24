from __future__ import annotations

import argparse
import json
import math
import platform
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_PATH = (
    PROJECT_ROOT / "benchmarks" / "information_set_search_late_game_v1.json"
)

INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_SCHEMA_VERSION = 1
INFORMATION_SET_SEARCH_BENCHMARK_OUTPUT_VERSION = 1
INFORMATION_SET_SEARCH_BENCHMARK_NAME = (
    "information_set_search_selected_world_performance_v1"
)
INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_NAME = "information_set_search_late_game_v1"

INFORMATION_SET_SEARCH_BENCHMARK_FUNCTIONAL_POLICY = (
    "frozen_functional_and_structural_signature"
)
INFORMATION_SET_SEARCH_BENCHMARK_BASELINE_POLICY = (
    "same_selection_pimc_and_independent_immediate_diagnostic_only"
)
INFORMATION_SET_SEARCH_BENCHMARK_WEIGHT_POLICY = (
    "sampled_duplicate_draw_weight_is_preserved"
)
INFORMATION_SET_SEARCH_BENCHMARK_TIMING_POLICY = (
    "local_wall_clock_reference_without_cross_machine_gate"
)
INFORMATION_SET_SEARCH_BENCHMARK_PRIVACY_POLICY = (
    "synthetic_fixture_without_public_or_user_data"
)
INFORMATION_SET_SEARCH_BENCHMARK_COMPATIBILITY_POLICY = (
    "no_routing_profile_or_public_contract_change"
)

INFORMATION_SET_SEARCH_BENCHMARK_POLICIES = {
    "functional": INFORMATION_SET_SEARCH_BENCHMARK_FUNCTIONAL_POLICY,
    "baseline": INFORMATION_SET_SEARCH_BENCHMARK_BASELINE_POLICY,
    "weight": INFORMATION_SET_SEARCH_BENCHMARK_WEIGHT_POLICY,
    "timing": INFORMATION_SET_SEARCH_BENCHMARK_TIMING_POLICY,
    "privacy": INFORMATION_SET_SEARCH_BENCHMARK_PRIVACY_POLICY,
    "compatibility": INFORMATION_SET_SEARCH_BENCHMARK_COMPATIBILITY_POLICY,
}

INFORMATION_SET_SEARCH_BENCHMARK_CASE_NAMES = (
    "clubs_declarer_lead_sampled_three_tricks",
    "grand_defender_second_seat_exhaustive_two_tricks",
    "null_defender_third_seat_exhaustive_one_trick",
    "null_hand_declarer_lead_exhaustive_two_tricks",
    "null_ouvert_defender_second_seat_sampled_two_tricks",
    "null_hand_ouvert_declarer_third_seat_exhaustive_one_trick",
    "clubs_strategy_fusion_sampled_two_tricks",
    "grand_sampled_duplicate_weight_two_tricks",
)

_ROOT_FIELDS = {"schema_version", "corpus_name", "cases"}
_CASE_FIELDS = {
    "name",
    "declaration",
    "actor",
    "fixture",
    "profile_name",
    "world_selection_seed",
    "immediate_seed",
    "immediate_sample_count",
    "immediate_use_basic_opponent_strategy",
    "immediate_response_policy_by_player",
    "fixed_player_policies",
    "expected_information_set_signature",
    "expected_same_selection_pimc_signature",
    "expected_immediate_signature",
    "expected_descriptive_comparison",
    "expected_strategy_fusion_diagnostic",
    "expected_sampled_duplicate_diagnostic",
}
_DECLARATION_FIELDS = {
    "game_type",
    "hand_game",
    "ouvert",
    "schneider_announced",
    "schwarz_announced",
    "matadors",
    "bid_value",
}
_ACTOR_FIELDS = {"player_role", "declarer_player", "turn_phase"}
_FIXTURE_FIELDS = {
    "initial_hands",
    "skat",
    "initial_next_player",
    "replayed_cards",
    "public_hand_players",
}
_FIXED_POLICY_FIELDS = {"player", "lead_policy", "response_policy", "tie_policy"}
_CANDIDATE_FIELDS = {
    "card",
    "rank",
    "is_recommended",
    "completed_world_count",
    "local_contract_success_count",
    "local_contract_success_rate",
    "mean_local_side_game_score",
    "mean_local_side_card_point_margin",
}
_INFORMATION_SET_SIGNATURE_FIELDS = {
    "status",
    "stop_reason",
    "world_coverage",
    "policy_claim",
    "policy_consistency",
    "recommended_card",
    "compatible_world_count",
    "candidate_results",
    "depth_reached",
    "state_nodes_evaluated",
    "information_sets_evaluated",
    "controlled_policy_decisions",
    "fixed_policy_decisions",
    "selected_world_count",
    "completed_world_count",
    "sampled_world_count",
    "unique_sampled_world_count",
}
_PIMC_SIGNATURE_FIELDS = {
    "status",
    "stop_reason",
    "world_coverage",
    "recommended_card",
    "compatible_world_count",
    "candidate_results",
    "depth_reached",
    "nodes_expanded",
    "selected_world_count",
    "completed_world_count",
    "sampled_world_count",
    "unique_sampled_world_count",
}
_IMMEDIATE_SIGNATURE_FIELDS = {"recommended_card", "candidate_order"}
_COMPARISON_FIELDS = {
    "information_set_pimc_same_card",
    "information_set_immediate_same_card",
    "pimc_immediate_same_card",
    "information_set_rank_of_pimc_card",
    "pimc_rank_of_information_set_card",
}
_STRATEGY_FUSION_FIELDS = {
    "equal_controlled_root_observation",
    "selected_world_count",
    "unique_exact_worlds_evaluated",
    "distinct_world_preferred_card_count",
    "world_preferred_card_counts",
    "information_set_common_root_card",
    "information_set_root_decision_count",
    "information_set_root_reached_world_count",
}
_DUPLICATE_FIELDS = {
    "sampled_world_count",
    "unique_sampled_world_count",
    "duplicate_draw_count",
    "maximum_draw_multiplicity",
    "multiplicity_histogram",
    "candidate_completed_world_counts",
    "root_reached_world_count",
    "selected_draw_weight_preserved",
}
_STRUCTURAL_FIELDS = (
    "state_nodes_evaluated",
    "information_sets_evaluated",
    "controlled_policy_decisions",
    "fixed_policy_decisions",
    "selected_world_count",
    "completed_world_count",
)
_TIMING_FIELDS = (
    "preparation_elapsed_ms",
    "information_set_execution_elapsed_ms",
    "information_set_total_elapsed_ms",
    "same_selection_pimc_elapsed_ms",
    "immediate_elapsed_ms",
)
_performance_clock_ns = time.perf_counter_ns


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON object key: {key!r}.")
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON number is not supported: {value}.")


def _parse_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"Non-finite JSON number is not supported: {value}.")
    return parsed


def _require_exact_fields(value: Any, expected: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object.")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise ValueError(
            f"{context} fields are invalid; missing={missing!r}, unknown={unknown!r}."
        )
    return value


def _require_integer(value: Any, context: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context} must be an integer, not a boolean.")
    if minimum is not None and value < minimum:
        raise ValueError(f"{context} must be at least {minimum}.")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string.")
    return value


def _require_boolean(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context} must be a boolean.")
    return value


def _require_cards(value: Any, context: str, *, count: int | None = None) -> tuple[str, ...]:
    from skat_ai.deck import get_full_deck

    if not isinstance(value, list):
        raise ValueError(f"{context} must be an array.")
    cards = tuple(value)
    if count is not None and len(cards) != count:
        raise ValueError(f"{context} must contain exactly {count} Cards.")
    if any(not isinstance(card, str) or card not in get_full_deck() for card in cards):
        raise ValueError(f"{context} contains an invalid Card.")
    if len(cards) != len(set(cards)):
        raise ValueError(f"{context} contains duplicate Cards.")
    return cards


def _validate_candidate_rows(value: Any, game_type: str, context: str) -> tuple[Any, ...]:
    from skat_ai.bounded_search_result import (
        AggregateSearchCandidateResult,
        rank_search_candidate_results,
    )

    if not isinstance(value, list) or not value:
        raise ValueError(f"{context} must be a non-empty array.")
    candidates = []
    for index, row in enumerate(value):
        candidate = _require_exact_fields(
            row,
            _CANDIDATE_FIELDS,
            f"{context}[{index}]",
        )
        candidates.append(
            AggregateSearchCandidateResult(
                card=candidate["card"],
                rank=candidate["rank"],
                is_recommended=candidate["is_recommended"],
                completed_world_count=candidate["completed_world_count"],
                local_contract_success_count=candidate["local_contract_success_count"],
                local_contract_success_rate=candidate["local_contract_success_rate"],
                mean_local_side_game_score=candidate["mean_local_side_game_score"],
                mean_local_side_card_point_margin=(
                    candidate["mean_local_side_card_point_margin"]
                ),
            )
        )
    expected = rank_search_candidate_results(tuple(candidates), game_type, recommend=True)
    if tuple(candidates) != expected:
        raise ValueError(f"{context} does not use existing deterministic Candidate ranking.")
    return tuple(candidates)


def _validate_information_set_signature(value: Any, game_type: str, context: str) -> None:
    from skat_ai.deck import get_full_deck
    from skat_ai.information_set_search_contracts import (
        InformationSetSearchConsumedBudgetV1,
    )

    signature = _require_exact_fields(value, _INFORMATION_SET_SIGNATURE_FIELDS, context)
    if signature["status"] != "complete" or signature["stop_reason"] != "completed":
        raise ValueError(f"{context} must freeze a complete measured case.")
    if (
        signature["world_coverage"]
        not in {"all_compatible_worlds", "sampled_compatible_worlds"}
        or signature["policy_claim"] != "exact_selected_world_policy"
        or signature["policy_consistency"]
        != "controlled_player_information_set_consistent"
    ):
        raise ValueError(f"{context} has an invalid coverage or Policy claim.")
    if signature["recommended_card"] not in get_full_deck():
        raise ValueError(f"{context} has an invalid Recommendation.")
    for field in (
        "compatible_world_count",
        "depth_reached",
        "state_nodes_evaluated",
        "information_sets_evaluated",
        "controlled_policy_decisions",
        "fixed_policy_decisions",
        "selected_world_count",
        "completed_world_count",
        "sampled_world_count",
        "unique_sampled_world_count",
    ):
        _require_integer(signature[field], f"{context}.{field}", minimum=0)
    candidates = _validate_candidate_rows(
        signature["candidate_results"],
        game_type,
        f"{context}.candidates",
    )
    InformationSetSearchConsumedBudgetV1(
        depth_reached=signature["depth_reached"],
        state_nodes_evaluated=signature["state_nodes_evaluated"],
        information_sets_evaluated=signature["information_sets_evaluated"],
        controlled_policy_decisions=signature["controlled_policy_decisions"],
        fixed_policy_decisions=signature["fixed_policy_decisions"],
        selected_world_count=signature["selected_world_count"],
        completed_world_count=signature["completed_world_count"],
        sampled_world_count=signature["sampled_world_count"],
        unique_sampled_world_count=signature["unique_sampled_world_count"],
        wall_clock_elapsed_ms=0,
    )
    if (
        signature["candidate_results"][0]["card"] != signature["recommended_card"]
        or signature["compatible_world_count"] <= 0
        or signature["completed_world_count"] != signature["selected_world_count"]
        or any(
            candidate.completed_world_count != signature["completed_world_count"]
            for candidate in candidates
        )
    ):
        raise ValueError(f"{context} has inconsistent Recommendation or World counts.")
    sampled = signature["sampled_world_count"]
    unique = signature["unique_sampled_world_count"]
    if signature["world_coverage"] == "all_compatible_worlds":
        if (
            signature["selected_world_count"] != signature["compatible_world_count"]
            or sampled
            or unique
        ):
            raise ValueError(f"{context} has inconsistent exhaustive coverage.")
    elif sampled != signature["selected_world_count"] or not 0 < unique <= sampled:
        raise ValueError(f"{context} has inconsistent sampled coverage.")


def _validate_pimc_signature(value: Any, game_type: str, context: str) -> None:
    from skat_ai.deck import get_full_deck

    signature = _require_exact_fields(value, _PIMC_SIGNATURE_FIELDS, context)
    if signature["status"] != "complete" or signature["stop_reason"] != "completed":
        raise ValueError(f"{context} must freeze a complete measured case.")
    if signature["world_coverage"] not in {
        "all_compatible_worlds",
        "sampled_compatible_worlds",
    }:
        raise ValueError(f"{context} has invalid World coverage.")
    if signature["recommended_card"] not in get_full_deck():
        raise ValueError(f"{context} has an invalid Recommendation.")
    for field in (
        "compatible_world_count",
        "depth_reached",
        "nodes_expanded",
        "selected_world_count",
        "completed_world_count",
        "sampled_world_count",
        "unique_sampled_world_count",
    ):
        _require_integer(signature[field], f"{context}.{field}", minimum=0)
    candidates = _validate_candidate_rows(
        signature["candidate_results"],
        game_type,
        f"{context}.candidates",
    )
    if (
        signature["candidate_results"][0]["card"] != signature["recommended_card"]
        or signature["compatible_world_count"] <= 0
        or signature["completed_world_count"] != signature["selected_world_count"]
        or any(
            candidate.completed_world_count != signature["completed_world_count"]
            for candidate in candidates
        )
    ):
        raise ValueError(f"{context} has inconsistent Recommendation or World counts.")
    sampled = signature["sampled_world_count"]
    unique = signature["unique_sampled_world_count"]
    if signature["world_coverage"] == "all_compatible_worlds":
        if (
            signature["selected_world_count"] != signature["compatible_world_count"]
            or sampled
            or unique
        ):
            raise ValueError(f"{context} has inconsistent exhaustive coverage.")
    elif sampled != signature["selected_world_count"] or not 0 < unique <= sampled:
        raise ValueError(f"{context} has inconsistent sampled coverage.")


def _validate_strategy_fusion_diagnostic(value: Any, context: str) -> None:
    from skat_ai.deck import get_full_deck

    diagnostic = _require_exact_fields(value, _STRATEGY_FUSION_FIELDS, context)
    equal_observation = _require_boolean(
        diagnostic["equal_controlled_root_observation"],
        f"{context}.equal_controlled_root_observation",
    )
    for field in (
        "selected_world_count",
        "unique_exact_worlds_evaluated",
        "distinct_world_preferred_card_count",
        "information_set_root_decision_count",
        "information_set_root_reached_world_count",
    ):
        _require_integer(diagnostic[field], f"{context}.{field}", minimum=0)
    rows = diagnostic["world_preferred_card_counts"]
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError(f"{context}.world_preferred_card_counts requires two Cards.")
    cards = []
    counts = []
    for index, row in enumerate(rows):
        item = _require_exact_fields(row, {"card", "count"}, f"{context}.cards[{index}]")
        card = _require_string(item["card"], f"{context}.cards[{index}].card")
        if card not in get_full_deck():
            raise ValueError(f"{context}.cards[{index}].card must be a valid Card.")
        cards.append(card)
        counts.append(
            _require_integer(item["count"], f"{context}.cards[{index}].count", minimum=1)
        )
    common_card = diagnostic["information_set_common_root_card"]
    if (
        not equal_observation
        or len(cards) != len(set(cards))
        or diagnostic["unique_exact_worlds_evaluated"]
        > diagnostic["selected_world_count"]
        or diagnostic["distinct_world_preferred_card_count"]
        > diagnostic["unique_exact_worlds_evaluated"]
        or diagnostic["distinct_world_preferred_card_count"] != len(cards)
        or sum(counts) != diagnostic["selected_world_count"]
        or common_card not in get_full_deck()
        or diagnostic["information_set_root_decision_count"] != 1
        or diagnostic["information_set_root_reached_world_count"]
        != diagnostic["selected_world_count"]
    ):
        raise ValueError(f"{context} has inconsistent aggregate Strategy-Fusion facts.")


def _validate_duplicate_diagnostic(value: Any, context: str) -> None:
    from skat_ai.deck import get_full_deck

    diagnostic = _require_exact_fields(value, _DUPLICATE_FIELDS, context)
    for field in (
        "sampled_world_count",
        "unique_sampled_world_count",
        "duplicate_draw_count",
        "maximum_draw_multiplicity",
        "root_reached_world_count",
    ):
        _require_integer(diagnostic[field], f"{context}.{field}", minimum=0)
    if diagnostic["sampled_world_count"] <= diagnostic["unique_sampled_world_count"]:
        raise ValueError(f"{context} must retain at least one duplicate sampled draw.")
    histogram = diagnostic["multiplicity_histogram"]
    if not isinstance(histogram, list) or not histogram:
        raise ValueError(f"{context}.multiplicity_histogram must be a non-empty array.")
    multiplicities = []
    world_counts = []
    for index, row in enumerate(histogram):
        item = _require_exact_fields(
            row,
            {"multiplicity", "world_count"},
            f"{context}.multiplicity_histogram[{index}]",
        )
        multiplicities.append(
            _require_integer(
                item["multiplicity"],
                f"{context}.multiplicity_histogram[{index}].multiplicity",
                minimum=1,
            )
        )
        world_counts.append(
            _require_integer(
                item["world_count"],
                f"{context}.multiplicity_histogram[{index}].world_count",
                minimum=1,
            )
        )
    candidate_rows = diagnostic["candidate_completed_world_counts"]
    if not isinstance(candidate_rows, list) or not candidate_rows:
        raise ValueError(
            f"{context}.candidate_completed_world_counts must be a non-empty array."
        )
    candidate_cards = []
    candidate_counts = []
    for index, row in enumerate(candidate_rows):
        item = _require_exact_fields(
            row,
            {"card", "count"},
            f"{context}.candidate_completed_world_counts[{index}]",
        )
        card = _require_string(
            item["card"],
            f"{context}.candidate_completed_world_counts[{index}].card",
        )
        if card not in get_full_deck():
            raise ValueError(
                f"{context}.candidate_completed_world_counts[{index}].card "
                "must be a valid Card."
            )
        candidate_cards.append(card)
        candidate_counts.append(
            _require_integer(
                item["count"],
                f"{context}.candidate_completed_world_counts[{index}].count",
                minimum=1,
            )
        )
    weight_preserved = _require_boolean(
        diagnostic["selected_draw_weight_preserved"],
        f"{context}.selected_draw_weight_preserved",
    )
    sampled = diagnostic["sampled_world_count"]
    unique = diagnostic["unique_sampled_world_count"]
    if (
        len(multiplicities) != len(set(multiplicities))
        or sum(world_counts) != unique
        or sum(
            multiplicity * world_count
            for multiplicity, world_count in zip(
                multiplicities,
                world_counts,
                strict=True,
            )
        )
        != sampled
        or diagnostic["duplicate_draw_count"] != sampled - unique
        or diagnostic["maximum_draw_multiplicity"] != max(multiplicities)
        or diagnostic["root_reached_world_count"] != sampled
        or len(candidate_cards) != len(set(candidate_cards))
        or any(count != sampled for count in candidate_counts)
        or not weight_preserved
    ):
        raise ValueError(f"{context} has inconsistent sampled duplicate-weight facts.")


def _validate_case(case: Any, index: int) -> None:
    from skat_ai.deck import get_full_deck
    from skat_ai.game_declaration import GameDeclaration
    from skat_ai.information_set_search_contracts import (
        INFORMATION_SET_SEARCH_CONTROL_SCOPES,
        INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
        InformationSetFixedPlayerPolicyV1,
        InformationSetSearchPolicySettingsV1,
    )
    from skat_ai.information_set_search_policy import (
        is_information_set_fixed_policy_supported_for_actor_v1,
    )
    from skat_ai.matador_inference import infer_matadors_from_known_ownership
    from skat_ai.search_budget_profiles import SEARCH_BUDGET_PROFILE_IDENTIFIERS

    row = _require_exact_fields(case, _CASE_FIELDS, f"cases[{index}]")
    name = _require_string(row["name"], f"cases[{index}].name")
    declaration_row = _require_exact_fields(
        row["declaration"],
        _DECLARATION_FIELDS,
        f"case {name!r} declaration",
    )
    declaration = GameDeclaration(**declaration_row)
    actor = _require_exact_fields(row["actor"], _ACTOR_FIELDS, f"case {name!r} actor")
    if actor["player_role"] not in {"declarer", "defender"}:
        raise ValueError(f"Case {name!r} has an invalid actor role.")
    if actor["declarer_player"] not in {"me", "left", "right"}:
        raise ValueError(f"Case {name!r} has an invalid declarer Player.")
    if actor["turn_phase"] not in {"lead", "second_seat", "third_seat"}:
        raise ValueError(f"Case {name!r} has an invalid turn phase.")
    if (actor["player_role"] == "declarer") != (actor["declarer_player"] == "me"):
        raise ValueError(f"Case {name!r} has inconsistent local role ownership.")

    fixture = _require_exact_fields(
        row["fixture"],
        _FIXTURE_FIELDS,
        f"case {name!r} fixture",
    )
    hands = _require_exact_fields(
        fixture["initial_hands"],
        {"me", "left", "right"},
        f"case {name!r} initial_hands",
    )
    complete_cards = []
    for player in ("me", "left", "right"):
        complete_cards.extend(
            _require_cards(
                hands[player],
                f"case {name!r} initial hand {player}",
                count=10,
            )
        )
    complete_cards.extend(
        _require_cards(fixture["skat"], f"case {name!r} Skat", count=2)
    )
    if len(complete_cards) != len(set(complete_cards)) or set(complete_cards) != set(
        get_full_deck()
    ):
        raise ValueError(f"Case {name!r} initial ownership must cover the full deck exactly.")
    if declaration.game_type != "null":
        declarer_player = actor["declarer_player"]
        inferred_matadors = infer_matadors_from_known_ownership(
            game_type=declaration.game_type,
            declarer_owned_cards=[*hands[declarer_player], *fixture["skat"]],
            non_declarer_owned_cards=[
                card
                for player in ("me", "left", "right")
                if player != declarer_player
                for card in hands[player]
            ],
        )
        if declaration.matadors != inferred_matadors:
            raise ValueError(
                f"Case {name!r} matadors={declaration.matadors} conflicts with "
                f"complete-deal inferred matadors={inferred_matadors}."
            )
    if fixture["initial_next_player"] not in {"me", "left", "right"}:
        raise ValueError(f"Case {name!r} has an invalid initial next Player.")
    _require_cards(fixture["replayed_cards"], f"case {name!r} replayed Cards")
    public_players = fixture["public_hand_players"]
    if not isinstance(public_players, list) or len(public_players) != len(set(public_players)):
        raise ValueError(f"Case {name!r} public_hand_players must be a unique array.")
    if any(player not in {"me", "left", "right"} for player in public_players):
        raise ValueError(f"Case {name!r} has an invalid public hand Player.")
    if bool(public_players) != declaration.ouvert or any(
        player != actor["declarer_player"] for player in public_players
    ):
        raise ValueError(f"Case {name!r} declared-Ouvert public hands are inconsistent.")

    profile_name = row["profile_name"]
    if profile_name not in SEARCH_BUDGET_PROFILE_IDENTIFIERS:
        raise ValueError(f"Unknown benchmark profile_name: {profile_name!r}.")
    _require_integer(row["world_selection_seed"], f"case {name!r} world seed")
    _require_integer(row["immediate_seed"], f"case {name!r} Immediate seed")
    _require_integer(
        row["immediate_sample_count"],
        f"case {name!r} Immediate sample count",
        minimum=1,
    )
    _require_boolean(
        row["immediate_use_basic_opponent_strategy"],
        f"case {name!r} Immediate strategy flag",
    )
    if row["immediate_response_policy_by_player"] is not None:
        raise ValueError(
            f"Case {name!r} Immediate response-policy override must be null."
        )

    policy_rows = row["fixed_player_policies"]
    if not isinstance(policy_rows, list) or len(policy_rows) != 2:
        raise ValueError(f"Case {name!r} requires exactly two fixed Policies.")
    fixed_policies = tuple(
        InformationSetFixedPlayerPolicyV1(
            **_require_exact_fields(
                policy,
                _FIXED_POLICY_FIELDS,
                f"case {name!r} fixed policy {policy_index}",
            )
        )
        for policy_index, policy in enumerate(policy_rows)
    )
    settings = InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=(
            INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION
        ),
        controlled_player="me",
        control_scope=INFORMATION_SET_SEARCH_CONTROL_SCOPES[0],
        fixed_player_policies=fixed_policies,
    )
    if not all(
        is_information_set_fixed_policy_supported_for_actor_v1(
            actor_player=player,
            declarer_player=actor["declarer_player"],
            policy_settings=settings,
        )
        for player in ("left", "right")
    ):
        raise ValueError(f"Case {name!r} has a role-incompatible fixed Policy.")

    information = row["expected_information_set_signature"]
    pimc = row["expected_same_selection_pimc_signature"]
    _validate_information_set_signature(
        information,
        declaration.game_type,
        f"case {name!r} Information-set signature",
    )
    _validate_pimc_signature(
        pimc,
        declaration.game_type,
        f"case {name!r} PIMC signature",
    )
    shared_selection_fields = (
        "compatible_world_count",
        "selected_world_count",
        "completed_world_count",
        "sampled_world_count",
        "unique_sampled_world_count",
    )
    if any(information[field] != pimc[field] for field in shared_selection_fields):
        raise ValueError(f"Case {name!r} PIMC does not retain the exact same selection.")
    immediate = _require_exact_fields(
        row["expected_immediate_signature"],
        _IMMEDIATE_SIGNATURE_FIELDS,
        f"case {name!r} Immediate signature",
    )
    _require_string(immediate["recommended_card"], f"case {name!r} Immediate Card")
    immediate_cards = _require_cards(
        immediate["candidate_order"],
        f"case {name!r} Immediate Candidates",
    )
    if immediate["recommended_card"] not in immediate_cards:
        raise ValueError(f"Case {name!r} Immediate Recommendation is not a Candidate.")
    information_cards = {
        candidate["card"] for candidate in information["candidate_results"]
    }
    pimc_cards = {candidate["card"] for candidate in pimc["candidate_results"]}
    if information_cards != pimc_cards or information_cards != set(immediate_cards):
        raise ValueError(f"Case {name!r} methods do not share one legal Candidate set.")
    comparison = _require_exact_fields(
        row["expected_descriptive_comparison"],
        _COMPARISON_FIELDS,
        f"case {name!r} descriptive comparison",
    )
    for field in (
        "information_set_pimc_same_card",
        "information_set_immediate_same_card",
        "pimc_immediate_same_card",
    ):
        _require_boolean(comparison[field], f"case {name!r} comparison {field}")
    for field in (
        "information_set_rank_of_pimc_card",
        "pimc_rank_of_information_set_card",
    ):
        _require_integer(comparison[field], f"case {name!r} comparison {field}", minimum=1)
    information_card = information["recommended_card"]
    pimc_card = pimc["recommended_card"]
    expected_comparison = {
        "information_set_pimc_same_card": information_card == pimc_card,
        "information_set_immediate_same_card": (
            information_card == immediate["recommended_card"]
        ),
        "pimc_immediate_same_card": pimc_card == immediate["recommended_card"],
        "information_set_rank_of_pimc_card": next(
            (
                candidate["rank"]
                for candidate in information["candidate_results"]
                if candidate["card"] == pimc_card
            ),
            None,
        ),
        "pimc_rank_of_information_set_card": next(
            (
                candidate["rank"]
                for candidate in pimc["candidate_results"]
                if candidate["card"] == information_card
            ),
            None,
        ),
    }
    if comparison != expected_comparison:
        raise ValueError(f"Case {name!r} has an inconsistent descriptive comparison.")

    strategy = row["expected_strategy_fusion_diagnostic"]
    duplicate = row["expected_sampled_duplicate_diagnostic"]
    if name == "clubs_strategy_fusion_sampled_two_tricks":
        _validate_strategy_fusion_diagnostic(strategy, f"case {name!r} Strategy Fusion")
        if (
            strategy["selected_world_count"] != information["selected_world_count"]
            or strategy["unique_exact_worlds_evaluated"]
            != information["unique_sampled_world_count"]
            or strategy["information_set_common_root_card"] != information_card
            or strategy["information_set_root_reached_world_count"]
            != information["selected_world_count"]
            or not {
                item["card"] for item in strategy["world_preferred_card_counts"]
            }.issubset(
                {candidate["card"] for candidate in information["candidate_results"]}
            )
        ):
            raise ValueError(
                f"Case {name!r} Strategy-Fusion diagnostic conflicts with its signature."
            )
    elif strategy is not None:
        raise ValueError("Only the Strategy-Fusion case may retain that diagnostic.")
    if name == "grand_sampled_duplicate_weight_two_tricks":
        _validate_duplicate_diagnostic(duplicate, f"case {name!r} duplicate weight")
        if (
            duplicate["sampled_world_count"] != information["sampled_world_count"]
            or duplicate["unique_sampled_world_count"]
            != information["unique_sampled_world_count"]
            or duplicate["root_reached_world_count"]
            != information["selected_world_count"]
            or duplicate["candidate_completed_world_counts"]
            != [
                {
                    "card": candidate["card"],
                    "count": candidate["completed_world_count"],
                }
                for candidate in information["candidate_results"]
            ]
        ):
            raise ValueError(
                f"Case {name!r} duplicate-weight diagnostic conflicts with its signature."
            )
    elif duplicate is not None:
        raise ValueError("Only the duplicate-weight case may retain that diagnostic.")


def _load_corpus(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Information-set benchmark corpus must not contain a UTF-8 BOM.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Information-set benchmark corpus must be valid UTF-8.") from error
    try:
        corpus = json.loads(
            text,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_non_finite_constant,
            parse_float=_parse_finite_float,
        )
    except json.JSONDecodeError as error:
        raise ValueError("Information-set benchmark corpus must be valid JSON.") from error

    root = _require_exact_fields(corpus, _ROOT_FIELDS, "Benchmark corpus root")
    version = root["schema_version"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version != INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_SCHEMA_VERSION
    ):
        raise ValueError("Unsupported Information-set benchmark corpus schema version.")
    if root["corpus_name"] != INFORMATION_SET_SEARCH_BENCHMARK_CORPUS_NAME:
        raise ValueError("Information-set benchmark corpus_name is not canonical.")
    cases = root["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("Information-set benchmark cases must be a non-empty array.")
    names = tuple(case.get("name") if isinstance(case, dict) else None for case in cases)
    if any(not isinstance(name, str) or not name for name in names):
        raise ValueError("Every Information-set benchmark case requires a name.")
    if len(names) != len(set(names)):
        raise ValueError("Information-set benchmark case names must be unique.")
    if names != INFORMATION_SET_SEARCH_BENCHMARK_CASE_NAMES:
        raise ValueError("Information-set benchmark cases do not match the exact matrix.")
    for index, case in enumerate(cases):
        _validate_case(case, index)
        _build_case_context(case)
    return root


@dataclass(frozen=True, slots=True)
class _CaseContext:
    information_view: Any
    immediate_state: Any
    left_hand_size: int
    right_hand_size: int
    public_hand_constraints: tuple[Any, ...]


def _build_case_context(case: dict[str, Any]) -> _CaseContext:
    from skat_ai.bounded_search_information import build_live_search_information_view
    from skat_ai.exact_search_state import apply_exact_search_card, build_exact_search_state
    from skat_ai.game_declaration import GameDeclaration
    from skat_ai.game_state import GameState
    from skat_ai.public_hand_constraint import DECLARED_OUVERT_SOURCE, PublicHandConstraint

    declaration = GameDeclaration(**case["declaration"])
    fixture = case["fixture"]
    actor = case["actor"]
    exact_state = build_exact_search_state(
        declaration=declaration,
        declarer_player=actor["declarer_player"],
        remaining_hands=fixture["initial_hands"],
        current_trick=(),
        next_player=fixture["initial_next_player"],
        declarer_trick_points=0,
        defender_trick_points=0,
        declarer_completed_tricks=0,
        defender_completed_tricks=0,
        out_of_play_cards=fixture["skat"],
    )
    completed_tricks = []
    for card in fixture["replayed_cards"]:
        transition = apply_exact_search_card(exact_state, card)
        exact_state = transition.next_state
        if transition.completed_trick is not None:
            trick = transition.completed_trick
            completed_tricks.append(
                {
                    "cards": [play.card for play in trick.plays],
                    "players": [play.player for play in trick.plays],
                    "winner_player": trick.winner_player,
                    "winner_role": trick.winner_side,
                }
            )
    if exact_state.next_player != "me":
        raise AssertionError(f"Benchmark case {case['name']!r} is not a local Decision.")

    expected_trick_size = {"lead": 0, "second_seat": 1, "third_seat": 2}[
        actor["turn_phase"]
    ]
    if len(exact_state.current_trick) != expected_trick_size:
        raise AssertionError(f"Benchmark case {case['name']!r} has the wrong turn phase.")
    public_hand_constraints = tuple(
        PublicHandConstraint(
            player=player,
            cards=exact_state.hand_for(player),
            source=DECLARED_OUVERT_SOURCE,
        )
        for player in fixture["public_hand_players"]
    )
    local_knows_skat = actor["player_role"] == "declarer" and not declaration.hand_game
    state = GameState(
        game_type=declaration.game_type,
        player_role=actor["player_role"],
        declarer_player=actor["declarer_player"],
        hand=list(exact_state.hand_for("me")),
        current_trick=[play.card for play in exact_state.current_trick],
        played_cards=[],
        completed_tricks=completed_tricks,
        skat=list(exact_state.out_of_play_cards) if local_knows_skat else [],
        declarer_points=0,
        defender_points=0,
        trick_leader=(
            exact_state.current_trick[0].player
            if exact_state.current_trick
            else exact_state.next_player
        ),
        next_player=exact_state.next_player,
    )
    information_view = build_live_search_information_view(
        state=state,
        declaration=declaration,
        left_hand_size=len(exact_state.hand_for("left")),
        right_hand_size=len(exact_state.hand_for("right")),
        skat_visibility="known_to_declarer" if local_knows_skat else "unknown",
        public_hand_constraints=public_hand_constraints,
    )
    if (
        information_view.local_remaining_hand != exact_state.hand_for("me")
        or information_view.declarer_points != exact_state.declarer_trick_points
        or information_view.defender_points != exact_state.defender_trick_points
        or information_view.declarer_trick_count != exact_state.declarer_completed_tricks
        or information_view.defender_trick_count != exact_state.defender_completed_tricks
    ):
        raise AssertionError(f"Benchmark case {case['name']!r} changed safe root facts.")
    public_players = {constraint.player for constraint in public_hand_constraints}
    if any(
        constraint.exact_cards and constraint.player not in {"me", *public_players}
        for constraint in information_view.hidden_card_constraints
    ):
        raise AssertionError(f"Benchmark case {case['name']!r} leaked fixture ownership.")
    return _CaseContext(
        information_view=information_view,
        immediate_state=state,
        left_hand_size=len(exact_state.hand_for("left")),
        right_hand_size=len(exact_state.hand_for("right")),
        public_hand_constraints=public_hand_constraints,
    )


def _build_policy_settings(case: dict[str, Any]) -> Any:
    from skat_ai.information_set_search_contracts import (
        INFORMATION_SET_SEARCH_CONTROL_SCOPES,
        INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
        InformationSetFixedPlayerPolicyV1,
        InformationSetSearchPolicySettingsV1,
    )

    return InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=(
            INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION
        ),
        controlled_player="me",
        control_scope=INFORMATION_SET_SEARCH_CONTROL_SCOPES[0],
        fixed_player_policies=tuple(
            InformationSetFixedPlayerPolicyV1(**policy)
            for policy in case["fixed_player_policies"]
        ),
    )


def _serialize_candidate(candidate: Any) -> dict[str, Any]:
    return {
        "card": candidate.card,
        "rank": candidate.rank,
        "is_recommended": candidate.is_recommended,
        "completed_world_count": candidate.completed_world_count,
        "local_contract_success_count": candidate.local_contract_success_count,
        "local_contract_success_rate": candidate.local_contract_success_rate,
        "mean_local_side_game_score": candidate.mean_local_side_game_score,
        "mean_local_side_card_point_margin": candidate.mean_local_side_card_point_margin,
    }


def _information_set_signature(result: Any) -> dict[str, Any]:
    consumed = result.consumed_budget
    return {
        "status": result.status,
        "stop_reason": result.stop_reason,
        "world_coverage": result.world_coverage,
        "policy_claim": result.policy_claim,
        "policy_consistency": result.policy_consistency,
        "recommended_card": result.recommended_card,
        "compatible_world_count": result.compatible_world_count,
        "candidate_results": [
            _serialize_candidate(candidate) for candidate in result.candidate_results
        ],
        "depth_reached": consumed.depth_reached,
        "state_nodes_evaluated": consumed.state_nodes_evaluated,
        "information_sets_evaluated": consumed.information_sets_evaluated,
        "controlled_policy_decisions": consumed.controlled_policy_decisions,
        "fixed_policy_decisions": consumed.fixed_policy_decisions,
        "selected_world_count": consumed.selected_world_count,
        "completed_world_count": consumed.completed_world_count,
        "sampled_world_count": consumed.sampled_world_count,
        "unique_sampled_world_count": consumed.unique_sampled_world_count,
    }


def _pimc_signature(result: Any) -> dict[str, Any]:
    consumed = result.consumed_budget
    return {
        "status": result.status,
        "stop_reason": result.stop_reason,
        "world_coverage": result.world_coverage,
        "recommended_card": result.recommended_card,
        "compatible_world_count": result.compatible_world_count,
        "candidate_results": [
            _serialize_candidate(candidate) for candidate in result.candidate_results
        ],
        "depth_reached": consumed.depth_reached,
        "nodes_expanded": consumed.nodes_expanded,
        "selected_world_count": consumed.selected_world_count,
        "completed_world_count": consumed.completed_world_count,
        "sampled_world_count": consumed.sampled_world_count,
        "unique_sampled_world_count": consumed.unique_sampled_world_count,
    }


def _rank_of(result: Any, card: str | None) -> int | None:
    return next(
        (candidate.rank for candidate in result.candidate_results if candidate.card == card),
        None,
    )


def _descriptive_comparison(
    information_set_result: Any,
    pimc_result: Any,
    immediate_card: str,
) -> dict[str, Any]:
    information_card = information_set_result.recommended_card
    pimc_card = pimc_result.recommended_card
    return {
        "information_set_pimc_same_card": information_card == pimc_card,
        "information_set_immediate_same_card": information_card == immediate_card,
        "pimc_immediate_same_card": pimc_card == immediate_card,
        "information_set_rank_of_pimc_card": _rank_of(information_set_result, pimc_card),
        "pimc_rank_of_information_set_card": _rank_of(pimc_result, information_card),
    }


def _strategy_fusion_diagnostic(
    case: dict[str, Any],
    preparation: Any,
    information_set_result: Any,
    requested_pimc_budget: Any,
) -> dict[str, Any] | None:
    from skat_ai.information_set_search_state import (
        build_information_set_search_observation_v1,
    )
    from skat_ai.perfect_information_minimax import solve_perfect_information_minimax

    if case["name"] != "clubs_strategy_fusion_sampled_two_tricks":
        return None
    selection = preparation.world_selection
    if selection is None:
        raise AssertionError("Strategy-Fusion diagnostic requires an available selection.")
    root_observations = tuple(
        build_information_set_search_observation_v1(state)
        for state in preparation.world_states
    )
    equal_observation = bool(root_observations) and all(
        observation == root_observations[0] for observation in root_observations[1:]
    )
    preferred_by_state = {
        state: solve_perfect_information_minimax(
            state=state,
            perspective_player="me",
            requested_budget=requested_pimc_budget,
        ).recommended_card
        for state in dict.fromkeys(selection.exact_states)
    }
    preferred_counts = Counter(preferred_by_state[state] for state in selection.exact_states)
    if None in preferred_counts:
        raise AssertionError("Strategy-Fusion exact-world diagnostic did not complete.")
    root_decisions = tuple(
        decision
        for decision in information_set_result.controlled_policy
        if decision.depth_plies == 0
    )
    return {
        "equal_controlled_root_observation": equal_observation,
        "selected_world_count": selection.selected_world_count,
        "unique_exact_worlds_evaluated": len(preferred_by_state),
        "distinct_world_preferred_card_count": len(preferred_counts),
        "world_preferred_card_counts": [
            {"card": card, "count": preferred_counts[card]}
            for card in selection.legal_root_cards
            if preferred_counts[card]
        ],
        "information_set_common_root_card": information_set_result.recommended_card,
        "information_set_root_decision_count": len(root_decisions),
        "information_set_root_reached_world_count": (
            root_decisions[0].reached_world_count if len(root_decisions) == 1 else 0
        ),
    }


def _sampled_duplicate_diagnostic(
    case: dict[str, Any],
    preparation: Any,
    information_set_result: Any,
) -> dict[str, Any] | None:
    if case["name"] != "grand_sampled_duplicate_weight_two_tricks":
        return None
    selection = preparation.world_selection
    if selection is None:
        raise AssertionError("Duplicate-weight diagnostic requires an available selection.")
    multiplicities = Counter(selection.exact_states)
    histogram = Counter(multiplicities.values())
    root_decisions = tuple(
        decision
        for decision in information_set_result.controlled_policy
        if decision.depth_plies == 0
    )
    sampled_count = selection.sampled_world_count
    unique_count = selection.unique_sampled_world_count
    candidate_counts = [
        {"card": candidate.card, "count": candidate.completed_world_count}
        for candidate in information_set_result.candidate_results
    ]
    root_reached_count = root_decisions[0].reached_world_count if len(root_decisions) == 1 else 0
    return {
        "sampled_world_count": sampled_count,
        "unique_sampled_world_count": unique_count,
        "duplicate_draw_count": sampled_count - unique_count,
        "maximum_draw_multiplicity": max(multiplicities.values()),
        "multiplicity_histogram": [
            {"multiplicity": multiplicity, "world_count": histogram[multiplicity]}
            for multiplicity in sorted(histogram)
        ],
        "candidate_completed_world_counts": candidate_counts,
        "root_reached_world_count": root_reached_count,
        "selected_draw_weight_preserved": (
            sampled_count > unique_count
            and all(row["count"] == sampled_count for row in candidate_counts)
            and root_reached_count == sampled_count
        ),
    }


def _timed(operation: Callable[[], Any]) -> tuple[Any, float]:
    started_at = _performance_clock_ns()
    result = operation()
    elapsed_ms = max(0.0, (_performance_clock_ns() - started_at) / 1_000_000)
    return result, elapsed_ms


def _frozen_monotonic() -> float:
    return 0.0


@contextmanager
def _frozen_search_operational_clocks() -> Iterator[None]:
    import skat_ai.compatible_world_minimax as compatible_world_minimax
    import skat_ai.information_set_search_executor as information_set_search_executor
    import skat_ai.perfect_information_minimax as perfect_information_minimax

    # Retain exact profile budgets while preventing machine speed from changing
    # the frozen complete functional signatures. External stage timing stays real.
    with (
        patch.object(
            information_set_search_executor,
            "_monotonic",
            _frozen_monotonic,
        ),
        patch.object(compatible_world_minimax, "_monotonic", _frozen_monotonic),
        patch.object(perfect_information_minimax, "_monotonic", _frozen_monotonic),
    ):
        yield


def _timed_search(operation: Callable[[], Any]) -> tuple[Any, float]:
    with _frozen_search_operational_clocks():
        return _timed(operation)


def _expected_functional_bundle(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "information_set_signature": case["expected_information_set_signature"],
        "same_selection_pimc_signature": case[
            "expected_same_selection_pimc_signature"
        ],
        "immediate_signature": case["expected_immediate_signature"],
        "descriptive_comparison": case["expected_descriptive_comparison"],
        "strategy_fusion_diagnostic": case["expected_strategy_fusion_diagnostic"],
        "sampled_duplicate_diagnostic": case["expected_sampled_duplicate_diagnostic"],
    }


def _execute_case(
    case: dict[str, Any],
    context: _CaseContext,
) -> tuple[dict[str, Any], dict[str, float]]:
    from skat_ai.compatible_world_minimax import (
        solve_compatible_world_minimax_on_selection_v1,
    )
    from skat_ai.information_set_search_contracts import (
        build_information_set_search_request_v1,
    )
    from skat_ai.information_set_search_executor import execute_information_set_search_v1
    from skat_ai.information_set_search_preparation import prepare_information_set_search_v1
    from skat_ai.information_set_search_workflow import (
        convert_information_set_search_budget_to_requested_search_budget_v1,
    )
    from skat_ai.recommender import recommend_card_by_expected_value
    from skat_ai.search_budget_profiles import get_information_set_search_budget_profile

    budget = get_information_set_search_budget_profile(case["profile_name"])
    request = build_information_set_search_request_v1(
        information_view=context.information_view,
        requested_budget=budget,
        world_selection_seed=case["world_selection_seed"],
        policy_settings=_build_policy_settings(case),
    )
    preparation, preparation_elapsed_ms = _timed(
        lambda: prepare_information_set_search_v1(request)
    )
    information_set_result, execution_elapsed_ms = _timed_search(
        lambda: execute_information_set_search_v1(preparation)
    )
    selection = preparation.world_selection
    if selection is None or not selection.available:
        raise AssertionError(f"Measured benchmark case {case['name']!r} was unavailable.")
    requested_pimc_budget = (
        convert_information_set_search_budget_to_requested_search_budget_v1(budget)
    )
    pimc_result, pimc_elapsed_ms = _timed_search(
        lambda: solve_compatible_world_minimax_on_selection_v1(
            information_view=context.information_view,
            requested_budget=requested_pimc_budget,
            selection=selection,
        )
    )
    immediate, immediate_elapsed_ms = _timed(
        lambda: recommend_card_by_expected_value(
            state=context.immediate_state,
            left_hand_size=context.left_hand_size,
            right_hand_size=context.right_hand_size,
            sample_count=case["immediate_sample_count"],
            random_seed=case["immediate_seed"],
            use_basic_opponent_strategy=case[
                "immediate_use_basic_opponent_strategy"
            ],
            opponent_response_policy_by_player=case[
                "immediate_response_policy_by_player"
            ],
            public_hand_constraints=context.public_hand_constraints,
        )
    )
    immediate_card, _reason, immediate_values = immediate
    with _frozen_search_operational_clocks():
        strategy_fusion_diagnostic = _strategy_fusion_diagnostic(
            case,
            preparation,
            information_set_result,
            requested_pimc_budget,
        )
    functional = {
        "information_set_signature": _information_set_signature(
            information_set_result
        ),
        "same_selection_pimc_signature": _pimc_signature(pimc_result),
        "immediate_signature": {
            "recommended_card": immediate_card,
            "candidate_order": list(immediate_values),
        },
        "descriptive_comparison": _descriptive_comparison(
            information_set_result,
            pimc_result,
            immediate_card,
        ),
        "strategy_fusion_diagnostic": strategy_fusion_diagnostic,
        "sampled_duplicate_diagnostic": _sampled_duplicate_diagnostic(
            case,
            preparation,
            information_set_result,
        ),
    }
    expected = _expected_functional_bundle(case)
    if functional != expected:
        raise AssertionError(
            f"Functional result changed for {case['name']!r}: "
            f"expected {expected!r}, got {functional!r}"
        )
    timings = {
        "preparation_elapsed_ms": preparation_elapsed_ms,
        "information_set_execution_elapsed_ms": execution_elapsed_ms,
        "information_set_total_elapsed_ms": (
            preparation_elapsed_ms + execution_elapsed_ms
        ),
        "same_selection_pimc_elapsed_ms": pimc_elapsed_ms,
        "immediate_elapsed_ms": immediate_elapsed_ms,
    }
    return functional, timings


def _metric_summary(values: list[float], *, include_total: bool = False) -> dict[str, float]:
    result = {
        "minimum": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "mean": round(statistics.fmean(values), 3),
        "maximum": round(max(values), 3),
    }
    if include_total:
        result["total"] = round(sum(values), 3)
    return result


def _structural_summary(values: list[int]) -> dict[str, int | float | bool]:
    return {
        **_metric_summary(values),
        "deterministic": len(set(values)) == 1,
    }


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator, 3) if denominator > 0 else None


def run_benchmark(
    *,
    corpus_path: Path = DEFAULT_CORPUS_PATH,
    warmup_run_count: int = 1,
    measured_run_count: int = 5,
    case_name: str | None = None,
) -> dict[str, Any]:
    _require_integer(warmup_run_count, "warmup_run_count", minimum=0)
    _require_integer(measured_run_count, "measured_run_count", minimum=2)
    corpus = _load_corpus(corpus_path)
    cases = corpus["cases"]
    if case_name is not None:
        known = {case["name"] for case in cases}
        if case_name not in known:
            raise ValueError(f"Unknown Information-set benchmark case: {case_name!r}.")
        cases = [case for case in cases if case["name"] == case_name]

    case_outputs = []
    aggregate_timings = {field: [] for field in _TIMING_FIELDS}
    aggregate_structural = {field: [] for field in _STRUCTURAL_FIELDS}
    for case in cases:
        context = _build_case_context(case)
        for _ in range(warmup_run_count):
            _execute_case(case, context)

        runs = []
        signatures = []
        for run_number in range(1, measured_run_count + 1):
            functional, timings = _execute_case(case, context)
            signatures.append(functional)
            structural = {
                field: functional["information_set_signature"][field]
                for field in _STRUCTURAL_FIELDS
            }
            for field, value in timings.items():
                aggregate_timings[field].append(value)
            for field, value in structural.items():
                aggregate_structural[field].append(value)
            runs.append(
                {
                    "run_number": run_number,
                    **{field: round(timings[field], 3) for field in _TIMING_FIELDS},
                    **structural,
                }
            )
        if any(signature != signatures[0] for signature in signatures[1:]):
            raise AssertionError(f"Measured functional results varied for {case['name']!r}.")

        timing_summaries = {
            field.removesuffix("_elapsed_ms"): _metric_summary(
                [run[field] for run in runs]
            )
            for field in _TIMING_FIELDS
        }
        structural_summaries = {
            field: _structural_summary([run[field] for run in runs])
            for field in _STRUCTURAL_FIELDS
        }
        case_outputs.append(
            {
                "case_name": case["name"],
                "game_type": case["declaration"]["game_type"],
                "profile_name": case["profile_name"],
                "world_selection_seed": case["world_selection_seed"],
                "immediate_seed": case["immediate_seed"],
                "functional_result": signatures[0],
                "deterministic_across_measured_runs": True,
                "timing_ms": timing_summaries,
                "structural_work": structural_summaries,
                "local_timing_ratios": {
                    "information_set_execution_to_pimc_median_ratio": _safe_ratio(
                        timing_summaries["information_set_execution"]["median"],
                        timing_summaries["same_selection_pimc"]["median"],
                    ),
                    "information_set_total_to_immediate_median_ratio": _safe_ratio(
                        timing_summaries["information_set_total"]["median"],
                        timing_summaries["immediate"]["median"],
                    ),
                },
                "runs": runs,
            }
        )

    aggregate_timing_summaries = {
        field.removesuffix("_elapsed_ms"): _metric_summary(values, include_total=True)
        for field, values in aggregate_timings.items()
    }
    return {
        "schema_version": INFORMATION_SET_SEARCH_BENCHMARK_OUTPUT_VERSION,
        "benchmark_name": INFORMATION_SET_SEARCH_BENCHMARK_NAME,
        "corpus": {
            "name": corpus["corpus_name"],
            "path": corpus_path.name,
        },
        "policies": dict(INFORMATION_SET_SEARCH_BENCHMARK_POLICIES),
        "profile_names": list(dict.fromkeys(case["profile_name"] for case in cases)),
        "warmup_run_count": warmup_run_count,
        "measured_run_count": measured_run_count,
        "environment": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_executable": Path(sys.executable).name,
        },
        "cases": case_outputs,
        "aggregate": {
            "measured_execution_count": len(cases) * measured_run_count,
            "timing_ms": aggregate_timing_summaries,
            "structural_work": {
                field: {
                    **_metric_summary(values),
                    "deterministic_within_each_case": all(
                        output["structural_work"][field]["deterministic"]
                        for output in case_outputs
                    ),
                }
                for field, values in aggregate_structural.items()
            },
            "local_timing_ratios": {
                "information_set_execution_to_pimc_median_ratio": _safe_ratio(
                    aggregate_timing_summaries["information_set_execution"]["median"],
                    aggregate_timing_summaries["same_selection_pimc"]["median"],
                ),
                "information_set_total_to_immediate_median_ratio": _safe_ratio(
                    aggregate_timing_summaries["information_set_total"]["median"],
                    aggregate_timing_summaries["immediate"]["median"],
                ),
            },
        },
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark deterministic late-game Information-set Search."
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS_PATH)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--case")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output = run_benchmark(
        corpus_path=args.corpus,
        warmup_run_count=args.warmup_runs,
        measured_run_count=args.runs,
        case_name=args.case,
    )
    json.dump(output, sys.stdout, indent=2, sort_keys=True, allow_nan=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
