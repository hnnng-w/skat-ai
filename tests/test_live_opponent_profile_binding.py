import copy
import json
from pathlib import Path

import pytest

from skat_ai.live_opponent_profile_binding import (
    resolve_live_opponent_profile_bindings,
)
from skat_ai.opponent_statistics import (
    build_opponent_statistics_input,
    build_opponent_statistics_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_example_statistics_data() -> dict[str, object]:
    with (PROJECT_ROOT / "examples" / "opponent_statistics.json").open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)["opponent_statistics_input"]


def build_example_summary() -> dict[str, object]:
    return build_opponent_statistics_summary(
        build_opponent_statistics_input(load_example_statistics_data())
    )


def test_resolves_left_right_or_both_by_exact_stable_id() -> None:
    summary = build_example_summary()

    left_only = resolve_live_opponent_profile_bindings(
        summary, left_player_id="opponent-123"
    )
    right_only = resolve_live_opponent_profile_bindings(
        summary, right_player_id="opponent-789"
    )
    both = resolve_live_opponent_profile_bindings(
        summary,
        left_player_id="opponent-123",
        right_player_id="opponent-789",
    )

    assert left_only.left is not None
    assert left_only.right is None
    assert right_only.left is None
    assert right_only.right is not None
    assert both.left == left_only.left
    assert both.right == right_only.right


def test_resolution_is_stable_and_preserves_profile_derivation_and_provenance() -> None:
    summary = build_example_summary()

    first = resolve_live_opponent_profile_bindings(
        summary,
        left_player_id="opponent-123",
        right_player_id="opponent-789",
    )
    second = resolve_live_opponent_profile_bindings(
        copy.deepcopy(summary),
        left_player_id="opponent-123",
        right_player_id="opponent-789",
    )

    assert first == second
    assert first.left is not None
    assert first.left.profile.defender_rate == 0.69
    assert first.left.source == {
        "source_type": "online_platform",
        "source_name": "Example platform",
        "source_player_id": "platform-user-456",
        "captured_at": "2026-07-23T12:00:00+02:00",
    }
    assert first.left.derivation["classification"] == "cautious_defender"
    assert first.left.derivation["actionable_policy_preset"] == "cautious_defender"


def test_additional_unbound_records_are_ignored() -> None:
    data = load_example_statistics_data()
    extra = copy.deepcopy(data["records"][0])
    extra["player_id"] = "unbound-player"
    data["records"].append(extra)
    summary = build_opponent_statistics_summary(build_opponent_statistics_input(data))

    bindings = resolve_live_opponent_profile_bindings(
        summary, right_player_id="opponent-789"
    )

    assert bindings.left is None
    assert bindings.right is not None
    assert bindings.right.player_id == "opponent-789"


@pytest.mark.parametrize(
    ("left_player_id", "right_player_id", "error_match"),
    [
        ("Opponent-123", None, "match exactly one"),
        ("unknown", None, "unknown.*match exactly one"),
        ("", None, "non-empty, non-padded"),
        (" opponent-123", None, "non-empty, non-padded"),
        ("opponent-123", "opponent-123", "must be different"),
    ],
)
def test_rejects_inexact_blank_padded_unknown_and_duplicate_bindings(
    left_player_id: str | None,
    right_player_id: str | None,
    error_match: str,
) -> None:
    with pytest.raises(ValueError, match=error_match):
        resolve_live_opponent_profile_bindings(
            build_example_summary(),
            left_player_id=left_player_id,
            right_player_id=right_player_id,
        )
