from dataclasses import dataclass
from typing import Any

from skat_ai.opponent_policy import validate_opponent_card_policy
from skat_ai.opponent_policy_preset import get_opponent_policy_settings_for_preset
from skat_ai.opponent_profile_policy import apply_profile_based_side_policy_preset
from skat_ai.player_profile import PlayerProfile, build_default_player_profile

DEFAULT_OPPONENT_LEAD_POLICY = "lowest_point"
DEFAULT_OPPONENT_RESPONSE_POLICY = "lowest_point"


@dataclass(frozen=True)
class EffectiveOpponentPolicySettings:
    """Resolved opponent policies for shared policy precedence."""

    global_lead_policy: str
    global_response_policy: str
    left_lead_policy: str
    left_response_policy: str
    right_lead_policy: str
    right_response_policy: str
    immediate_response_policy_by_player: dict[str, str] | None


def build_effective_opponent_policy_settings(
    data: dict[str, Any],
    left_player_profile: PlayerProfile | None = None,
    right_player_profile: PlayerProfile | None = None,
    opponent_policy_preset_override: str | None = None,
    opponent_lead_policy_override: str | None = None,
    opponent_response_policy_override: str | None = None,
    use_profile_presets_override: bool = False,
    left_opponent_lead_policy_override: str | None = None,
    left_opponent_response_policy_override: str | None = None,
    right_opponent_lead_policy_override: str | None = None,
    right_opponent_response_policy_override: str | None = None,
) -> EffectiveOpponentPolicySettings:
    """
    Builds effective opponent policy settings using the intended unified precedence.

    This resolver is intentionally pure and independent from current orchestration.
    Immediate Analysis activation is represented separately from complete side
    settings so normalized defaults do not activate policy-driven responses.
    """
    left_profile = left_player_profile or build_default_player_profile()
    right_profile = right_player_profile or build_default_player_profile()

    global_lead_policy = DEFAULT_OPPONENT_LEAD_POLICY
    global_response_policy = DEFAULT_OPPONENT_RESPONSE_POLICY
    left_lead_policy = DEFAULT_OPPONENT_LEAD_POLICY
    left_response_policy = DEFAULT_OPPONENT_RESPONSE_POLICY
    right_lead_policy = DEFAULT_OPPONENT_LEAD_POLICY
    right_response_policy = DEFAULT_OPPONENT_RESPONSE_POLICY
    immediate_response_policy_by_player: dict[str, str] = {}

    def apply_global_lead_policy(policy: str) -> None:
        nonlocal global_lead_policy, left_lead_policy, right_lead_policy
        validate_opponent_card_policy(policy)
        global_lead_policy = policy
        left_lead_policy = policy
        right_lead_policy = policy

    def apply_global_response_policy(policy: str, activate_immediate: bool) -> None:
        nonlocal global_response_policy, left_response_policy, right_response_policy
        validate_opponent_card_policy(policy)
        global_response_policy = policy
        left_response_policy = policy
        right_response_policy = policy

        if activate_immediate:
            immediate_response_policy_by_player["left"] = policy
            immediate_response_policy_by_player["right"] = policy

    def apply_global_preset(preset: str) -> None:
        preset_settings = get_opponent_policy_settings_for_preset(preset)
        apply_global_lead_policy(preset_settings["opponent_lead_policy"])
        apply_global_response_policy(
            policy=preset_settings["opponent_response_policy"],
            activate_immediate=True,
        )

    def apply_side_lead_policy(player: str, policy: str) -> None:
        nonlocal left_lead_policy, right_lead_policy
        validate_opponent_card_policy(policy)

        if player == "left":
            left_lead_policy = policy
            return

        if player == "right":
            right_lead_policy = policy
            return

        raise ValueError(f"Invalid opponent player: {player}")

    def apply_side_response_policy(
        player: str,
        policy: str,
        activate_immediate: bool,
    ) -> None:
        nonlocal left_response_policy, right_response_policy
        validate_opponent_card_policy(policy)

        if player == "left":
            left_response_policy = policy
        elif player == "right":
            right_response_policy = policy
        else:
            raise ValueError(f"Invalid opponent player: {player}")

        if activate_immediate:
            immediate_response_policy_by_player[player] = policy

    def apply_profile_side_policy(player: str, profile: PlayerProfile) -> None:
        side_settings = apply_profile_based_side_policy_preset(
            opponent_policy_settings={},
            profile=profile,
            use_profile_presets=True,
        )

        lead_policy = side_settings.get("opponent_lead_policy")
        if lead_policy is not None:
            apply_side_lead_policy(player, lead_policy)

        response_policy = side_settings.get("opponent_response_policy")
        if response_policy is not None:
            apply_side_response_policy(
                player=player,
                policy=response_policy,
                activate_immediate=True,
            )

    if "opponent_policy_preset" in data:
        apply_global_preset(data["opponent_policy_preset"])

    if "opponent_lead_policy" in data:
        apply_global_lead_policy(data["opponent_lead_policy"])

    if "opponent_response_policy" in data:
        apply_global_response_policy(
            policy=data["opponent_response_policy"],
            activate_immediate=True,
        )

    if data.get("use_profile_presets") is True:
        apply_profile_side_policy("left", left_profile)
        apply_profile_side_policy("right", right_profile)

    if "left_opponent_lead_policy" in data:
        apply_side_lead_policy("left", data["left_opponent_lead_policy"])

    if "left_opponent_response_policy" in data:
        apply_side_response_policy(
            player="left",
            policy=data["left_opponent_response_policy"],
            activate_immediate=True,
        )

    if "right_opponent_lead_policy" in data:
        apply_side_lead_policy("right", data["right_opponent_lead_policy"])

    if "right_opponent_response_policy" in data:
        apply_side_response_policy(
            player="right",
            policy=data["right_opponent_response_policy"],
            activate_immediate=True,
        )

    if opponent_policy_preset_override is not None:
        apply_global_preset(opponent_policy_preset_override)

    if use_profile_presets_override:
        apply_profile_side_policy("left", left_profile)
        apply_profile_side_policy("right", right_profile)

    if opponent_lead_policy_override is not None:
        apply_global_lead_policy(opponent_lead_policy_override)

    if opponent_response_policy_override is not None:
        apply_global_response_policy(
            policy=opponent_response_policy_override,
            activate_immediate=True,
        )

    if left_opponent_lead_policy_override is not None:
        apply_side_lead_policy("left", left_opponent_lead_policy_override)

    if left_opponent_response_policy_override is not None:
        apply_side_response_policy(
            player="left",
            policy=left_opponent_response_policy_override,
            activate_immediate=True,
        )

    if right_opponent_lead_policy_override is not None:
        apply_side_lead_policy("right", right_opponent_lead_policy_override)

    if right_opponent_response_policy_override is not None:
        apply_side_response_policy(
            player="right",
            policy=right_opponent_response_policy_override,
            activate_immediate=True,
        )

    return EffectiveOpponentPolicySettings(
        global_lead_policy=global_lead_policy,
        global_response_policy=global_response_policy,
        left_lead_policy=left_lead_policy,
        left_response_policy=left_response_policy,
        right_lead_policy=right_lead_policy,
        right_response_policy=right_response_policy,
        immediate_response_policy_by_player=(
            immediate_response_policy_by_player.copy()
            if immediate_response_policy_by_player
            else None
        ),
    )
