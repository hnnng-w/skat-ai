from __future__ import annotations

import random
from dataclasses import replace
from typing import Any

from skat_ai.canonical_multi_step_phase import COMPLETE_CURRENT_TRICK_THEN_CONTINUE
from skat_ai.card_selection import (
    LEGACY_CARD_SELECTION_POLICIES,
    SEARCH_AWARE_MULTI_STEP_POLICIES,
    VALID_MULTI_STEP_POLICIES,
    choose_card_by_policy,
)
from skat_ai.coherent_hidden_world import (
    CoherentHiddenWorld,
    build_coherent_hidden_world,
    build_hidden_world_summary,
    derive_simulation_child_seed,
    reconcile_hidden_world_with_state,
    validate_coherent_hidden_world,
)
from skat_ai.effective_opponent_policy import EffectiveOpponentPolicySettings
from skat_ai.game_declaration import GameDeclaration
from skat_ai.game_state import GameState
from skat_ai.hidden_card_inference import (
    HiddenCardInferenceModel,
    build_hidden_card_inference_model,
    build_hidden_card_inference_summary,
)
from skat_ai.information_set_search_multi_step import (
    build_information_set_search_multi_step_decision_v1,
    derive_information_set_search_multi_step_configuration_v1,
    validate_information_set_search_multi_step_inputs_v1,
)
from skat_ai.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD,
)
from skat_ai.multi_step_recommendation import (
    LOCAL_POLICY_NO_RECOMMENDATION,
    MULTI_STEP_BOUNDED_SEARCH_DECISION_STREAM,
    build_multi_step_recommendation_decision,
)
from skat_ai.multi_step_summary import build_multi_step_summary
from skat_ai.opponent_sequence import (
    can_prepare_player_action,
    extract_opponent_sequence_cards,
    get_canonical_multi_step_phase_plan,
    get_unsupported_turn_phase_reason,
    prepare_player_action_state,
)
from skat_ai.public_hand_constraint import (
    PublicHandConstraint,
    remove_public_hand_cards,
)
from skat_ai.recommendation_workflow import (
    RecommendationMethodConfiguration,
    build_serializable_information_set_search_settings,
    execute_recommendation_workflow,
)
from skat_ai.rules import get_legal_cards
from skat_ai.simulation_context import (
    SimulationContext,
    add_simulated_opponent_plays,
    add_simulation_event,
    apply_context_to_state_for_sampling,
    build_context_summary,
    update_hidden_world,
    update_public_hand_constraints,
    validate_simulation_context,
)
from skat_ai.simulation_provenance import (
    DecisionProvenanceHook,
    build_safe_selection_settings,
)
from skat_ai.simulation_step import simulate_and_advance_once
from skat_ai.strategic_metadata import StrategicMetadata


def should_continue_multi_step_simulation(
    current_state: GameState,
    step_index: int,
) -> bool:
    """
    Determines whether the multi-step simulation should continue.

    A step continues only if the engine can act locally, prepare to a local
    action, or complete the existing Trick and continue from its winner.
    """
    _ = step_index

    return can_prepare_player_action(current_state)


def get_multi_step_stop_reason(
    current_state: GameState,
    step_index: int,
    strategic_metadata: StrategicMetadata | None = None,
) -> str | None:
    """
    Returns a human-readable stop reason if simulation should stop.
    """
    if (
        strategic_metadata is not None
        and strategic_metadata.game_end_reason != "not_ended"
    ):
        return "Game is already complete."

    if current_state.hand == []:
        phase_plan = get_canonical_multi_step_phase_plan(current_state)
        if (
            phase_plan is None
            or phase_plan.phase_action != COMPLETE_CURRENT_TRICK_THEN_CONTINUE
        ):
            return "Player has no cards left."

    _ = step_index

    if not can_prepare_player_action(current_state):
        return get_unsupported_turn_phase_reason()

    return None


