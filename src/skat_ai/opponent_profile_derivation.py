import math
from dataclasses import dataclass
from typing import Literal

from skat_ai.player_profile import PlayerProfile

PROFILE_DERIVATION_VERSION = 1
ROLE_RATE_ROUNDING_TOLERANCE = 0.02

ConfidenceLevel = Literal["unknown", "low", "medium", "high"]
EvidenceKind = Literal[
    "exact",
    "estimated_from_rate",
    "estimated_from_complement",
    "unavailable",
]
ConfidenceScope = Literal["overall", "declarer", "defender"]
SignalReasonCode = Literal[
    "threshold_matched",
    "threshold_not_matched",
    "value_unavailable",
    "insufficient_confidence",
]
ProfileClassification = Literal["aggressive", "cautious_defender", "neutral"]
PolicyPreset = Literal["aggressive_points", "cautious_defender", "simple_lowest"]
DerivationStatus = Literal[
    "actionable",
    "insufficient_confidence",
    "neutral",
    "insufficient_data",
]


@dataclass(frozen=True)
class ProfileConfidence:
    """One heuristic confidence band and its evidence provenance."""

    level: ConfidenceLevel
    evidence_count: float | None
    evidence_kind: EvidenceKind


@dataclass(frozen=True)
class OpponentProfileSignal:
    """One threshold signal evaluated with denominator-scoped confidence."""

    code: str
    source_field: str
    observed_value: float | None
    comparison_operator: Literal[">="]
    threshold: float
    confidence_scope: ConfidenceScope
    confidence_level: ConfidenceLevel
    value_threshold_matched: bool
    actionable: bool
    reason_code: SignalReasonCode


@dataclass(frozen=True)
class OpponentProfileDerivation:
    """Versioned, deterministic, explainable opponent-profile derivation."""

    profile_derivation_version: int
    confidence: dict[ConfidenceScope, ProfileConfidence]
    signals: tuple[OpponentProfileSignal, ...]
    classification: ProfileClassification
    recommended_policy_preset: PolicyPreset
    actionable_policy_preset: PolicyPreset | None
    derivation_status: DerivationStatus
    decisive_signal_codes: tuple[str, ...]
    explanations: tuple[str, ...]


@dataclass(frozen=True)
class _SignalDefinition:
    code: str
    source_field: str
    display_name: str
    threshold: float
    confidence_scope: ConfidenceScope
    classification: ProfileClassification


_SIGNAL_DEFINITIONS = (
    _SignalDefinition(
        "frequent_declarer",
        "solo_rate",
        "solo rate",
        0.35,
        "overall",
        "aggressive",
    ),
    _SignalDefinition(
        "grand_oriented",
        "grand_rate",
        "grand rate",
        0.25,
        "declarer",
        "aggressive",
    ),
    _SignalDefinition(
        "hand_oriented",
        "hand_game_rate",
        "Hand-game rate",
        0.10,
        "declarer",
        "aggressive",
    ),
    _SignalDefinition(
        "reliable_defender",
        "defender_win_rate",
        "defender win rate",
        0.52,
        "defender",
        "cautious_defender",
    ),
)

_CLASSIFICATION_PRESETS: dict[ProfileClassification, PolicyPreset] = {
    "aggressive": "aggressive_points",
    "cautious_defender": "cautious_defender",
    "neutral": "simple_lowest",
}


def _validate_optional_count(value: int | None, field_name: str) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value < 0
    ):
        raise ValueError(f"{field_name} must be a non-negative integer or None.")


def _validate_optional_rate(value: float | None, field_name: str) -> None:
    if value is not None and (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or value > 1
    ):
        raise ValueError(f"{field_name} must be a finite number from 0 through 1 or None.")


def _validate_exact_count_rate(
    count: int | None,
    rate: float | None,
    games_played: int | None,
    count_field: str,
    rate_field: str,
) -> None:
    if count is None or rate is None or games_played is None:
        return
    expected_rate = count / games_played if games_played else 0.0
    difference = abs(expected_rate - rate)
    if difference > ROLE_RATE_ROUNDING_TOLERANCE and not math.isclose(
        difference,
        ROLE_RATE_ROUNDING_TOLERANCE,
        abs_tol=1e-12,
    ):
        raise ValueError(
            f"{count_field} contradicts {rate_field} beyond the "
            f"{ROLE_RATE_ROUNDING_TOLERANCE:g} rounding tolerance."
        )


