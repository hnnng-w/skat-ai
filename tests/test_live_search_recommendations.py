import copy
import json
import subprocess
import sys
from pathlib import Path

import main as main_module
from main import build_analysis_result

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXHAUSTIVE_EXAMPLE = PROJECT_ROOT / "examples" / "grand_bounded_search_exhaustive.json"
FALLBACK_EXAMPLE = PROJECT_ROOT / "examples" / "grand_auto_search_fallback.json"


def _write_input(tmp_path: Path, data: dict, name: str = "position.json") -> str:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _without_elapsed(result: dict) -> dict:
    normalized = copy.deepcopy(result)
    normalized["bounded_search_result"]["consumed_budget"]["wall_clock_elapsed_ms"] = 0
    return normalized


def test_omitted_method_preserves_existing_output_and_explicit_immediate_adds_only_contract(
    tmp_path: Path,
) -> None:
    source_path = PROJECT_ROOT / "examples" / "grand_second_position.json"
    source = _load(source_path)
    default_result = build_analysis_result(str(source_path), sample_count_override=20)
    explicit_path = _write_input(
        tmp_path,
        {**source, "recommendation_method": "immediate_expected_value"},
    )
    explicit_result = build_analysis_result(explicit_path, sample_count_override=20)

    assert "recommendation_method_summary" not in default_result
    assert "bounded_search_result" not in default_result
    assert "recommendation_method" not in default_result["settings"]
    summary = explicit_result.pop("recommendation_method_summary")
    assert explicit_result.pop("bounded_search_result") is None
    explicit_result["settings"].pop("recommendation_method")
    assert explicit_result["settings"].pop("bounded_search_settings") is None
    explicit_result["input_file"] = default_result["input_file"]
    assert explicit_result == default_result
    assert summary == {
        "requested_method": "immediate_expected_value",
        "effective_method": "immediate_expected_value",
        "search_attempted": False,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "immediate_expected_value",
    }


def test_omitted_method_preserves_main_immediate_patch_points(
    monkeypatch,
) -> None:
    values = {
        "SA": {
            "win_rate": 1.0,
            "average_trick_points": 0.0,
            "average_points_won": 0.0,
            "average_points_lost": 0.0,
        }
    }
    report = [
        {
            "card": "SA",
            "win_rate": 1.0,
            "average_trick_points": 0.0,
            "average_points_won": 0.0,
            "average_points_lost": 0.0,
            "expected_point_swing": 0.0,
            "is_recommended": True,
        }
    ]
    monkeypatch.setattr(
        main_module,
        "recommend_card_by_expected_value",
        lambda **_kwargs: ("SA", "Patched recommendation.", values),
    )
    monkeypatch.setattr(
        main_module,
        "build_card_analysis_report",
        lambda **_kwargs: report,
    )

    result = main_module.build_analysis_result(
        str(PROJECT_ROOT / "examples" / "grand_second_position.json")
    )

    assert result["recommendation"] == {
        "card": "SA",
        "reason": "Patched recommendation.",
    }
    assert result["analysis_report"] == report