def prepare_state_for_player_action(
    current_state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    random_generator: random.Random,
    opponent_lead_policy: str = "lowest_point",
    opponent_response_policy: str = "lowest_point",
    left_opponent_policy_settings: dict[str, str] | None = None,
    right_opponent_policy_settings: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    coherent_hidden_world: CoherentHiddenWorld | None = None,
    coherent_step_index: int = 0,
) -> tuple[GameState, dict[str, Any] | None]:
    """
    Kept as a compatibility wrapper around opponent_sequence.prepare_player_action_state.
    """
    return prepare_player_action_state(
        current_state=current_state,
        left_hand_size=left_hand_size,
        right_hand_size=right_hand_size,
        random_generator=random_generator,
        opponent_lead_policy=opponent_lead_policy,
        opponent_response_policy=opponent_response_policy,
        left_opponent_policy_settings=left_opponent_policy_settings,
        right_opponent_policy_settings=right_opponent_policy_settings,
        public_hand_constraints=public_hand_constraints,
        coherent_hidden_world=coherent_hidden_world,
        coherent_step_index=coherent_step_index,
    )

def extract_opponent_cards_from_step(
    step: dict[str, Any],
) -> list[str]:
    """
    Extracts simulated opponent cards from one multi-step result.

    Sources:
    - opponent sequence cards
    - opponent cards inside the completed trick, excluding the candidate card
    """
    opponent_cards = extract_opponent_sequence_cards(
        step.get("opponent_lead_result")
    )

    detailed_result = step["detailed_result"]
    trick = detailed_result["trick"]
    candidate_card = step["candidate_card"]

    for card in trick:
        if card != candidate_card and card not in opponent_cards:
            opponent_cards.append(card)

    return opponent_cards


def _advance_public_opponent_hand_sizes(
    left_hand_size: int,
    right_hand_size: int,
    plays: tuple[tuple[str, str], ...],
) -> tuple[int, int]:
    """Applies attributed public opponent actions to public hand counts."""
    for player, _card in plays:
        if player == "left":
            left_hand_size -= 1
        elif player == "right":
            right_hand_size -= 1
        else:
            raise ValueError(f"Unexpected opponent play owner: {player}")
        if left_hand_size < 0 or right_hand_size < 0:
            raise ValueError("Public opponent hand-size accounting became negative.")
    return left_hand_size, right_hand_size


def _validate_search_policy_inputs(
    card_selection_policy: str,
    game_declaration: GameDeclaration | None,
    recommendation_configuration: RecommendationMethodConfiguration | None,
    strategic_metadata: StrategicMetadata | None,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None,
) -> None:
    if card_selection_policy not in VALID_MULTI_STEP_POLICIES:
        raise ValueError(f"Invalid card selection policy: {card_selection_policy}")
    if card_selection_policy in LEGACY_CARD_SELECTION_POLICIES:
        return
    if card_selection_policy == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        validate_information_set_search_multi_step_inputs_v1(
            game_declaration=game_declaration,
            recommendation_configuration=recommendation_configuration,
            strategic_metadata=strategic_metadata,
            effective_opponent_policy_settings=effective_opponent_policy_settings,
        )
        return
    if not isinstance(game_declaration, GameDeclaration):
        raise ValueError("Search-aware Multi-Step requires a normalized game declaration.")
    if not isinstance(
        recommendation_configuration,
        RecommendationMethodConfiguration,
    ):
        raise ValueError("Search-aware Multi-Step requires Search method configuration.")
    if recommendation_configuration.requested_method != card_selection_policy:
        raise ValueError("Multi-Step Search policy and recommendation method must match.")
    if recommendation_configuration.search_random_seed is None:
        raise ValueError("Search-aware Multi-Step requires an explicit Search base seed.")
    if recommendation_configuration.requested_search_budget is None:
        raise ValueError("Search-aware Multi-Step requires a requested Search budget.")
    if strategic_metadata is None:
        raise ValueError("Search-aware Multi-Step requires live strategic metadata.")
    if strategic_metadata.analysis_mode != "live_decision":
        raise ValueError("Search-aware Multi-Step requires analysis_mode='live_decision'.")
    if strategic_metadata.game_end_reason != "not_ended":
        raise ValueError("Search-aware Multi-Step requires game_end_reason='not_ended'.")

