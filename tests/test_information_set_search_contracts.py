import ast
import json
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import skat_ai
import skat_ai.api.v1 as api_v1
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1 import WorkflowV1
from skat_ai.bounded_search_result import (
    BOUNDED_SEARCH_METHODS,
    BOUNDED_SEARCH_STATUSES,
    BOUNDED_SEARCH_STOP_REASONS,
    AggregateSearchCandidateResult,
    rank_search_candidate_results,
)
from skat_ai.deck import get_full_deck
from skat_ai.game_declaration import GameDeclaration
from skat_ai.information_set_search_contracts import (
    BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD,
    INFORMATION_SET_SEARCH_BUDGET_VERSION,
    INFORMATION_SET_SEARCH_CLAIM_POLICY,
    INFORMATION_SET_SEARCH_CONTROL_SCOPES,
    INFORMATION_SET_SEARCH_CONTROLLED_PLAYERS,
    INFORMATION_SET_SEARCH_CONTROLLED_POLICY,
    INFORMATION_SET_SEARCH_EQUIVALENCE_POLICY,
    INFORMATION_SET_SEARCH_EXECUTION_POLICY,
    INFORMATION_SET_SEARCH_FIXED_PLAYER_POLICY,
    INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY,
    INFORMATION_SET_SEARCH_FIXED_POLICY_VALUES,
    INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS,
    INFORMATION_SET_SEARCH_OBSERVATION_POLICY,
    INFORMATION_SET_SEARCH_OBSERVATION_VERSION,
    INFORMATION_SET_SEARCH_OUT_OF_PLAY_POLICY,
    INFORMATION_SET_SEARCH_PARTNER_POLICY,
    INFORMATION_SET_SEARCH_POLICY_CLAIMS,
    INFORMATION_SET_SEARCH_POLICY_CONSISTENCY_VALUES,
    INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
    INFORMATION_SET_SEARCH_PREPARATION_STATUSES,
    INFORMATION_SET_SEARCH_PREPARATION_VERSION,
    INFORMATION_SET_SEARCH_PUBLIC_HAND_POLICY,
    INFORMATION_SET_SEARCH_PUBLIC_POLICY,
    INFORMATION_SET_SEARCH_REQUEST_VERSION,
    INFORMATION_SET_SEARCH_RESULT_VERSION,
    INFORMATION_SET_SEARCH_SOURCE_POLICY,
    INFORMATION_SET_SEARCH_STATUSES,
    INFORMATION_SET_SEARCH_STOP_REASONS,
    INFORMATION_SET_SEARCH_STRATEGY_FUSION_POLICY,
    INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS,
    INFORMATION_SET_SEARCH_UTILITY_POLICY,
    INFORMATION_SET_SEARCH_VOID_POLICY,
    INFORMATION_SET_SEARCH_WORLD_STATE_POLICY,
    INFORMATION_SET_SEARCH_WORLD_STATE_VERSION,
    INFORMATION_SET_SEARCH_WORLD_WEIGHT_POLICY,
    InformationSetFixedPlayerPolicyV1,
    InformationSetSearchBudgetV1,
    InformationSetSearchConsumedBudgetV1,
    InformationSetSearchPolicySettingsV1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _budget(**changes: object) -> InformationSetSearchBudgetV1:
    values = {
        "information_set_search_budget_version": 1,
        "max_remaining_tricks": 3,
        "max_depth_plies": 9,
        "max_state_nodes": 10_000,
        "max_information_sets": 2_000,
        "max_selected_worlds": 32,
        "max_sampled_worlds": 16,
        "minimum_comparable_worlds": 1,
        "wall_clock_timeout_ms": None,
    }
    return InformationSetSearchBudgetV1(**(values | changes))


def _fixed_policy(
    player: str,
    *,
    lead_policy: str = "lowest_point",
    response_policy: str = "basic_trick_play",
) -> InformationSetFixedPlayerPolicyV1:
    return InformationSetFixedPlayerPolicyV1(
        player=player,
        lead_policy=lead_policy,
        response_policy=response_policy,
        tie_policy="first_canonical_preferred_card",
    )


def _policy_settings() -> InformationSetSearchPolicySettingsV1:
    return InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=1,
        controlled_player="me",
        control_scope="root_perspective_only",
        fixed_player_policies=(_fixed_policy("left"), _fixed_policy("right")),
    )