def validate_player_profile_evidence(profile: PlayerProfile) -> None:
    """Validates evidence fields used by the version-1 derivation contract."""
    count_fields = ("games_played", "solo_games_played", "defender_games_played")
    rate_fields = (
        "solo_rate",
        "defender_rate",
        "solo_win_rate",
        "hand_game_rate",
        "suit_game_rate",
        "grand_rate",
        "null_game_rate",
        "defender_win_rate",
    )
    for field_name in count_fields:
        _validate_optional_count(getattr(profile, field_name), field_name)
    for field_name in rate_fields:
        _validate_optional_rate(getattr(profile, field_name), field_name)

    total = profile.games_played
    if total is not None:
        for field_name in ("solo_games_played", "defender_games_played"):
            count = getattr(profile, field_name)
            if count is not None and count > total:
                raise ValueError(f"{field_name} must not exceed games_played.")
        if (
            profile.solo_games_played is not None
            and profile.defender_games_played is not None
            and profile.solo_games_played + profile.defender_games_played != total
        ):
            raise ValueError(
                "solo_games_played and defender_games_played must sum to games_played."
            )

    _validate_exact_count_rate(
        profile.solo_games_played,
        profile.solo_rate,
        total,
        "solo_games_played",
        "solo_rate",
    )
    _validate_exact_count_rate(
        profile.defender_games_played,
        profile.defender_rate,
        total,
        "defender_games_played",
        "defender_rate",
    )
    _validate_exact_count_rate(
        profile.solo_games_played,
        1 - profile.defender_rate if profile.defender_rate is not None else None,
        total,
        "solo_games_played",
        "1 - defender_rate",
    )
    _validate_exact_count_rate(
        profile.defender_games_played,
        1 - profile.solo_rate if profile.solo_rate is not None else None,
        total,
        "defender_games_played",
        "1 - solo_rate",
    )
    if profile.solo_rate is not None and profile.defender_rate is not None:
        difference = abs(profile.solo_rate + profile.defender_rate - 1.0)
        if difference > ROLE_RATE_ROUNDING_TOLERANCE and not math.isclose(
            difference,
            ROLE_RATE_ROUNDING_TOLERANCE,
            abs_tol=1e-12,
        ):
            raise ValueError(
                "solo_rate and defender_rate contradict the role total beyond the "
                f"{ROLE_RATE_ROUNDING_TOLERANCE:g} rounding tolerance."
            )


def get_evidence_confidence(
    evidence_count: float | None,
    evidence_kind: EvidenceKind,
) -> ProfileConfidence:
    """Maps one evidence count to the fixed heuristic confidence bands."""
    if evidence_count is None:
        return ProfileConfidence("unknown", None, "unavailable")
    if evidence_count < 100:
        level: ConfidenceLevel = "low"
    elif evidence_count < 500:
        level = "medium"
    else:
        level = "high"
    return ProfileConfidence(level, float(evidence_count), evidence_kind)


def _derive_confidence(
    profile: PlayerProfile,
) -> dict[ConfidenceScope, ProfileConfidence]:
    total = profile.games_played
    overall = get_evidence_confidence(
        float(total) if total is not None else None,
        "exact" if total is not None else "unavailable",
    )

    if profile.solo_games_played is not None:
        declarer_count = float(profile.solo_games_played)
        declarer_kind: EvidenceKind = "exact"
    elif total is not None and profile.solo_rate is not None:
        declarer_count = total * profile.solo_rate
        declarer_kind = "estimated_from_rate"
    else:
        declarer_count = None
        declarer_kind = "unavailable"

    if profile.defender_games_played is not None:
        defender_count = float(profile.defender_games_played)
        defender_kind: EvidenceKind = "exact"
    elif total is not None and profile.defender_rate is not None:
        defender_count = total * profile.defender_rate
        defender_kind = "estimated_from_rate"
    elif total is not None and profile.solo_rate is not None:
        defender_count = total * (1 - profile.solo_rate)
        defender_kind = "estimated_from_complement"
    else:
        defender_count = None
        defender_kind = "unavailable"

    return {
        "overall": overall,
        "declarer": get_evidence_confidence(declarer_count, declarer_kind),
        "defender": get_evidence_confidence(defender_count, defender_kind),
    }


def _evaluate_signal(
    profile: PlayerProfile,
    definition: _SignalDefinition,
    confidence: dict[ConfidenceScope, ProfileConfidence],
) -> OpponentProfileSignal:
    value = getattr(profile, definition.source_field)
    scoped_confidence = confidence[definition.confidence_scope]
    if value is None:
        matched = False
        actionable = False
        reason_code: SignalReasonCode = "value_unavailable"
    else:
        matched = value >= definition.threshold
        actionable = matched and scoped_confidence.level in ("medium", "high")
        if not matched:
            reason_code = "threshold_not_matched"
        elif actionable:
            reason_code = "threshold_matched"
        else:
            reason_code = "insufficient_confidence"
    return OpponentProfileSignal(
        code=definition.code,
        source_field=definition.source_field,
        observed_value=float(value) if value is not None else None,
        comparison_operator=">=",
        threshold=definition.threshold,
        confidence_scope=definition.confidence_scope,
        confidence_level=scoped_confidence.level,
        value_threshold_matched=matched,
        actionable=actionable,
        reason_code=reason_code,
    )


