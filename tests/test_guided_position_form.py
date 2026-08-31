from dataclasses import FrozenInstanceError

import pytest

from skatmind.api.v1 import ExecutionOptionsV1, RequestDocumentV1, WorkflowV1
from skatmind.app_web.card_form import (
    CANONICAL_CARD_CONTROLS_V1,
    CardZoneSelectionV1,
    find_card_zone_conflicts_v1,
)
from skatmind.app_web.form_parsing import FormFieldErrorV1
from skatmind.app_web.position_form import (
    DEFAULT_POSITION_RANDOM_SEED_V1,
    DEFAULT_POSITION_SAMPLE_COUNT_V1,
    POSITION_ANALYSIS_METHODS_V1,
    PositionFormError,
    build_guided_position_execution_v1,
    parse_position_form_v1,
)
from skatmind.deck import get_full_deck
from skatmind.rules import get_card_name, get_legal_cards
from skatmind.search_budget_profiles import (
    INTERACTIVE_SEARCH_BUDGET_PROFILE,
    convert_requested_search_budget_to_information_set_search_budget_v1,
    get_search_budget_profile,
)


def _form(**updates: list[str]) -> dict[str, list[str]]:
    values = {
        "game_type": ["grand"],
        "player_role": ["declarer"],
        "player_position": ["forehand"],
        "trick_leader": ["me"],
        "hand": ["CJ", "CA", "C10", "CK", "CQ", "C9", "C8", "C7", "SA", "S10"],
    }
    values.update(updates)
    return values


def _build(**updates: list[str]) -> tuple[RequestDocumentV1, ExecutionOptionsV1]:
    return build_guided_position_execution_v1(parse_position_form_v1(_form(**updates)))


def _document(**updates: list[str]) -> dict[str, object]:
    request, _ = _build(**updates)
    return request.to_dict()["document"]


def test_card_controls_derive_exact_deck_order_and_readable_labels() -> None:
    assert tuple(control.code for control in CANONICAL_CARD_CONTROLS_V1) == tuple(get_full_deck())
    assert len(CANONICAL_CARD_CONTROLS_V1) == 32
    assert len({control.code for control in CANONICAL_CARD_CONTROLS_V1}) == 32
    for control in CANONICAL_CARD_CONTROLS_V1:
        assert control.name == get_card_name(control.code)
        assert control.label == f"{get_card_name(control.code)} ({control.code})"


def test_card_zone_conflicts_are_immutable_and_deck_ordered() -> None:
    conflicts = find_card_zone_conflicts_v1(
        (
            CardZoneSelectionV1("hand", ("S7", "CA", "CA")),
            CardZoneSelectionV1("skat", ("S7",)),
        )
    )
    assert [(item.card, item.fields) for item in conflicts] == [
        ("CA", ("hand",)),
        ("S7", ("hand", "skat")),
    ]
    with pytest.raises(FrozenInstanceError):
        conflicts[0].card = "C7"  # type: ignore[misc]


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand"])
def test_suit_and_grand_contracts_build(game_type: str) -> None:
    document = _document(game_type=[game_type], matadors=["1"], bid_value=["18"])
    assert document["game_type"] == game_type
    assert document["matadors"] == 1
    assert document["bid_value"] == 18


@pytest.mark.parametrize(
    ("hand_game", "ouvert"),
    [(False, False), (True, False), (False, True), (True, True)],
)
def test_all_four_null_variants_preserve_hand_and_ouvert(
    hand_game: bool,
    ouvert: bool,
) -> None:
    updates = {"game_type": ["null"]}
    if hand_game:
        updates["hand_game"] = ["on"]
    if ouvert:
        updates["ouvert"] = ["on"]
        updates["public_declarer_cards"] = _form()["hand"]
    document = _document(**updates)
    assert document["hand_game"] is hand_game
    assert document["ouvert"] is ouvert
    assert document["schneider_announced"] is False
    assert document["schwarz_announced"] is False
    assert "matadors" not in document


def test_suit_ouvert_uses_existing_declaration_dependencies() -> None:
    hand = _form()["hand"]
    document = _document(
        game_type=["clubs"],
        ouvert=["on"],
        public_declarer_cards=hand,
    )
    assert document["hand_game"] is True
    assert document["schneider_announced"] is True
    assert document["schwarz_announced"] is True
    assert document["ouvert"] is True


