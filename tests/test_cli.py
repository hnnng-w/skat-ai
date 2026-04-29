from main import apply_cli_overrides, build_analysis_result


def test_apply_cli_overrides_keeps_settings_when_no_overrides_are_given() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy=None,
    )

    assert updated_settings == settings


def test_apply_cli_overrides_updates_sample_count() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=None,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 42


def test_apply_cli_overrides_updates_random_seed() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=123,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 1000
    assert updated_settings["random_seed"] == 123


def test_apply_cli_overrides_updates_sample_count_and_random_seed() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy=None,
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123


def test_apply_cli_overrides_does_not_mutate_original_settings() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy=None,
    )

    assert settings["sample_count"] == 1000
    assert settings["random_seed"] == 42
    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123

def test_apply_cli_overrides_sets_basic_opponent_strategy() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": False,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy="basic",
    )

    assert updated_settings["use_basic_opponent_strategy"] is True


def test_apply_cli_overrides_sets_random_opponent_strategy() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=None,
        random_seed=None,
        opponent_strategy="random",
    )

    assert updated_settings["use_basic_opponent_strategy"] is False


def test_apply_cli_overrides_updates_all_cli_options() -> None:
    settings = {
        "left_hand_size": 5,
        "right_hand_size": 5,
        "sample_count": 1000,
        "random_seed": 42,
        "use_basic_opponent_strategy": True,
    }

    updated_settings = apply_cli_overrides(
        settings=settings,
        sample_count=500,
        random_seed=123,
        opponent_strategy="random",
    )

    assert updated_settings["sample_count"] == 500
    assert updated_settings["random_seed"] == 123
    assert updated_settings["use_basic_opponent_strategy"] is False

def test_build_analysis_result_returns_expected_top_level_keys() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert set(result.keys()) == {
        "input_file",
        "position",
        "settings",
        "legal_cards",
        "analysis_report",
        "strategic_summary",
        "score_summary",
        "recommendation",
    }


def test_build_analysis_result_contains_recommendation() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=42,
        opponent_strategy_override="basic",
    )

    assert "card" in result["recommendation"]
    assert "reason" in result["recommendation"]
    assert result["recommendation"]["card"] in result["legal_cards"]


def test_build_analysis_result_applies_cli_overrides() -> None:
    result = build_analysis_result(
        file_path="examples/grand_leading.json",
        sample_count_override=20,
        random_seed_override=123,
        opponent_strategy_override="random",
    )

    assert result["settings"]["sample_count"] == 20
    assert result["settings"]["random_seed"] == 123
    assert result["settings"]["use_basic_opponent_strategy"] is False