def test_omitted_unavailable_method_preserves_main_summary_patch_point(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data = _load(PROJECT_ROOT / "examples" / "grand_second_position.json")
    data.update(trick_leader="left", current_trick=[], next_player="left")
    monkeypatch.setattr(
        main_module,
        "build_unavailable_strategic_summary",
        lambda reason: f"Patched unavailable summary: {reason}",
    )

    result = main_module.build_analysis_result(_write_input(tmp_path, data))

    assert result["strategic_summary"].startswith("Patched unavailable summary:")


def test_complete_search_output_uses_search_card_and_no_immediate_report() -> None:
    result = build_analysis_result(str(EXHAUSTIVE_EXAMPLE))
    search = result["bounded_search_result"]

    assert result["recommendation_method_summary"] == {
        "requested_method": "bounded_search",
        "effective_method": "compatible_world_minimax_v1",
        "search_attempted": True,
        "fallback_used": False,
        "fallback_method": None,
        "analysis_report_method": "none",
    }
    assert search["status"] == "complete"
    assert search["world_coverage"] == "all_compatible_worlds"
    assert search["compatible_world_count"] == 1
    assert result["recommendation"]["card"] == search["recommended_card"] == "D7"
    assert result["analysis_report"] == []
    assert "status complete" in result["recommendation"]["reason"]
    assert "coverage all compatible worlds" in result["strategic_summary"]


def test_auto_fallback_output_preserves_search_and_immediate_reports() -> None:
    result = build_analysis_result(str(FALLBACK_EXAMPLE))
    search = result["bounded_search_result"]

    assert result["recommendation_method_summary"] == {
        "requested_method": "auto",
        "effective_method": "immediate_expected_value",
        "search_attempted": True,
        "fallback_used": True,
        "fallback_method": "immediate_expected_value",
        "analysis_report_method": "immediate_expected_value",
    }
    assert search["status"] == "partial"
    assert search["stop_reason"] == "node_budget_exhausted"
    assert search["recommended_card"] is None
    assert search["fallback_used"] is True
    assert result["recommendation"]["card"] == "D7"
    assert result["analysis_report"][0]["card"] == "D7"
    assert result["analysis_report"][0]["is_recommended"] is True
    assert "Auto fallback" in result["recommendation"]["reason"]


def test_strict_unavailable_search_has_no_effective_card_or_report(
    tmp_path: Path,
) -> None:
    data = _load(
        PROJECT_ROOT / "examples" / "defender_open_play_continuation.json"
    )
    data.update(
        recommendation_method="bounded_search",
        matadors=1,
        bid_value=24,
        bounded_search_settings={
            "random_seed": 113,
            "max_remaining_tricks": 1,
            "max_depth_plies": 3,
            "max_nodes": 100,
            "max_selected_worlds": 2,
            "max_sampled_worlds": 2,
            "minimum_comparable_worlds": 1,
            "wall_clock_timeout_ms": None,
        },
    )

    result = build_analysis_result(_write_input(tmp_path, data))

    assert result["bounded_search_result"]["status"] == "unavailable"
    assert result["bounded_search_result"]["stop_reason"] == (
        "remaining_trick_limit_exceeded"
    )
    assert result["recommendation_method_summary"]["effective_method"] == "none"
    assert result["recommendation"]["card"] is None
    assert result["analysis_report"] == []
    assert result["recommendation_method_summary"]["fallback_used"] is False


def test_search_output_contains_no_private_world_or_derived_seed_fields() -> None:
    result = build_analysis_result(str(EXHAUSTIVE_EXAMPLE))
    serialized = json.dumps(result["bounded_search_result"], sort_keys=True)

    for forbidden in (
        "left_hand",
        "right_hand",
        "hypothetical_skat",
        "exact_state",
        "world_assignment",
        "principal_variation",
        "child_seed",
    ):
        assert forbidden not in serialized
    assert set(result["settings"]["bounded_search_settings"]) == {
        "random_seed",
        "max_remaining_tricks",
        "max_depth_plies",
        "max_nodes",
        "max_selected_worlds",
        "max_sampled_worlds",
        "minimum_comparable_worlds",
        "wall_clock_timeout_ms",
    }


def test_successful_search_is_independent_from_immediate_seed(
    tmp_path: Path,
) -> None:
    data = _load(EXHAUSTIVE_EXAMPLE)
    first_path = _write_input(tmp_path, {**data, "random_seed": 1}, "first.json")
    second_path = _write_input(tmp_path, {**data, "random_seed": 999}, "second.json")

    first = build_analysis_result(first_path)
    second = build_analysis_result(second_path)

    assert _without_elapsed(first)["bounded_search_result"] == _without_elapsed(second)[
        "bounded_search_result"
    ]
    assert first["recommendation"] == second["recommendation"]


def test_exact_enumeration_is_independent_from_search_seed(
    tmp_path: Path,
) -> None:
    data = _load(EXHAUSTIVE_EXAMPLE)
    first_settings = {**data["bounded_search_settings"], "random_seed": 1}
    second_settings = {**data["bounded_search_settings"], "random_seed": 999}
    first_path = _write_input(
        tmp_path,
        {**data, "bounded_search_settings": first_settings},
        "first-search.json",
    )
    second_path = _write_input(
        tmp_path,
        {**data, "bounded_search_settings": second_settings},
        "second-search.json",
    )

    first = build_analysis_result(first_path)
    second = build_analysis_result(second_path)

    assert _without_elapsed(first)["bounded_search_result"] == _without_elapsed(second)[
        "bounded_search_result"
    ]


def test_search_ignores_defender_private_skat_identities(tmp_path: Path) -> None:
    data = _load(PROJECT_ROOT / "examples" / "declarer_card_exposure_continuation.json")
    data["hand"] = ["C9", "C7", "H8", "D9"]
    data["current_trick"] = []
    data["completed_tricks"].extend(
        [
            {
                "cards": ["C8", "CK", "C10"],
                "players": ["right", "me", "left"],
                "winner_role": "declarer",
                "winner_player": "left",
            },
            {
                "cards": ["S7", "H9", "S9"],
                "players": ["left", "right", "me"],
                "winner_role": "defenders",
                "winner_player": "me",
            },
        ]
    )
    data["trick_leader"] = "me"
    data["next_player"] = "me"
    data["left_hand_size"] = 4
    data["right_hand_size"] = 4
    data["game_continuation"]["public_declarer_cards"] = ["DK", "HK", "SJ", "SK"]
    data.update(
        skat_visibility="known_to_declarer",
        recommendation_method="bounded_search",
        bounded_search_settings={
            "random_seed": 113,
            "max_remaining_tricks": 4,
            "max_depth_plies": 1,
            "max_nodes": 1,
            "max_selected_worlds": 2,
            "max_sampled_worlds": 2,
            "minimum_comparable_worlds": 1,
            "wall_clock_timeout_ms": None,
        },
    )
    first_path = _write_input(tmp_path, {**data, "skat": ["CA", "CQ"]}, "first.json")
    second_path = _write_input(tmp_path, {**data, "skat": ["SQ", "HQ"]}, "second.json")

    first = build_analysis_result(first_path)
    second = build_analysis_result(second_path)

    assert first["position"]["skat"] == second["position"]["skat"] == []
    assert first["bounded_search_result"]["world_coverage"] == "sampled_compatible_worlds"
    assert _without_elapsed(first)["bounded_search_result"] == _without_elapsed(second)[
        "bounded_search_result"
    ]
    assert first["recommendation"] == second["recommendation"]


def test_search_executes_with_authorized_continuation_public_hand(
    tmp_path: Path,
) -> None:
    data = _load(PROJECT_ROOT / "examples" / "defender_open_play_continuation.json")
    data.update(
        recommendation_method="bounded_search",
        bounded_search_settings={
            "random_seed": 113,
            "max_remaining_tricks": 3,
            "max_depth_plies": 1,
            "max_nodes": 1,
            "max_selected_worlds": 1,
            "max_sampled_worlds": 1,
            "minimum_comparable_worlds": 1,
            "wall_clock_timeout_ms": None,
        },
    )

    result = build_analysis_result(_write_input(tmp_path, data))

    assert result["recommendation_method_summary"]["search_attempted"] is True
    constraint = result["information_policy_summary"]["public_hand_constraints"][0]
    assert constraint["player"] == "left"
    assert set(constraint["cards"]) == {"C7", "D9", "H8"}
    assert constraint["source"] == "defender_open_play_continuation"


def test_explicit_search_cli_and_quiet_mode() -> None:
    command = [sys.executable, str(PROJECT_ROOT / "main.py"), "--input", str(EXHAUSTIVE_EXAMPLE)]
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    quiet = subprocess.run(
        [*command, "--quiet"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    fallback = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(FALLBACK_EXAMPLE),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Requested recommendation method: bounded_search" in completed.stdout
    assert "Effective recommendation method: compatible_world_minimax_v1" in completed.stdout
    assert "Search status: complete" in completed.stdout
    assert "Search stop reason: completed" in completed.stdout
    assert "Search random seed: 113" in completed.stdout
    assert "Search completed worlds: 1 of 1" in completed.stdout
    assert quiet.returncode == 0
    assert quiet.stdout == ""
    assert quiet.stderr == ""
    assert fallback.returncode == 0
    assert "Fallback method: immediate_expected_value" in fallback.stdout


def test_default_cli_text_remains_without_method_lines() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(PROJECT_ROOT / "examples" / "grand_second_position.json"),
            "--samples",
            "5",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Requested recommendation method:" not in completed.stdout
    assert "Search status:" not in completed.stdout


def test_search_supports_multi_step_with_expected_cli_output() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(EXHAUSTIVE_EXAMPLE),
            "--multi-step",
            "1",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "Card selection policy: bounded_search" in completed.stdout
    assert "Requested recommendation method: bounded_search" in completed.stdout
    assert "Search chosen card: D7" in completed.stdout
    assert completed.stderr == ""


def test_auto_multi_step_cli_labels_fallback_card_and_comparison_counts() -> None:
    fallback = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(FALLBACK_EXAMPLE),
            "--multi-step",
            "1",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    comparison = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(EXHAUSTIVE_EXAMPLE),
            "--multi-step",
            "1",
            "--compare-policies",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert fallback.returncode == 0
    assert "Fallback method: immediate_expected_value" in fallback.stdout
    assert "Fallback chosen card: D7" in fallback.stdout
    assert "Search chosen card: D7" not in fallback.stdout
    assert comparison.returncode == 0
    assert (
        "Search decisions: 1 attempted, 1 executed, 1 Search, 0 fallback, "
        "0 no recommendation"
    ) in comparison.stdout


def test_search_multi_step_rejects_conflicting_explicit_card_policy() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(EXHAUSTIVE_EXAMPLE),
            "--multi-step",
            "1",
            "--card-policy",
            "first_legal",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "conflicts with the configured Search" in completed.stderr


def test_search_card_policy_requires_matching_json_configuration() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "main.py"),
            "--input",
            str(PROJECT_ROOT / "examples" / "grand_second_position.json"),
            "--multi-step",
            "1",
            "--card-policy",
            "bounded_search",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "requires matching recommendation_method" in completed.stderr
