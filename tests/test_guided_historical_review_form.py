from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from skatmind.api.v1 import ExecutionOptionsV1, RequestDocumentV1, WorkflowV1
from skatmind.app_web.historical_form import (
    HISTORICAL_FORM_STEPS,
    HISTORICAL_GAME_ID,
    HISTORICAL_PLAYER_IDS,
    HISTORICAL_SEATS,
    HistoricalFormDraftV1,
    append_historical_play_v1,
    build_historical_execution_options_v1,
    build_historical_options_summary_v1,
    build_historical_play_view_v1,
    build_historical_request_v1,
    create_historical_form_draft_v1,
    go_back_historical_form_v1,
    undo_historical_play_v1,
    update_historical_deal_v1,
    update_historical_declaration_v1,
    update_historical_discards_v1,
    update_historical_options_v1,
    update_historical_players_v1,
)
from skatmind.app_web.historical_form_parsing import (
    HistoricalFormInputError,
    parse_historical_deal_form_v1,
    parse_historical_play_form_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
SOURCE_PATH = PROJECT_ROOT / "src" / "skatmind" / "app_web" / "historical_form.py"
ORIGINAL_TO_FRONTEND_ID = {
    "player-a": "frontend-forehand",
    "player-b": "frontend-middlehand",
    "player-c": "frontend-rearhand",
}


def _example_game() -> dict[str, object]:
    root = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    return root["historical_game_input"]


def _draft_after_deal() -> HistoricalFormDraftV1:
    game = _example_game()
    players = game["players"]
    draft = update_historical_players_v1(
        create_historical_form_draft_v1(),
        forehand_label="Alice",
        rearhand_label="Carol",
    )
    return update_historical_deal_v1(
        draft,
        forehand_hand=players[0]["initial_hand"],
        middlehand_hand=players[1]["initial_hand"],
        rearhand_hand=players[2]["initial_hand"],
        skat=game["skat"],
    )


def _draft_at_play(*, hand_game: bool = False) -> HistoricalFormDraftV1:
    game = _example_game()
    draft = update_historical_declaration_v1(
        _draft_after_deal(),
        declarer_player_id="frontend-middlehand",
        game_type="grand",
        bid_value=18,
        hand_game=hand_game,
    )
    return update_historical_discards_v1(
        draft,
        () if hand_game else game["discarded_cards"],
    )


def _completed_example_draft() -> HistoricalFormDraftV1:
    game = _example_game()
    draft = _draft_at_play()
    for trick in game["tricks"]:
        for play in trick["plays"]:
            view = build_historical_play_view_v1(draft)
            assert view.acting_player_id == ORIGINAL_TO_FRONTEND_ID[play["player_id"]]
            draft = append_historical_play_v1(draft, play["card"])
    return draft


def _complete_with_first_legal_card(draft: HistoricalFormDraftV1) -> HistoricalFormDraftV1:
    while len(draft.plays) < 30:
        view = build_historical_play_view_v1(draft)
        draft = append_historical_play_v1(draft, view.legal_cards[0])
    return draft


@pytest.fixture(scope="module")
def completed_draft() -> HistoricalFormDraftV1:
    return _completed_example_draft()


def test_draft_starts_at_first_of_exactly_seven_steps_with_fixed_identity() -> None:
    draft = create_historical_form_draft_v1()

    assert HISTORICAL_FORM_STEPS == (
        "players",
        "deal",
        "declaration",
        "discards",
        "play",
        "options",
        "review",
    )
    assert draft.step == 1
    assert draft.step_name == "players"
    assert tuple(player.player_id for player in draft.players) == HISTORICAL_PLAYER_IDS
    assert tuple(player.seat for player in draft.players) == HISTORICAL_SEATS
    assert tuple(player.player_label for player in draft.players) == (None, None, None)
    with pytest.raises(FrozenInstanceError):
        draft.step = 2


def test_players_deal_and_discards_preserve_exact_form_facts() -> None:
    game = _example_game()
    draft = _draft_after_deal()

    assert draft.step == 3
    assert tuple(player.player_label for player in draft.players) == (
        "Alice",
        None,
        "Carol",
    )
    assert tuple(player.initial_hand for player in draft.players) == tuple(
        tuple(player["initial_hand"]) for player in game["players"]
    )
    assert draft.skat == tuple(game["skat"])

    draft = update_historical_declaration_v1(
        draft,
        declarer_player_id="frontend-middlehand",
        game_type="grand",
        bid_value=18,
    )
    with pytest.raises(ValueError, match="belong to the declarer"):
        update_historical_discards_v1(draft, ("CA", "D8"))
    draft = update_historical_discards_v1(draft, game["discarded_cards"])
    assert draft.discarded_cards == ("SK", "SQ")
    assert draft.step_name == "play"


def test_deal_requires_exact_unique_canonical_10_10_10_2_cards() -> None:
    game = _example_game()
    players = game["players"]
    draft = update_historical_players_v1(create_historical_form_draft_v1())

    short_forehand = players[0]["initial_hand"][:-1]
    with pytest.raises(ValueError, match="exactly 10"):
        update_historical_deal_v1(
            draft,
            forehand_hand=short_forehand,
            middlehand_hand=players[1]["initial_hand"],
            rearhand_hand=players[2]["initial_hand"],
            skat=game["skat"],
        )

    duplicate_middlehand = list(players[1]["initial_hand"])
    duplicate_middlehand[0] = players[0]["initial_hand"][0]
    with pytest.raises(ValueError, match="duplicate cards"):
        update_historical_deal_v1(
            draft,
            forehand_hand=players[0]["initial_hand"],
            middlehand_hand=duplicate_middlehand,
            rearhand_hand=players[2]["initial_hand"],
            skat=game["skat"],
        )


def test_invalid_deal_retains_safe_submitted_card_selections() -> None:
    game = _example_game()
    players = game["players"]
    draft = update_historical_players_v1(create_historical_form_draft_v1())

    with pytest.raises(HistoricalFormInputError) as error:
        parse_historical_deal_form_v1(
            draft,
            {
                "forehand_hand": players[0]["initial_hand"][:-1],
                "middlehand_hand": players[1]["initial_hand"],
                "rearhand_hand": players[2]["initial_hand"],
                "skat": game["skat"],
            },
        )

    retained = error.value.draft
    assert retained is not None
    assert retained.step == 2
    assert retained.players[0].initial_hand == tuple(players[0]["initial_hand"][:-1])
    assert retained.players[1].initial_hand == tuple(players[1]["initial_hand"])
    assert retained.skat == tuple(game["skat"])

@pytest.mark.parametrize(
    "game_type",
    ("clubs", "spades", "hearts", "diamonds", "grand", "null"),
)
def test_declaration_accepts_all_six_game_types(game_type: str) -> None:
    game = _example_game()
    draft = update_historical_declaration_v1(
        _draft_after_deal(),
        declarer_player_id="frontend-middlehand",
        game_type=game_type,
        bid_value=18,
    )
    draft = update_historical_discards_v1(draft, game["discarded_cards"])
    draft = _complete_with_first_legal_card(draft)
    request = build_historical_request_v1(draft)
    historical = request.to_dict()["document"]["historical_game_input"]

    assert draft.declaration is not None
    assert draft.declaration.game_type == game_type
    assert historical["declaration"]["game_type"] == game_type
    assert sum(len(trick["plays"]) for trick in historical["tricks"]) == 30


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "discard_count"),
    (
        (False, False, 2),
        (True, False, 0),
        (False, True, 2),
        (True, True, 0),
    ),
)
def test_all_four_null_hand_and_ouvert_variants_use_exact_discard_count(
    hand_game: bool,
    ouvert: bool,
    discard_count: int,
) -> None:
    game = _example_game()
    draft = update_historical_declaration_v1(
        _draft_after_deal(),
        declarer_player_id="frontend-middlehand",
        game_type="null",
        bid_value=18,
        hand_game=hand_game,
        ouvert=ouvert,
    )
    discarded_cards = () if hand_game else tuple(game["discarded_cards"])
    draft = update_historical_discards_v1(draft, discarded_cards)
    draft = _complete_with_first_legal_card(draft)
    request = build_historical_request_v1(draft)
    historical = request.to_dict()["document"]["historical_game_input"]

    assert draft.declaration is not None
    assert (draft.declaration.hand_game, draft.declaration.ouvert) == (
        hand_game,
        ouvert,
    )
    assert len(draft.discarded_cards) == discard_count
    assert historical["declaration"]["hand_game"] is hand_game
    assert historical["declaration"]["ouvert"] is ouvert
    assert len(historical["discarded_cards"]) == discard_count


