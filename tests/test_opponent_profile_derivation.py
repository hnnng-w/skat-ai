from dataclasses import replace

import pytest

from skat_ai.opponent_profile_derivation import (
    PROFILE_DERIVATION_VERSION,
    derive_opponent_profile,
    get_evidence_confidence,
)
from skat_ai.player_profile import PlayerProfile


def get_signal(profile: PlayerProfile, code: str):
    derivation = derive_opponent_profile(profile)
    return next(signal for signal in derivation.signals if signal.code == code)


def test_derives_exact_overall_declarer_and_defender_evidence() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_games_played=400,
        defender_games_played=600,
        solo_rate=0.40,
        defender_rate=0.60,
    )

    confidence = derive_opponent_profile(profile).confidence

    assert confidence["overall"].evidence_count == 1000.0
    assert confidence["overall"].evidence_kind == "exact"
    assert confidence["declarer"].evidence_count == 400.0
    assert confidence["declarer"].evidence_kind == "exact"
    assert confidence["defender"].evidence_count == 600.0
    assert confidence["defender"].evidence_kind == "exact"


def test_derives_decimal_estimates_from_rates_without_rounding() -> None:
    profile = PlayerProfile(
        games_played=127,
        solo_rate=0.315,
        defender_rate=0.685,
    )

    confidence = derive_opponent_profile(profile).confidence

    assert confidence["declarer"].evidence_count == pytest.approx(40.005)
    assert confidence["declarer"].evidence_kind == "estimated_from_rate"
    assert confidence["defender"].evidence_count == pytest.approx(86.995)
    assert confidence["defender"].evidence_kind == "estimated_from_rate"


def test_derives_defender_estimate_from_solo_rate_complement() -> None:
    confidence = derive_opponent_profile(
        PlayerProfile(games_played=127, solo_rate=0.315)
    ).confidence

    assert confidence["defender"].evidence_count == pytest.approx(86.995)
    assert confidence["defender"].evidence_kind == "estimated_from_complement"


def test_exact_role_counts_take_precedence_over_estimates() -> None:
    profile = PlayerProfile(
        games_played=1000,
        solo_games_played=310,
        defender_games_played=690,
        solo_rate=0.31,
        defender_rate=0.69,
    )

    confidence = derive_opponent_profile(profile).confidence

    assert confidence["declarer"].evidence_count == 310.0
    assert confidence["declarer"].evidence_kind == "exact"
    assert confidence["defender"].evidence_count == 690.0
    assert confidence["defender"].evidence_kind == "exact"


def test_unavailable_evidence_remains_null_and_unknown() -> None:
    confidence = derive_opponent_profile(PlayerProfile()).confidence

    for scope in ("overall", "declarer", "defender"):
        assert confidence[scope].level == "unknown"
        assert confidence[scope].evidence_count is None
        assert confidence[scope].evidence_kind == "unavailable"


@pytest.mark.parametrize(
    "profile",
    [
        PlayerProfile(games_played=100, solo_games_played=101),
        PlayerProfile(games_played=100, defender_games_played=101),
    ],
)
def test_rejects_exact_role_counts_above_total(profile: PlayerProfile) -> None:
    with pytest.raises(ValueError, match="must not exceed games_played"):
        derive_opponent_profile(profile)


def test_rejects_inconsistent_exact_role_count_total() -> None:
    profile = PlayerProfile(
        games_played=100,
        solo_games_played=30,
        defender_games_played=60,
    )

    with pytest.raises(ValueError, match="must sum to games_played"):
        derive_opponent_profile(profile)


@pytest.mark.parametrize(
    "profile",
    [
        PlayerProfile(games_played=1000, solo_games_played=300, solo_rate=0.40),
        PlayerProfile(
            games_played=1000,
            defender_games_played=700,
            defender_rate=0.60,
        ),
        PlayerProfile(
            games_played=1000,
            defender_games_played=700,
            solo_rate=0.40,
        ),
        PlayerProfile(
            games_played=1000,
            solo_games_played=300,
            defender_rate=0.60,
        ),
        PlayerProfile(games_played=1000, solo_rate=0.30, defender_rate=0.60),
    ],
)
def test_rejects_contradictory_exact_counts_and_rates(profile: PlayerProfile) -> None:
    with pytest.raises(ValueError, match="contradict"):
        derive_opponent_profile(profile)