def simulate_multiple_steps(
    state: GameState,
    left_hand_size: int,
    right_hand_size: int,
    step_count: int,
    random_seed: int | None = None,
    use_basic_opponent_strategy: bool = True,
    card_selection_policy: str = "first_legal",
    expected_value_sample_count: int = 100,
    strict_context: bool = False,
    strategic_metadata: StrategicMetadata | None = None,
    opponent_lead_policy: str = "lowest_point",
    opponent_response_policy: str = "lowest_point",
    left_opponent_policy_settings: dict[str, str] | None = None,
    right_opponent_policy_settings: dict[str, str] | None = None,
    opponent_response_policy_by_player: dict[str, str] | None = None,
    public_hand_constraints: tuple[PublicHandConstraint, ...] = (),
    initial_hidden_world: CoherentHiddenWorld | None = None,
    initial_hidden_card_inference_model: HiddenCardInferenceModel | None = None,
    game_declaration: GameDeclaration | None = None,
    recommendation_configuration: RecommendationMethodConfiguration | None = None,
    effective_opponent_policy_settings: EffectiveOpponentPolicySettings | None = None,
    decision_provenance_hook: DecisionProvenanceHook | None = None,
) -> dict[str, Any]:
    """
    Simulates multiple sequential player-action steps.

    One private hidden-card world is sampled at path start and evolves only
    through immutable opponent-card removals. Local candidate policies receive
    public state and constraints, never private unplayed world ownership.
    """
    if step_count <= 0:
        raise ValueError("step_count must be a positive integer.")
    _validate_search_policy_inputs(
        card_selection_policy,
        game_declaration,
        recommendation_configuration,
        strategic_metadata,
        effective_opponent_policy_settings,
    )
    if card_selection_policy == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
        assert effective_opponent_policy_settings is not None
        opponent_lead_policy = effective_opponent_policy_settings.global_lead_policy
        opponent_response_policy = (
            effective_opponent_policy_settings.global_response_policy
        )
        left_opponent_policy_settings = {
            "opponent_lead_policy": effective_opponent_policy_settings.left_lead_policy,
            "opponent_response_policy": (
                effective_opponent_policy_settings.left_response_policy
            ),
        }
        right_opponent_policy_settings = {
            "opponent_lead_policy": effective_opponent_policy_settings.right_lead_policy,
            "opponent_response_policy": (
                effective_opponent_policy_settings.right_response_policy
            ),
        }
        opponent_response_policy_by_player = {
            "left": effective_opponent_policy_settings.left_response_policy,
            "right": effective_opponent_policy_settings.right_response_policy,
        }
    if decision_provenance_hook is not None and (
        strategic_metadata is None or game_declaration is None
    ):
        raise ValueError(
            "Decision Provenance requires live strategic metadata and a game declaration."
        )

    root_seed = derive_simulation_child_seed(random_seed, "root_world")
    opponent_action_seed = derive_simulation_child_seed(
        random_seed,
        "opponent_actions",
    )
    opponent_action_rng = random.Random(opponent_action_seed)
    root_inference_model = (
        initial_hidden_card_inference_model
        or build_hidden_card_inference_model(
            state,
            left_hand_size,
            right_hand_size,
            public_hand_constraints,
        )
    )

    if initial_hidden_world is None:
        hidden_world = build_coherent_hidden_world(
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            random_generator=random.Random(root_seed),
            public_hand_constraints=public_hand_constraints,
            hidden_card_inference_model=root_inference_model,
        )
    else:
        validate_coherent_hidden_world(
            initial_hidden_world,
            state=state,
            left_hand_size=left_hand_size,
            right_hand_size=right_hand_size,
            public_hand_constraints=public_hand_constraints,
            hidden_card_inference_constraints=(
                root_inference_model.constraints
                if root_inference_model is not None
                else None
            ),
        )
        if initial_hidden_world.ownership_transitions:
            raise ValueError(
                "initial_hidden_world must be an unplayed root world without "
                "ownership transitions."
            )
        hidden_world = initial_hidden_world

    current_state = state
    public_left_hand_size = left_hand_size
    public_right_hand_size = right_hand_size
    steps = []
    stop_reason = None
    stopped_recommendation_decision = None
    context = (
        SimulationContext(
            strategic_metadata=strategic_metadata,
            public_hand_constraints=public_hand_constraints,
            hidden_world=hidden_world,
            root_hidden_world=hidden_world,
        )
        if strategic_metadata is not None
        else SimulationContext(
            public_hand_constraints=public_hand_constraints,
            hidden_world=hidden_world,
            root_hidden_world=hidden_world,
        )
    )

    for step_index in range(step_count):
        stop_reason = get_multi_step_stop_reason(
            current_state=current_state,
            step_index=step_index,
            strategic_metadata=strategic_metadata,
        )

        if stop_reason is not None:
            break

        if not should_continue_multi_step_simulation(
            current_state=current_state,
            step_index=step_index,
        ):
            stop_reason = get_unsupported_turn_phase_reason()
            break

        sampling_state = apply_context_to_state_for_sampling(
            state=current_state,
            context=context,
        )

        if context.hidden_world is None:
            raise ValueError(
                f"Hidden-world ownership invariant violated at step {step_index}: "
                "coherent path world is missing."
            )
        current_world = context.hidden_world
        if (
            len(current_world.left_hand) != public_left_hand_size
            or len(current_world.right_hand) != public_right_hand_size
        ):
            raise ValueError("Public and coherent-world opponent hand sizes disagree.")
        reconcile_hidden_world_with_state(
            current_world,
            sampling_state,
            context.public_hand_constraints,
            hidden_card_inference_constraints=(
                root_inference_model.constraints
                if step_index == 0 and root_inference_model is not None
                else None
            ),
            step_index=step_index,
        )
        prepared_state, opponent_lead_result = prepare_state_for_player_action(
            current_state=sampling_state,
            left_hand_size=public_left_hand_size,
            right_hand_size=public_right_hand_size,
            random_generator=opponent_action_rng,
            opponent_lead_policy=opponent_lead_policy,
            opponent_response_policy=opponent_response_policy,
            left_opponent_policy_settings=left_opponent_policy_settings,
            right_opponent_policy_settings=right_opponent_policy_settings,
            public_hand_constraints=context.public_hand_constraints,
            coherent_hidden_world=current_world,
            coherent_step_index=step_index,
        )

        preparation_plays: tuple[tuple[str, str], ...] = ()
        prepared_world = current_world
        if opponent_lead_result is not None:
            preparation_plays = opponent_lead_result.get("_opponent_plays", ())
            prepared_world = opponent_lead_result.get(
                "_coherent_hidden_world",
                current_world,
            )
        prepared_constraints = remove_public_hand_cards(
            context.public_hand_constraints,
            [card for _, card in preparation_plays],
        )
        prepared_left_hand_size, prepared_right_hand_size = (
            _advance_public_opponent_hand_sizes(
                public_left_hand_size,
                public_right_hand_size,
                preparation_plays,
            )
        )
        if (
            len(prepared_world.left_hand) != prepared_left_hand_size
            or len(prepared_world.right_hand) != prepared_right_hand_size
        ):
            raise ValueError("Prepared public and coherent-world hand sizes disagree.")
        if prepared_state.hand == []:
            terminal_inference_model = build_hidden_card_inference_model(
                prepared_state,
                prepared_left_hand_size,
                prepared_right_hand_size,
                prepared_constraints,
            )
            reconcile_hidden_world_with_state(
                prepared_world,
                prepared_state,
                prepared_constraints,
                hidden_card_inference_constraints=(
                    terminal_inference_model.constraints
                    if terminal_inference_model is not None
                    else None
                ),
                step_index=step_index,
            )
            context = add_simulated_opponent_plays(context, preparation_plays)
            context = update_public_hand_constraints(context, prepared_constraints)
            context = update_hidden_world(context, prepared_world)
            if preparation_plays:
                context = add_simulation_event(
                    context,
                    {
                        "type": "opponent_preparation_before_local_stop",
                        "step_index": step_index,
                        "opponent_cards": [
                            card for _, card in preparation_plays
                        ],
                        "opponent_plays": preparation_plays,
                    },
                )
            current_state = prepared_state
            public_left_hand_size = prepared_left_hand_size
            public_right_hand_size = prepared_right_hand_size
            stop_reason = "Player has no cards left."
            if strict_context:
                validate_simulation_context(
                    context,
                    current_state,
                    step_index=step_index,
                )
            break
        if decision_provenance_hook is not None:
            assert strategic_metadata is not None
            assert game_declaration is not None
            selection_settings = build_safe_selection_settings(
                sample_count=expected_value_sample_count,
                use_basic_opponent_strategy=use_basic_opponent_strategy,
                opponent_response_policy_by_player=(
                    opponent_response_policy_by_player or {}
                ),
                requested_search_budget=(
                    recommendation_configuration.requested_search_budget
                    if recommendation_configuration is not None
                    else None
                ),
            )
            if card_selection_policy == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
                assert recommendation_configuration is not None
                selection_settings["information_set_search_settings"] = (
                    build_serializable_information_set_search_settings(
                        recommendation_configuration
                    )
                )
            decision_provenance_hook(
                state=prepared_state,
                left_hand_size=prepared_left_hand_size,
                right_hand_size=prepared_right_hand_size,
                public_hand_constraints=prepared_constraints,
                strategic_metadata=strategic_metadata,
                game_declaration=game_declaration,
                decision_index=step_index,
                selection_method=card_selection_policy,
                selection_settings=selection_settings,
            )
        prepared_inference_model = build_hidden_card_inference_model(
            prepared_state,
            prepared_left_hand_size,
            prepared_right_hand_size,
            prepared_constraints,
        )
        reconcile_hidden_world_with_state(
            prepared_world,
            prepared_state,
            prepared_constraints,
            hidden_card_inference_constraints=(
                prepared_inference_model.constraints
                if prepared_inference_model is not None
                else None
            ),
            step_index=step_index,
        )

        immediate_seed = derive_simulation_child_seed(
            random_seed,
            "expected_value_samples",
            child_index=step_index,
        )
        recommendation_decision = None
        if card_selection_policy in SEARCH_AWARE_MULTI_STEP_POLICIES:
            if game_declaration is None or recommendation_configuration is None:
                raise ValueError("Search-aware Multi-Step configuration is missing.")
            if card_selection_policy == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD:
                decision_configuration = (
                    derive_information_set_search_multi_step_configuration_v1(
                        recommendation_configuration,
                        step_index=step_index,
                    )
                )
            else:
                decision_configuration = replace(
                    recommendation_configuration,
                    search_random_seed=derive_simulation_child_seed(
                        recommendation_configuration.search_random_seed,
                        MULTI_STEP_BOUNDED_SEARCH_DECISION_STREAM,
                        child_index=step_index,
                    ),
                )
            recommendation_workflow = execute_recommendation_workflow(
                configuration=decision_configuration,
                state=prepared_state,
                declaration=game_declaration,
                left_hand_size=prepared_left_hand_size,
                right_hand_size=prepared_right_hand_size,
                sample_count=expected_value_sample_count,
                immediate_random_seed=immediate_seed,
                use_basic_opponent_strategy=use_basic_opponent_strategy,
                opponent_response_policy_by_player=(
                    opponent_response_policy_by_player or {}
                ),
                public_hand_constraints=prepared_constraints,
                skat_visibility=strategic_metadata.skat_visibility,
                immediate_unavailable_reason=None,
                effective_opponent_policy_settings=(
                    effective_opponent_policy_settings
                    if card_selection_policy
                    == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
                    else None
                ),
            )
            recommendation_decision = (
                build_information_set_search_multi_step_decision_v1(
                    step_index=step_index,
                    workflow=recommendation_workflow,
                )
                if card_selection_policy
                == INFORMATION_SET_SEARCH_RECOMMENDATION_METHOD
                else build_multi_step_recommendation_decision(
                    step_index,
                    recommendation_workflow,
                )
            )
            candidate_card = recommendation_decision.recommendation_card
            if candidate_card is None:
                context = add_simulated_opponent_plays(context, preparation_plays)
                context = update_public_hand_constraints(context, prepared_constraints)
                context = update_hidden_world(context, prepared_world)
                if preparation_plays:
                    context = add_simulation_event(
                        context,
                        {
                            "type": "opponent_preparation_before_local_stop",
                            "step_index": step_index,
                            "opponent_cards": [card for _, card in preparation_plays],
                            "opponent_plays": preparation_plays,
                        },
                    )
                current_state = prepared_state
                public_left_hand_size = prepared_left_hand_size
                public_right_hand_size = prepared_right_hand_size
                if strict_context:
                    validate_simulation_context(
                        context,
                        current_state,
                        step_index=step_index,
                    )
                stopped_recommendation_decision = recommendation_decision
                stop_reason = LOCAL_POLICY_NO_RECOMMENDATION
                break
        else:
            candidate_card = choose_card_by_policy(
                state=prepared_state,
                policy=card_selection_policy,
                left_hand_size=prepared_left_hand_size,
                right_hand_size=prepared_right_hand_size,
                expected_value_sample_count=expected_value_sample_count,
                random_seed=immediate_seed,
                use_basic_opponent_strategy=use_basic_opponent_strategy,
                opponent_response_policy_by_player=opponent_response_policy_by_player,
                public_hand_constraints=prepared_constraints,
                hidden_card_inference_model=prepared_inference_model,
            )

        if candidate_card not in prepared_state.hand or candidate_card not in get_legal_cards(
            prepared_state.hand,
            prepared_state.current_trick,
            prepared_state.game_type,
        ):
            raise ValueError("The local policy selected an illegal or unowned card.")

        step_result = simulate_and_advance_once(
            state=prepared_state,
            candidate_card=candidate_card,
            left_hand_size=prepared_left_hand_size,
            right_hand_size=prepared_right_hand_size,
            random_generator=opponent_action_rng,
            use_basic_opponent_strategy=use_basic_opponent_strategy,
            opponent_response_policy_by_player=opponent_response_policy_by_player,
            public_hand_constraints=prepared_constraints,
            coherent_hidden_world=prepared_world,
            coherent_step_index=step_index,
            hidden_card_inference_model=prepared_inference_model,
        )
        updated_world = step_result["coherent_hidden_world"]
        completion_plays: tuple[tuple[str, str], ...] = step_result[
            "opponent_plays"
        ]
        opponent_plays = (*preparation_plays, *completion_plays)
        public_left_hand_size, public_right_hand_size = (
            _advance_public_opponent_hand_sizes(
                prepared_left_hand_size,
                prepared_right_hand_size,
                completion_plays,
            )
        )
        if (
            len(updated_world.left_hand) != public_left_hand_size
            or len(updated_world.right_hand) != public_right_hand_size
        ):
            raise ValueError("Updated public and coherent-world hand sizes disagree.")

        step = {
            "step_index": step_index,
            "opponent_lead_result": opponent_lead_result,
            "prepared_state": prepared_state,
            "candidate_card": candidate_card,
            "card_selection_policy": card_selection_policy,
            "detailed_result": step_result["detailed_result"],
            "next_state": step_result["next_state"],
            "coherence_summary": build_hidden_world_summary(updated_world),
        }
        if recommendation_decision is not None:
            step["recommendation_decision"] = recommendation_decision
        prepared_inference_summary = build_hidden_card_inference_summary(
            prepared_inference_model
        )
        if prepared_inference_summary is not None:
            step["hidden_card_inference_summary"] = prepared_inference_summary

        opponent_cards = [card for _, card in opponent_plays]
        context = add_simulated_opponent_plays(
            context=context,
            plays=opponent_plays,
        )
        context = update_public_hand_constraints(
            context,
            remove_public_hand_cards(
                prepared_constraints,
                step_result["detailed_result"]["trick"],
            ),
        )
        context = update_hidden_world(context, updated_world)

        context = add_simulation_event(
            context=context,
            event={
                "type": "player_action_step",
                "step_index": step_index,
                "candidate_card": candidate_card,
                "opponent_cards": opponent_cards,
                "opponent_plays": opponent_plays,
            },
        )

        if strict_context:
            validate_simulation_context(
                context,
                step_result["next_state"],
                step_index=step_index,
            )
        else:
            reconcile_hidden_world_with_state(
                updated_world,
                step_result["next_state"],
                context.public_hand_constraints,
                step_index=step_index,
            )

        steps.append(step)

        current_state = step_result["next_state"]

    if stop_reason is None and len(steps) == step_count:
        stop_reason = "Requested step count reached."

    result = {
        "initial_state": state,
        "final_state": current_state,
        "card_selection_policy": card_selection_policy,
        "requested_step_count": step_count,
        "steps_simulated": len(steps),
        "stop_reason": stop_reason,
        "strict_context": strict_context,
        "opponent_policy_settings": {
            "opponent_lead_policy": opponent_lead_policy,
            "opponent_response_policy": opponent_response_policy,
        },
        "left_opponent_policy_settings": left_opponent_policy_settings,
        "right_opponent_policy_settings": right_opponent_policy_settings,
        "context": context,
        "context_summary": build_context_summary(context),
        "steps": steps,
    }

    if stopped_recommendation_decision is not None:
        result["stopped_recommendation_decision"] = stopped_recommendation_decision

    result["summary"] = build_multi_step_summary(result)
    root_inference_summary = build_hidden_card_inference_summary(root_inference_model)
    if root_inference_summary is not None:
        result["hidden_card_inference_summary"] = root_inference_summary

    return result