def _build_explanations(
    confidence: dict[ConfidenceScope, ProfileConfidence],
    signals: tuple[OpponentProfileSignal, ...],
    classification: ProfileClassification,
    preset: PolicyPreset,
    status: DerivationStatus,
) -> tuple[str, ...]:
    explanations: list[str] = []
    for scope in ("overall", "declarer", "defender"):
        result = confidence[scope]
        if result.evidence_count is None:
            explanations.append(f"{scope.title()} evidence is unavailable.")
        else:
            kind = result.evidence_kind.replace("_", " ")
            explanations.append(
                f"{scope.title()} evidence is {result.level} based on {kind} "
                f"evidence of {result.evidence_count} games."
            )

    definitions = {definition.code: definition for definition in _SIGNAL_DEFINITIONS}
    for signal in signals:
        definition = definitions[signal.code]
        if signal.observed_value is None:
            explanations.append(
                f"The {definition.display_name} is unavailable, so "
                f"{signal.code} cannot be evaluated."
            )
        elif signal.value_threshold_matched:
            explanations.append(
                f"The {definition.display_name} of {signal.observed_value:g} meets the "
                f"{signal.threshold:g} threshold."
            )
        else:
            explanations.append(
                f"The {definition.display_name} of {signal.observed_value:g} is below the "
                f"{signal.threshold:g} threshold."
            )

    actionable_aggressive = any(
        signal.actionable and signal.code != "reliable_defender" for signal in signals
    )
    actionable_defender = any(
        signal.actionable and signal.code == "reliable_defender" for signal in signals
    )
    if actionable_aggressive and actionable_defender:
        explanations.append(
            "The aggressive classification takes precedence over actionable defender evidence."
        )
    explanations.append(f"The derived classification is {classification}.")
    if status == "actionable":
        explanations.append(f"The {preset} preset is actionable.")
    elif status == "insufficient_confidence":
        explanations.append(
            f"The {preset} preset is recommended for explanation but is not actionable."
        )
    elif status == "neutral":
        explanations.append(
            "The simple_lowest preset is a neutral fallback and is not actionable."
        )
    else:
        explanations.append(
            "The simple_lowest preset is a fallback for insufficient data and is not actionable."
        )
    return tuple(explanations)


def derive_opponent_profile(profile: PlayerProfile) -> OpponentProfileDerivation:
    """Derives a versioned profile result without mutating or applying the profile."""
    validate_player_profile_evidence(profile)
    confidence = _derive_confidence(profile)
    signals = tuple(
        _evaluate_signal(profile, definition, confidence)
        for definition in _SIGNAL_DEFINITIONS
    )
    actionable_aggressive = tuple(
        signal.code
        for signal in signals
        if signal.actionable and signal.code != "reliable_defender"
    )
    actionable_defender = tuple(
        signal.code
        for signal in signals
        if signal.actionable and signal.code == "reliable_defender"
    )
    matched_aggressive = tuple(
        signal.code
        for signal in signals
        if signal.value_threshold_matched and signal.code != "reliable_defender"
    )
    matched_defender = tuple(
        signal.code
        for signal in signals
        if signal.value_threshold_matched and signal.code == "reliable_defender"
    )

    if actionable_aggressive:
        classification: ProfileClassification = "aggressive"
        decisive_codes = actionable_aggressive
        status: DerivationStatus = "actionable"
    elif actionable_defender:
        classification = "cautious_defender"
        decisive_codes = actionable_defender
        status = "actionable"
    elif matched_aggressive:
        classification = "aggressive"
        decisive_codes = matched_aggressive
        status = "insufficient_confidence"
    elif matched_defender:
        classification = "cautious_defender"
        decisive_codes = matched_defender
        status = "insufficient_confidence"
    else:
        classification = "neutral"
        decisive_codes = ()
        evaluable = any(
            signal.observed_value is not None and signal.confidence_level != "unknown"
            for signal in signals
        )
        status = "neutral" if evaluable else "insufficient_data"

    recommended_preset = _CLASSIFICATION_PRESETS[classification]
    actionable_preset = recommended_preset if status == "actionable" else None
    return OpponentProfileDerivation(
        profile_derivation_version=PROFILE_DERIVATION_VERSION,
        confidence=confidence,
        signals=signals,
        classification=classification,
        recommended_policy_preset=recommended_preset,
        actionable_policy_preset=actionable_preset,
        derivation_status=status,
        decisive_signal_codes=decisive_codes,
        explanations=_build_explanations(
            confidence,
            signals,
            classification,
            recommended_preset,
            status,
        ),
    )