def test_accepts_exact_count_rate_difference_at_rounding_tolerance() -> None:
    derivation = derive_opponent_profile(
        PlayerProfile(games_played=1000, solo_games_played=300, solo_rate=0.32)
    )

    assert derivation.confidence["declarer"].evidence_count == 300.0


@pytest.mark.parametrize(
    ("evidence_count", "expected_level"),
    [
        (None, "unknown"),
        (99.999, "low"),
        (100, "medium"),
        (499.999, "medium"),
        (500, "high"),
    ],
)
def test_confidence_boundaries(
    evidence_count: float | None,
    expected_level: str,
) -> None:
    kind = "unavailable" if evidence_count is None else "estimated_from_rate"

    assert get_evidence_confidence(evidence_count, kind).level == expected_level


@pytest.mark.parametrize(
    ("scope", "profile", "expected_level"),
    [
        ("overall", PlayerProfile(), "unknown"),
        ("overall", PlayerProfile(games_played=99), "low"),
        ("overall", PlayerProfile(games_played=100), "medium"),
        ("overall", PlayerProfile(games_played=499), "medium"),
        ("overall", PlayerProfile(games_played=500), "high"),
        ("declarer", PlayerProfile(games_played=1000), "unknown"),
        ("declarer", PlayerProfile(games_played=1000, solo_rate=0.099999), "low"),
        ("declarer", PlayerProfile(games_played=1000, solo_rate=0.1), "medium"),
        ("declarer", PlayerProfile(games_played=1000, solo_rate=0.499999), "medium"),
        ("declarer", PlayerProfile(games_played=1000, solo_rate=0.5), "high"),
        ("defender", PlayerProfile(games_played=1000), "unknown"),
        ("defender", PlayerProfile(games_played=1000, defender_rate=0.099999), "low"),
        ("defender", PlayerProfile(games_played=1000, defender_rate=0.1), "medium"),
        ("defender", PlayerProfile(games_played=1000, defender_rate=0.499999), "medium"),
        ("defender", PlayerProfile(games_played=1000, defender_rate=0.5), "high"),
    ],
)
def test_scoped_confidence_boundaries(
    scope: str,
    profile: PlayerProfile,
    expected_level: str,
) -> None:
    assert derive_opponent_profile(profile).confidence[scope].level == expected_level


@pytest.mark.parametrize(
    ("code", "field_name", "threshold", "base_profile"),
    [
        ("frequent_declarer", "solo_rate", 0.35, PlayerProfile(games_played=1000)),
        (
            "grand_oriented",
            "grand_rate",
            0.25,
            PlayerProfile(games_played=1000, solo_rate=0.2),
        ),
        (
            "hand_oriented",
            "hand_game_rate",
            0.10,
            PlayerProfile(games_played=1000, solo_rate=0.2),
        ),
        (
            "reliable_defender",
            "defender_win_rate",
            0.52,
            PlayerProfile(games_played=1000, defender_rate=0.8),
        ),
    ],
)
@pytest.mark.parametrize(
    ("offset", "matched"),
    [(-0.000001, False), (0, True), (0.000001, True)],
)
def test_signal_threshold_boundaries(
    code: str,
    field_name: str,
    threshold: float,
    base_profile: PlayerProfile,
    offset: float,
    matched: bool,
) -> None:
    profile = replace(base_profile, **{field_name: threshold + offset})
    signal = get_signal(profile, code)

    assert signal.value_threshold_matched is matched
    assert signal.reason_code == (
        "threshold_matched" if matched else "threshold_not_matched"
    )


@pytest.mark.parametrize(
    "code",
    ["frequent_declarer", "grand_oriented", "hand_oriented", "reliable_defender"],
)
def test_signal_missing_source_value(code: str) -> None:
    signal = get_signal(PlayerProfile(games_played=1000), code)

    assert signal.observed_value is None
    assert signal.value_threshold_matched is False
    assert signal.actionable is False
    assert signal.reason_code == "value_unavailable"