@pytest.mark.parametrize("seat", ["forehand", "middlehand", "rearhand"])
def test_all_local_seats_are_preserved(seat: str) -> None:
    assert _document(player_position=[seat])["player_position"] == seat


@pytest.mark.parametrize("declarer_player", ["left", "right"])
def test_defender_perspective_requires_and_preserves_relative_declarer(
    declarer_player: str,
) -> None:
    document = _document(
        player_role=["defender"],
        declarer_player=[declarer_player],
    )
    assert document["player_role"] == "defender"
    assert document["declarer_player"] == declarer_player


def test_strict_form_shape_allowlist_duplicates_checkboxes_and_integer_bounds() -> None:
    with pytest.raises(PositionFormError) as duplicate:
        parse_position_form_v1(_form(game_type=["grand", "null"]))
    assert duplicate.value.field_messages["game_type"] == (
        "This field must be supplied exactly once.",
    )
    assert duplicate.value.draft.form_values.all("game_type") == ("grand", "null")

    with pytest.raises(PositionFormError) as unknown:
        parse_position_form_v1(_form(opponent_statistics_file=["private.json"]))
    assert "opponent_statistics_file" in unknown.value.field_messages
    assert not unknown.value.draft.form_values.contains("opponent_statistics_file")

    with pytest.raises(PositionFormError) as checkbox:
        parse_position_form_v1(_form(ouvert=["true"]))
    assert checkbox.value.field_messages["ouvert"] == (
        "Checkbox value must be 'on' when selected.",
    )

    with pytest.raises(PositionFormError) as integer:
        parse_position_form_v1(_form(sample_count=["true"]))
    assert "integer" in integer.value.field_messages["sample_count"][0]

    with pytest.raises(PositionFormError) as bounds:
        parse_position_form_v1(_form(sample_count=["100001"]))
    assert bounds.value.field_messages["sample_count"] == ("sample_count must be at most 100000.",)


def test_draft_values_and_errors_are_immutable() -> None:
    draft = parse_position_form_v1(_form())
    with pytest.raises(FrozenInstanceError):
        draft.game_type = "null"  # type: ignore[misc]
    error = FormFieldErrorV1("hand", "Invalid hand.")
    with pytest.raises(FrozenInstanceError):
        error.message = "changed"  # type: ignore[misc]
    with pytest.raises(PositionFormError) as caught:
        parse_position_form_v1(_form(game_type=["bad"]))
    with pytest.raises(AttributeError):
        caught.value.draft = draft  # type: ignore[misc]


def test_completed_trick_text_derives_players_winner_turn_and_hand_sizes() -> None:
    document = _document(
        completed_tricks=["me|C7,C8,CA"],
        trick_leader=["right"],
        hand=["CJ", "CQ", "C9", "S7", "S8", "S9", "H7", "H8"],
        current_trick=["S10", "SA"],
        left_hand_size=["9"],
        right_hand_size=["8"],
    )
    trick = document["completed_tricks"][0]
    assert trick == {
        "cards": ["C7", "C8", "CA"],
        "players": ["me", "left", "right"],
        "winner_role": "defenders",
        "winner_player": "right",
    }
    assert document["trick_leader"] == "right"
    assert document["next_player"] == "left"
    assert document["left_hand_size"] == 9
    assert document["right_hand_size"] == 8


def test_local_hand_size_must_match_attributed_play() -> None:
    draft = parse_position_form_v1(
        _form(
            completed_tricks=["me|C7,C8,CA"],
            trick_leader=["right"],
            hand=["CJ", "CQ", "C9", "S7", "S8", "S9", "H7", "H8", "D7"],
            current_trick=["S10", "SA"],
        )
    )

    with pytest.raises(PositionFormError) as error:
        build_guided_position_execution_v1(draft)

    assert "expected 8 Cards, got 9" in error.value.field_messages["hand"][0]


def test_guided_completed_trick_selectors_build_the_same_canonical_history() -> None:
    document = _document(
        completed_trick_1_leader=["me"],
        completed_trick_1_card_1=["C7"],
        completed_trick_1_card_2=["C8"],
        completed_trick_1_card_3=["CA"],
        trick_leader=["right"],
        hand=["CJ", "CQ", "C9", "S7", "S8", "S9", "H7", "H8", "D7"],
    )

    assert document["completed_tricks"] == [
        {
            "cards": ["C7", "C8", "CA"],
            "players": ["me", "left", "right"],
            "winner_role": "defenders",
            "winner_player": "right",
        }
    ]
    assert document["left_hand_size"] == 9
    assert document["right_hand_size"] == 9