def test_versions_vocabularies_reasons_and_policies_are_exact() -> None:
    assert (
        INFORMATION_SET_SEARCH_WORLD_STATE_VERSION,
        INFORMATION_SET_SEARCH_OBSERVATION_VERSION,
        INFORMATION_SET_SEARCH_POLICY_SETTINGS_VERSION,
        INFORMATION_SET_SEARCH_BUDGET_VERSION,
        INFORMATION_SET_SEARCH_REQUEST_VERSION,
        INFORMATION_SET_SEARCH_PREPARATION_VERSION,
        INFORMATION_SET_SEARCH_RESULT_VERSION,
    ) == (1, 1, 1, 1, 1, 1, 1)
    assert BOUNDED_INFORMATION_SET_POLICY_SEARCH_METHOD == (
        "bounded_information_set_policy_search_v1"
    )
    assert INFORMATION_SET_SEARCH_CONTROLLED_PLAYERS == ("me",)
    assert INFORMATION_SET_SEARCH_CONTROL_SCOPES == ("root_perspective_only",)
    assert INFORMATION_SET_SEARCH_MAXIMUM_REMAINING_TRICKS == 3
    assert INFORMATION_SET_SEARCH_PREPARATION_STATUSES == ("available", "unavailable")
    assert INFORMATION_SET_SEARCH_STATUSES == (
        "complete",
        "partial",
        "timeout",
        "unavailable",
    )
    assert INFORMATION_SET_SEARCH_POLICY_CLAIMS == (
        "none",
        "common_policy_prefix",
        "exact_selected_world_policy",
    )
    assert INFORMATION_SET_SEARCH_POLICY_CONSISTENCY_VALUES == (
        "not_assessed",
        "controlled_player_information_set_consistent",
    )
    assert INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS == (
        "unsupported_game_type",
        "unsupported_turn_phase",
        "unsupported_perspective",
        "local_player_not_to_act",
        "missing_concrete_declarer",
        "remaining_trick_limit_exceeded",
        "incompatible_world_space",
        "missing_terminal_utility_inputs",
        "game_already_complete",
        "no_legal_cards",
        "unsupported_fixed_policy",
        "nondeterministic_fixed_policy",
        "information_set_model_unavailable",
    )
    assert INFORMATION_SET_SEARCH_STOP_REASONS == (
        "completed",
        "state_node_budget_exhausted",
        "information_set_budget_exhausted",
        "depth_budget_exhausted",
        "wall_clock_timeout",
        *INFORMATION_SET_SEARCH_UNAVAILABLE_REASONS,
    )
    assert INFORMATION_SET_SEARCH_FIXED_POLICY_VALUES == (
        "lowest_point",
        "highest_point",
        "basic_trick_play",
        "basic_defender_response",
        "basic_defender_lead",
    )
    assert (
        INFORMATION_SET_SEARCH_SOURCE_POLICY,
        INFORMATION_SET_SEARCH_WORLD_STATE_POLICY,
        INFORMATION_SET_SEARCH_OBSERVATION_POLICY,
        INFORMATION_SET_SEARCH_EQUIVALENCE_POLICY,
        INFORMATION_SET_SEARCH_CONTROLLED_POLICY,
        INFORMATION_SET_SEARCH_FIXED_PLAYER_POLICY,
        INFORMATION_SET_SEARCH_PARTNER_POLICY,
        INFORMATION_SET_SEARCH_OUT_OF_PLAY_POLICY,
        INFORMATION_SET_SEARCH_PUBLIC_HAND_POLICY,
        INFORMATION_SET_SEARCH_VOID_POLICY,
        INFORMATION_SET_SEARCH_WORLD_WEIGHT_POLICY,
        INFORMATION_SET_SEARCH_FIXED_POLICY_TIE_POLICY,
        INFORMATION_SET_SEARCH_UTILITY_POLICY,
        INFORMATION_SET_SEARCH_STRATEGY_FUSION_POLICY,
        INFORMATION_SET_SEARCH_CLAIM_POLICY,
        INFORMATION_SET_SEARCH_EXECUTION_POLICY,
        INFORMATION_SET_SEARCH_PUBLIC_POLICY,
    ) == (
        "existing_information_view_and_selected_compatible_worlds",
        "exact_state_plus_complete_public_history",
        "actor_own_hand_private_facts_and_public_history_only",
        "equal_actor_observations_define_one_information_set",
        "optimize_root_perspective_policy_over_information_sets",
        "non_controlled_players_use_fixed_information_safe_policies",
        "defender_partner_remains_separate_fixed_policy_actor",
        "exact_discards_visible_only_to_non_hand_declarer",
        "authorized_public_hands_visible_to_all_and_shrink_with_play",
        "confirmed_voids_derive_from_public_play_only",
        "selected_world_order_and_sampled_duplicate_weight_are_preserved",
        "first_canonical_preferred_card",
        "existing_local_side_terminal_utility",
        "one_controlled_action_per_equal_information_set",
        "best_response_to_fixed_policies_not_equilibrium_or_general_optimality",
        "contracts_and_preparation_without_policy_search_execution",
        "private_internal_without_public_schema_or_routing",
    )