def test_play_view_derives_actor_legality_winner_and_next_leader() -> None:
    draft = _draft_at_play()
    first_view = build_historical_play_view_v1(draft)
    assert first_view.acting_player_id == "frontend-forehand"
    assert first_view.current_trick_leader_player_id == "frontend-forehand"
    assert first_view.next_leader_player_id == "frontend-forehand"
    assert first_view.legal_cards == draft.players[0].initial_hand

    draft = append_historical_play_v1(draft, "SA")
    second_view = build_historical_play_view_v1(draft)
    assert second_view.acting_player_id == "frontend-middlehand"
    assert second_view.legal_cards == ("S9", "S8", "S7")
    with pytest.raises(ValueError, match="illegal"):
        append_historical_play_v1(draft, "HA")

    draft = append_historical_play_v1(draft, "S9")
    draft = append_historical_play_v1(draft, "H9")
    next_view = build_historical_play_view_v1(draft)
    completed = next_view.completed_tricks[0]
    assert completed.winner_player_id == "frontend-forehand"
    assert completed.next_leader_player_id == "frontend-forehand"
    assert next_view.last_trick_winner_player_id == "frontend-forehand"
    assert next_view.acting_player_id == "frontend-forehand"
    assert next_view.next_leader_player_id == "frontend-forehand"