def test_incomplete_guided_completed_trick_has_one_field_local_error() -> None:
    with pytest.raises(PositionFormError) as error:
        parse_position_form_v1(
            _form(
                completed_trick_1_leader=["me"],
                completed_trick_1_card_1=["C7"],
            )
        )

    assert error.value.field_messages["completed_tricks"] == (
        "Completed Trick 1 requires one leader and three Cards.",
    )


def test_explicit_hand_size_must_match_attributed_history() -> None:
    draft = parse_position_form_v1(_form(left_hand_size=["9"]))
    with pytest.raises(PositionFormError) as error:
        build_guided_position_execution_v1(draft)
    assert "expected 10" in error.value.field_messages["left_hand_size"][0]


def test_known_card_zones_are_unique_but_actual_and_local_public_hand_may_overlap() -> None:
    with pytest.raises(PositionFormError) as duplicate:
        parse_position_form_v1(_form(skat=["CJ", "D7"]))
    assert "Card CJ" in duplicate.value.field_messages["hand"][0]
    assert "Card CJ" in duplicate.value.field_messages["skat"][0]

    hand = _form()["hand"]
    draft = parse_position_form_v1(
        _form(
            analysis_mode=["post_game_review"],
            actual_card_played=["CJ"],
            ouvert=["on"],
            public_declarer_cards=hand,
        )
    )
    assert draft.actual_card_played == "CJ"


def test_visible_skat_visibility_follows_existing_live_and_retrospective_rules() -> None:
    live = _document(skat=["D7", "D8"])
    assert live["skat_visibility"] == "known_to_declarer"
    retrospective = _document(
        analysis_mode=["post_game_review"],
        actual_card_played=["CJ"],
        skat=["D7", "D8"],
    )
    assert retrospective["skat_visibility"] == "known_post_game"

    with pytest.raises(PositionFormError) as defender:
        parse_position_form_v1(
            _form(
                player_role=["defender"],
                declarer_player=["left"],
                skat=["D7", "D8"],
            )
        )
    assert "private to the local Declarer" in defender.value.field_messages["skat"][0]


def test_defaults_are_exact_and_immediate_method_is_omitted() -> None:
    request, options = _build()
    document = request.to_dict()["document"]
    assert request.workflow is WorkflowV1.POSITION_ANALYSIS
    assert document["sample_count"] == DEFAULT_POSITION_SAMPLE_COUNT_V1 == 1000
    assert document["random_seed"] == DEFAULT_POSITION_RANDOM_SEED_V1 == 42
    assert document["use_basic_opponent_strategy"] is True
    assert document["analysis_mode"] == "live_decision"
    assert document["game_end_reason"] == "not_ended"
    assert "recommendation_method" not in document
    assert options.validate_output is True
    assert options.include_provenance is False
    assert dict(options.workflow_options) == {}
    assert options.opponent_statistics_document is None
    assert options.opponent_statistics_reference is None


def test_method_labels_and_exact_search_maps_use_interactive_profile() -> None:
    methods = [
        (item.form_value, item.label, item.recommendation_method)
        for item in POSITION_ANALYSIS_METHODS_V1
    ]
    assert methods == [
        ("immediate", "Standard immediate analysis", None),
        ("bounded_search", "Bounded Search", "bounded_search"),
        ("auto", "Automatic Search with Immediate fallback", "auto"),
        (
            "information_set_search",
            "Information-set Search",
            "information_set_search",
        ),
    ]
    budget = get_search_budget_profile(INTERACTIVE_SEARCH_BUDGET_PROFILE)
    for method in ("bounded_search", "auto"):
        document = _document(analysis_method=[method], search_seed=["91"])
        assert document["recommendation_method"] == method
        assert document["bounded_search_settings"] == {
            "random_seed": 91,
            "max_remaining_tricks": budget.max_remaining_tricks,
            "max_depth_plies": budget.max_depth_plies,
            "max_nodes": budget.max_nodes,
            "max_selected_worlds": budget.max_selected_worlds,
            "max_sampled_worlds": budget.max_sampled_worlds,
            "minimum_comparable_worlds": budget.minimum_comparable_worlds,
            "wall_clock_timeout_ms": budget.wall_clock_timeout_ms,
        }

    converted = convert_requested_search_budget_to_information_set_search_budget_v1(budget)
    information_set = _document(
        analysis_method=["information_set_search"],
        search_seed=["92"],
    )
    assert information_set["recommendation_method"] == "information_set_search"
    assert information_set["information_set_search_settings"] == {
        "random_seed": 92,
        "max_remaining_tricks": converted.max_remaining_tricks,
        "max_depth_plies": converted.max_depth_plies,
        "max_state_nodes": converted.max_state_nodes,
        "max_information_sets": converted.max_information_sets,
        "max_selected_worlds": converted.max_selected_worlds,
        "max_sampled_worlds": converted.max_sampled_worlds,
        "minimum_comparable_worlds": converted.minimum_comparable_worlds,
        "wall_clock_timeout_ms": converted.wall_clock_timeout_ms,
    }