def test_budget_is_strict_frozen_slotted_and_deterministic() -> None:
    budget = _budget(wall_clock_timeout_ms=250)
    assert [field.name for field in fields(budget)] == [
        "information_set_search_budget_version",
        "max_remaining_tricks",
        "max_depth_plies",
        "max_state_nodes",
        "max_information_sets",
        "max_selected_worlds",
        "max_sampled_worlds",
        "minimum_comparable_worlds",
        "wall_clock_timeout_ms",
    ]
    assert not hasattr(budget, "__dict__")
    assert list(budget.to_dict()) == [field.name for field in fields(budget)]
    json.dumps(budget.to_dict(), allow_nan=False)
    with pytest.raises(FrozenInstanceError):
        budget.max_state_nodes = 5  # type: ignore[misc]
    with pytest.raises(TypeError):
        InformationSetSearchBudgetV1(1, 3, 9, 10, 10, 10, 10, 1, None)  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"information_set_search_budget_version": True},
        {"information_set_search_budget_version": 2},
        {"max_remaining_tricks": 4},
        {"max_depth_plies": True},
        {"max_state_nodes": 0},
        {"max_information_sets": -1},
        {"max_selected_worlds": 4, "max_sampled_worlds": 5},
        {"max_selected_worlds": 4, "minimum_comparable_worlds": 5},
        {"wall_clock_timeout_ms": 0},
        {"wall_clock_timeout_ms": True},
    ],
)
def test_budget_rejects_invalid_limits(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        _budget(**changes)


def test_fixed_policy_settings_are_exact_canonical_and_private() -> None:
    settings = InformationSetSearchPolicySettingsV1(
        information_set_search_policy_settings_version=1,
        controlled_player="me",
        control_scope="root_perspective_only",
        fixed_player_policies=(_fixed_policy("right"), _fixed_policy("left")),
    )
    assert tuple(policy.player for policy in settings.fixed_player_policies) == (
        "left",
        "right",
    )
    assert settings.to_dict()["fixed_player_policies"][0]["player"] == "left"
    assert not hasattr(settings, "__dict__")
    json.dumps(settings.to_dict(), allow_nan=False)

    for policies in (
        (_fixed_policy("left"),),
        (_fixed_policy("left"), _fixed_policy("left")),
    ):
        with pytest.raises(ValueError):
            InformationSetSearchPolicySettingsV1(
                information_set_search_policy_settings_version=1,
                controlled_player="me",
                control_scope="root_perspective_only",
                fixed_player_policies=policies,
            )
    for invalid in ("random_legal", "unknown"):
        with pytest.raises(ValueError):
            _fixed_policy("left", lead_policy=invalid)
    with pytest.raises(ValueError):
        _fixed_policy("me")


def test_consumed_budget_rejects_booleans_and_invalid_count_relationships() -> None:
    valid = {
        "depth_reached": 2,
        "state_nodes_evaluated": 10,
        "information_sets_evaluated": 4,
        "controlled_policy_decisions": 3,
        "fixed_policy_decisions": 7,
        "selected_world_count": 5,
        "completed_world_count": 2,
        "sampled_world_count": 5,
        "unique_sampled_world_count": 3,
        "wall_clock_elapsed_ms": 8,
    }
    consumed = InformationSetSearchConsumedBudgetV1(**valid)
    assert list(consumed.to_dict()) == list(valid)
    for changes in (
        {"depth_reached": True},
        {"state_nodes_evaluated": -1},
        {"information_sets_evaluated": 11},
        {"completed_world_count": 6},
        {"sampled_world_count": 4},
        {"unique_sampled_world_count": 6},
        {"controlled_policy_decisions": 8},
        {"controlled_policy_decisions": 5, "fixed_policy_decisions": 0},
    ):
        with pytest.raises(ValueError):
            InformationSetSearchConsumedBudgetV1(**(valid | changes))


def test_existing_search_contracts_and_ranking_are_unchanged() -> None:
    assert BOUNDED_SEARCH_METHODS == (
        "perfect_information_minimax_v1",
        "compatible_world_minimax_v1",
    )
    assert BOUNDED_SEARCH_STATUSES == ("complete", "partial", "timeout", "unavailable")
    assert BOUNDED_SEARCH_STOP_REASONS[0:4] == (
        "completed",
        "node_budget_exhausted",
        "depth_budget_exhausted",
        "wall_clock_timeout",
    )
    cards = get_full_deck()
    candidates = tuple(
        AggregateSearchCandidateResult(
            card=card,
            rank=index,
            is_recommended=False,
            completed_world_count=1,
            local_contract_success_count=1,
            local_contract_success_rate=1.0,
            mean_local_side_game_score=10.0,
            mean_local_side_card_point_margin=2.0,
        )
        for index, card in enumerate((cards[1], cards[0]), start=1)
    )
    ranked = rank_search_candidate_results(candidates, "grand", recommend=True)
    assert tuple(candidate.card for candidate in ranked) == (cards[0], cards[1])
    assert ranked[0].is_recommended is True


def test_new_modules_have_no_solver_public_transport_or_io_imports() -> None:
    module_paths = tuple(
        PROJECT_ROOT / "src" / "skat_ai" / name
        for name in (
            "information_set_search_contracts.py",
            "information_set_search_state.py",
            "information_set_search_policy.py",
            "information_set_search_preparation.py",
        )
    )
    forbidden_import_fragments = (
        "api",
        "cli",
        "coherent_hidden_world",
        "compatible_world_minimax",
        "perfect_information_minimax",
        "effective_opponent_policy",
        "card_selection",
    )
    forbidden_import_roots = {
        "http",
        "os",
        "pathlib",
        "requests",
        "socket",
        "subprocess",
        "urllib",
    }
    forbidden_calls = {
        "solve_compatible_world_minimax",
        "solve_perfect_information_minimax",
        "evaluate_exact_terminal_utility",
        "open",
        "read_bytes",
        "read_text",
        "urlopen",
        "write_bytes",
        "write_text",
    }
    for path in module_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = tuple(
            imported
            for node in ast.walk(tree)
            for imported in (
                (node.module or "",)
                if isinstance(node, ast.ImportFrom)
                else tuple(alias.name for alias in node.names)
                if isinstance(node, ast.Import)
                else ()
            )
        )
        assert not any(
            fragment in imported for fragment in forbidden_import_fragments for imported in imports
        )
        assert forbidden_import_roots.isdisjoint(
            imported.split(".", maxsplit=1)[0] for imported in imports
        )
        calls = {
            node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
        }
        assert forbidden_calls.isdisjoint(calls)


def test_contract_values_do_not_add_equilibrium_or_optimality_fields() -> None:
    forbidden = {"equilibrium", "nash", "optimality", "calibrated_probability"}
    for value_type in (
        InformationSetSearchBudgetV1,
        InformationSetFixedPlayerPolicyV1,
        InformationSetSearchPolicySettingsV1,
        InformationSetSearchConsumedBudgetV1,
    ):
        assert forbidden.isdisjoint(field.name for field in fields(value_type))


def test_declaration_fixture_remains_valid() -> None:
    declaration = GameDeclaration("grand", matadors=1, bid_value=24)
    assert declaration.game_type == "grand"


def test_public_package_schema_example_and_scenario_baselines_are_unchanged() -> None:
    private_names = {
        "InformationSetSearchWorldStateV1",
        "InformationSetSearchObservationV1",
        "InformationSetSearchRequestV1",
        "InformationSetSearchPreparationV1",
        "InformationSetSearchResultV1",
    }
    assert private_names.isdisjoint(api_v1.__all__)
    assert skat_ai.__all__ == ("api", "errors", "__version__")
    assert len(WorkflowV1) == 7
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 69
    assert (
        len(tuple((PROJECT_ROOT / "src" / "skat_ai" / "schema_resources").glob("*.schema.json")))
        == 69
    )
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    assert len(SCENARIOS) == 94
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["version"] == skat_ai.__version__ == "0.16.0"
    assert project["requires-python"] == ">=3.13"
    assert project["scripts"] == {"skat-ai": "skat_ai.cli:main"}