def test_undo_removes_only_final_card_and_preserves_prior_draft() -> None:
    initial = _draft_at_play()
    after_one = append_historical_play_v1(initial, "SA")
    after_two = append_historical_play_v1(after_one, "S9")
    undone = undo_historical_play_v1(after_two)

    assert after_two.plays[:-1] == after_one.plays
    assert undone.plays == after_one.plays
    assert build_historical_play_view_v1(undone).acting_player_id == ("frontend-middlehand")
    assert after_two.plays[-1].card == "S9"
    assert after_two.step == 5
    with pytest.raises(ValueError, match="no Historical play"):
        undo_historical_play_v1(initial)


def test_known_example_builds_only_after_30_plays_with_exact_root(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    game = _example_game()
    incomplete = undo_historical_play_v1(completed_draft)
    with pytest.raises(ValueError, match="exactly 30 plays"):
        build_historical_request_v1(incomplete)

    assert completed_draft.step_name == "options"
    final_view = build_historical_play_view_v1(completed_draft)
    assert final_view.is_complete is True
    assert final_view.played_card_count == 30
    assert final_view.acting_player_id is None
    assert final_view.legal_cards == ()
    assert len(final_view.completed_tricks) == 10

    request = build_historical_request_v1(completed_draft)
    root = request.to_dict()["document"]
    historical = root["historical_game_input"]
    assert type(request) is RequestDocumentV1
    assert request.workflow is WorkflowV1.HISTORICAL_GAME
    assert historical["game_id"] == HISTORICAL_GAME_ID
    assert "played_at" not in historical
    assert [player["player_id"] for player in historical["players"]] == list(HISTORICAL_PLAYER_IDS)
    assert [player["seat"] for player in historical["players"]] == list(HISTORICAL_SEATS)
    assert [player.get("player_label") for player in historical["players"]] == (
        ["Alice", None, "Carol"]
    )
    assert [player["initial_hand"] for player in historical["players"]] == [
        player["initial_hand"] for player in game["players"]
    ]
    assert historical["skat"] == game["skat"]
    assert historical["discarded_cards"] == game["discarded_cards"]
    assert historical["declarer_player_id"] == "frontend-middlehand"
    assert historical["game_end_reason"] == "normal_completion"
    assert len(historical["tricks"]) == 10
    assert sum(len(trick["plays"]) for trick in historical["tricks"]) == 30


def test_canonical_declaration_dependencies_are_rejected_before_play_entry(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    declaration = completed_draft.declaration
    assert declaration is not None
    invalid = replace(
        completed_draft,
        declaration=replace(
            declaration,
            ouvert=True,
            hand_game=False,
            schneider_announced=False,
            schwarz_announced=False,
        ),
    )

    with pytest.raises(ValueError, match="ouvert=true requires schwarz_announced=true"):
        build_historical_request_v1(invalid)

    declaration_step = replace(completed_draft, step=3, plays=())
    with pytest.raises(ValueError, match="ouvert=true requires schwarz_announced=true"):
        update_historical_declaration_v1(
            declaration_step,
            declarer_player_id=declaration.declarer_player_id,
            game_type=declaration.game_type,
            bid_value=declaration.bid_value,
            ouvert=True,
        )


@pytest.mark.parametrize(
    ("form_name", "public_name", "needs_search", "has_review"),
    (
        ("decision_snapshots", "decision_snapshots", False, False),
        ("immediate_review", "immediate_review", False, True),
        ("search_review", "search_review", True, True),
        (
            "information_set_search_review",
            "information_set_search_review",
            True,
            True,
        ),
        ("replay_coaching", "replay_coaching", True, True),
        (
            "information_set_replay_coaching",
            "information_set_replay_coaching",
            True,
            True,
        ),
        ("tactical", "historical_tactical_motif_review", False, False),
    ),
)
def test_each_optional_historical_output_maps_to_existing_public_options(
    completed_draft: HistoricalFormDraftV1,
    form_name: str,
    public_name: str,
    needs_search: bool,
    has_review: bool,
) -> None:
    selected = update_historical_options_v1(
        completed_draft,
        **{form_name: True},
        search_seed=73,
        immediate_sample_count=1,
        immediate_base_random_seed=43,
    )
    execution_options = build_historical_execution_options_v1(selected)
    workflow_options = execution_options.to_dict()["workflow_options"]

    assert type(execution_options) is ExecutionOptionsV1
    assert workflow_options[public_name] is True
    assert ("search_seed" in workflow_options) is needs_search
    assert ("search_budget_profile" in workflow_options) is needs_search
    if needs_search:
        assert workflow_options["search_seed"] == 73
        assert workflow_options["search_budget_profile"] == "historical_review_v1"
    assert ("immediate_sample_count" in workflow_options) is has_review
    assert ("immediate_base_random_seed" in workflow_options) is has_review
    if has_review:
        assert workflow_options["immediate_sample_count"] == 1
        assert workflow_options["immediate_base_random_seed"] == 43
    assert "settlement" not in workflow_options


def test_base_settlement_needs_no_option_and_summary_shows_safe_prerequisites(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    base_options = build_historical_execution_options_v1(completed_draft)
    base_summary = build_historical_options_summary_v1(completed_draft)
    assert base_options.to_dict()["workflow_options"] == {}
    assert base_summary.always_included == ("game_result", "final_settlement")
    assert base_summary.selected_outputs == ()
    assert base_summary.implied_prerequisites == ()

    selected = update_historical_options_v1(
        completed_draft,
        replay_coaching=True,
        search_seed=73,
        immediate_sample_count=1,
        immediate_base_random_seed=43,
    )
    summary = build_historical_options_summary_v1(selected)
    assert summary.selected_outputs == ("replay_coaching",)
    assert summary.implied_prerequisites == (
        "decision_snapshots_prepared_internally",
        "immediate_comparison_prepared_internally",
        "classic_search_review_prepared_for_replay_coaching",
    )
    assert "73" not in repr(summary)
    assert "43" not in repr(summary)


def test_historical_provenance_is_an_explicit_public_execution_option(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    selected = update_historical_options_v1(
        completed_draft,
        include_provenance=True,
    )
    options = build_historical_execution_options_v1(selected)
    summary = build_historical_options_summary_v1(selected)

    assert options.include_provenance is True
    assert dict(options.workflow_options) == {}
    assert summary.selected_outputs == ("field_provenance",)


def test_classic_and_information_set_search_families_cannot_mix(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        update_historical_options_v1(
            completed_draft,
            replay_coaching=True,
            information_set_search_review=True,
        )


def test_historical_sample_count_uses_the_existing_product_maximum(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    with pytest.raises(ValueError, match="from 1 through 100000"):
        update_historical_options_v1(
            completed_draft,
            immediate_review=True,
            immediate_sample_count=100_001,
        )


def test_back_is_immutable_and_stays_within_the_seven_steps(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    review = update_historical_options_v1(completed_draft, decision_snapshots=True)
    options = go_back_historical_form_v1(review)

    assert review.step == 7
    assert review.step_name == "review"
    assert options.step == 6
    assert options.step_name == "options"
    assert options.plays == review.plays
    with pytest.raises(ValueError, match="no preceding step"):
        go_back_historical_form_v1(create_historical_form_draft_v1())


def test_back_preserves_play_and_can_return_to_options(
    completed_draft: HistoricalFormDraftV1,
) -> None:
    play = go_back_historical_form_v1(completed_draft)
    assert play.step == 5
    assert play.plays == completed_draft.plays

    options = parse_historical_play_form_v1(play, {})
    assert options.step == 6
    assert options.plays == completed_draft.plays

    partial = undo_historical_play_v1(completed_draft)
    discards = go_back_historical_form_v1(partial)
    restored = update_historical_discards_v1(discards, discards.discarded_cards)
    assert restored.step == 5
    assert restored.plays == partial.plays

    with pytest.raises(ValueError, match="step 5"):
        parse_historical_play_form_v1(completed_draft, {})


def test_duplicate_non_empty_player_labels_are_rejected() -> None:
    with pytest.raises(ValueError, match="labels must be unique"):
        update_historical_players_v1(
            create_historical_form_draft_v1(),
            forehand_label="Same Player",
            middlehand_label="Same Player",
        )


def test_form_domain_has_no_persistence_or_other_product_area_objects() -> None:
    draft = create_historical_form_draft_v1()
    assert set(draft.__slots__) == {
        "step",
        "players",
        "skat",
        "declaration",
        "discarded_cards",
        "plays",
        "options",
    }
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "validate_observed_game_trace_v1" in source
    assert "get_trick_winner" not in source
    for forbidden_import in (
        "from skatmind.session",
        "from skatmind.match_workspace",
        "from skatmind.corpus",
        "import skatmind.session",
        "import skatmind.match_workspace",
        "import skatmind.corpus",
    ):
        assert forbidden_import not in source