@pytest.mark.parametrize(
    ("code", "profile_factory"),
    [
        (
            "frequent_declarer",
            lambda count: PlayerProfile(games_played=count, solo_rate=0.35),
        ),
        (
            "grand_oriented",
            lambda count: PlayerProfile(
                games_played=1000,
                solo_games_played=count,
                grand_rate=0.25,
            ),
        ),
        (
            "hand_oriented",
            lambda count: PlayerProfile(
                games_played=1000,
                solo_games_played=count,
                hand_game_rate=0.10,
            ),
        ),
        (
            "reliable_defender",
            lambda count: PlayerProfile(
                games_played=1000,
                defender_games_played=count,
                defender_win_rate=0.52,
            ),
        ),
    ],
)
@pytest.mark.parametrize(
    ("evidence_count", "expected_level", "actionable"),
    [(99, "low", False), (100, "medium", True), (500, "high", True)],
)
def test_matched_signal_uses_scoped_confidence(
    code: str,
    profile_factory,
    evidence_count: int,
    expected_level: str,
    actionable: bool,
) -> None:
    signal = get_signal(profile_factory(evidence_count), code)

    assert signal.confidence_level == expected_level
    assert signal.actionable is actionable
    assert signal.reason_code == (
        "threshold_matched" if actionable else "insufficient_confidence"
    )


@pytest.mark.parametrize(
    ("profile", "decisive_code"),
    [
        (PlayerProfile(games_played=500, solo_rate=0.35), "frequent_declarer"),
        (
            PlayerProfile(games_played=500, solo_rate=0.2, grand_rate=0.25),
            "grand_oriented",
        ),
        (
            PlayerProfile(games_played=500, solo_rate=0.2, hand_game_rate=0.10),
            "hand_oriented",
        ),
    ],
)
def test_actionable_declarer_signals_classify_aggressive(
    profile: PlayerProfile,
    decisive_code: str,
) -> None:
    derivation = derive_opponent_profile(profile)

    assert derivation.classification == "aggressive"
    assert derivation.actionable_policy_preset == "aggressive_points"
    assert decisive_code in derivation.decisive_signal_codes


def test_actionable_reliable_defender_classifies_cautious() -> None:
    derivation = derive_opponent_profile(
        PlayerProfile(
            games_played=500,
            solo_rate=0.2,
            grand_rate=0.2,
            hand_game_rate=0.05,
            defender_win_rate=0.52,
        )
    )

    assert derivation.classification == "cautious_defender"
    assert derivation.actionable_policy_preset == "cautious_defender"


def test_actionable_aggressive_signal_takes_precedence_over_defender() -> None:
    derivation = derive_opponent_profile(
        PlayerProfile(
            games_played=1000,
            solo_rate=0.4,
            defender_rate=0.6,
            defender_win_rate=0.6,
        )
    )

    assert derivation.classification == "aggressive"
    assert derivation.decisive_signal_codes == ("frequent_declarer",)
    assert any("takes precedence" in line for line in derivation.explanations)


@pytest.mark.parametrize(
    ("profile", "classification", "preset"),
    [
        (
            PlayerProfile(games_played=99, solo_rate=0.4),
            "aggressive",
            "aggressive_points",
        ),
        (
            PlayerProfile(
                games_played=100,
                defender_rate=0.99,
                defender_win_rate=0.6,
            ),
            "cautious_defender",
            "cautious_defender",
        ),
    ],
)
def test_low_confidence_candidate_is_explanatory_not_actionable(
    profile: PlayerProfile,
    classification: str,
    preset: str,
) -> None:
    derivation = derive_opponent_profile(profile)

    assert derivation.classification == classification
    assert derivation.recommended_policy_preset == preset
    assert derivation.actionable_policy_preset is None
    assert derivation.derivation_status == "insufficient_confidence"


def test_sufficiently_evidenced_neutral_profile_uses_non_actionable_fallback() -> None:
    derivation = derive_opponent_profile(
        PlayerProfile(
            games_played=500,
            solo_rate=0.2,
            defender_rate=0.8,
            grand_rate=0.2,
            hand_game_rate=0.05,
            defender_win_rate=0.5,
        )
    )

    assert derivation.classification == "neutral"
    assert derivation.recommended_policy_preset == "simple_lowest"
    assert derivation.actionable_policy_preset is None
    assert derivation.derivation_status == "neutral"


def test_empty_profile_has_insufficient_data() -> None:
    derivation = derive_opponent_profile(PlayerProfile())

    assert derivation.profile_derivation_version == PROFILE_DERIVATION_VERSION
    assert derivation.classification == "neutral"
    assert derivation.recommended_policy_preset == "simple_lowest"
    assert derivation.actionable_policy_preset is None
    assert derivation.derivation_status == "insufficient_data"
    assert len(derivation.signals) == 4
    assert derivation.explanations


def test_derivation_does_not_mutate_profile() -> None:
    profile = PlayerProfile(games_played=500, solo_rate=0.35)

    derive_opponent_profile(profile)

    assert profile == PlayerProfile(games_played=500, solo_rate=0.35)