def test_advanced_options_map_without_external_statistics_fields() -> None:
    _, options = _build(
        opponent_strategy=["random"],
        opponent_policy_preset=["cautious_defender"],
        opponent_lead_policy=["lowest_point"],
        opponent_response_policy=["highest_point"],
        left_opponent_lead_policy=["basic_defender_lead"],
        left_opponent_response_policy=["basic_defender_response"],
        right_opponent_lead_policy=["random_legal"],
        right_opponent_response_policy=["basic_trick_play"],
        use_profile_presets=["on"],
        multi_step_count=["2"],
        card_selection_policy=["highest_expected_value"],
        expected_value_sample_count=["250"],
        strict_context=["on"],
        compare_policies=["on"],
        comparison_only=["on"],
        include_provenance=["on"],
    )
    assert dict(options.workflow_options) == {
        "opponent_strategy_override": "random",
        "opponent_policy_preset_override": "cautious_defender",
        "opponent_lead_policy_override": "lowest_point",
        "opponent_response_policy_override": "highest_point",
        "left_opponent_lead_policy_override": "basic_defender_lead",
        "left_opponent_response_policy_override": "basic_defender_response",
        "right_opponent_lead_policy_override": "random_legal",
        "right_opponent_response_policy_override": "basic_trick_play",
        "multi_step_count": 2,
        "card_selection_policy": "highest_expected_value",
        "use_profile_presets_override": True,
        "expected_value_sample_count": 250,
        "strict_context": True,
        "compare_policies": True,
        "comparison_only": True,
    }
    assert options.include_provenance is True
    assert options.opponent_statistics_document is None
    assert options.opponent_statistics_reference is None


def test_retrospective_actual_card_must_be_in_hand_and_legal() -> None:
    with pytest.raises(PositionFormError) as missing:
        parse_position_form_v1(_form(analysis_mode=["post_game_review"]))
    assert "actual_card_played" in missing.value.field_messages

    illegal_hand = ["CJ", "SA", "S10", "SK", "SQ", "S9", "S8", "H7", "H8", "D7"]
    assert "CJ" not in get_legal_cards(illegal_hand, ["S7"], "grand")
    draft = parse_position_form_v1(
        _form(
            analysis_mode=["post_game_review"],
            hand=illegal_hand,
            trick_leader=["right"],
            current_trick=["S7"],
            actual_card_played=["CJ"],
        )
    )
    with pytest.raises(PositionFormError) as illegal:
        build_guided_position_execution_v1(draft)
    assert "legal" in illegal.value.field_messages["actual_card_played"][0]

    document = _document(
        analysis_mode=["post_game_review"],
        hand=illegal_hand,
        trick_leader=["right"],
        current_trick=["S7"],
        actual_card_played=["SA"],
    )
    assert document["actual_card_played"] == "SA"
    assert document["analysis_mode"] == "post_game_review"


def test_build_calls_public_parse_request_once(monkeypatch: pytest.MonkeyPatch) -> None:
    import skatmind.app_web.position_form as module

    original = module.parse_request
    calls = []

    def counted(document: object) -> RequestDocumentV1:
        calls.append(document)
        return original(document)

    monkeypatch.setattr(module, "parse_request", counted)
    request, _ = module.build_guided_position_execution_v1(module.parse_position_form_v1(_form()))
    assert isinstance(request, RequestDocumentV1)
    assert len(calls) == 1
