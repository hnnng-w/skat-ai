import copy
import json
from dataclasses import asdict
from pathlib import Path

import pytest
from test_historical_declarer_concession import build_concession_prefix
from test_historical_defender_concession import build_defender_concession_prefix
from test_historical_game import build_historical_input
from test_historical_opponent_profiles import stub_expected_value_recommendation
from test_training_dataset import build_training_input

from skat_ai.dataset_partition_audit import audit_training_dataset_partitions
from skat_ai.declarer_card_exposure import (
    DeclarerCardExposure,
    DeclarerCardExposureDetails,
    DeclarerExposedCardEvidence,
    DefenderExposureResponse,
    adjudicate_accepted_declarer_card_exposure,
)
from skat_ai.declarer_concession import DeclarerCardCountEvidence
from skat_ai.final_settlement import build_final_settlement_summary
from skat_ai.game_result import build_game_result_summary_from_score_summary
from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary_from_input,
)
from skat_ai.historical_game_review import build_historical_game_review_summary
from skat_ai.historical_opponent_profile_binding import (
    resolve_historical_opponent_profile_bindings,
)
from skat_ai.historical_opponent_statistics import (
    aggregate_historical_opponent_statistics,
    build_exportable_opponent_statistics_input,
)
from skat_ai.input_loader import load_opponent_statistics_from_json
from skat_ai.rolling_opponent_policy_evaluation import (
    build_serializable_rolling_opponent_policy_evaluation,
    evaluate_rolling_opponent_policy_predictions,
)
from skat_ai.training_dataset import (
    build_training_dataset_input,
    build_training_dataset_summary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NORMAL_EXAMPLE_PATH = PROJECT_ROOT / "examples" / "historical_grand_normal_completion.json"
EXPOSURE_EXAMPLE_PATH = (
    PROJECT_ROOT / "examples" / "historical_grand_declarer_card_exposure.json"
)


def load_historical_data(path: Path = NORMAL_EXAMPLE_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)["historical_game_input"]


def _set_exact_exposed_cards(data: dict) -> None:
    declarer_id = data["declarer_player_id"]
    declarer = next(
        player for player in data["players"] if player["player_id"] == declarer_id
    )
    hand = list(declarer["initial_hand"])
    if not data["declaration"].get("hand_game", False):
        hand.extend(data["skat"])
        for card in data["discarded_cards"]:
            hand.remove(card)
    for trick in data["tricks"]:
        for play in trick["plays"]:
            if play["player_id"] == declarer_id:
                hand.remove(play["card"])
    data["game_end"]["exposure"]["exposed_cards"] = hand


def build_exposure_prefix(
    *,
    completed_trick_count: int = 0,
    current_trick_card_count: int = 0,
    exposure_form: str = "laid_open",
    shown_to_defender_player_id: str | None = None,
    claimed_play_level: str = "simple",
) -> dict:
    data = load_historical_data()
    tricks = copy.deepcopy(data["tricks"][:completed_trick_count])
    if current_trick_card_count:
        current = copy.deepcopy(data["tricks"][completed_trick_count])
        current["plays"] = current["plays"][:current_trick_card_count]
        tricks.append(current)
    exposure = {"form": exposure_form, "exposed_cards": []}
    if exposure_form == "shown_to_defender":
        exposure["shown_to_defender_player_id"] = (
            shown_to_defender_player_id or "player-a"
        )
    data.update(
        {
            "game_id": "test-historical-declarer-card-exposure",
            "game_end_reason": "declarer_card_exposure",
            "game_end": {
                "schema_version": 1,
                "kind": "declarer_card_exposure",
                "exposure": exposure,
                "claimed_play_level": claimed_play_level,
                "defender_responses": [
                    {
                        "defender_player_id": "player-c",
                        "response": "accept",
                        "form": "unambiguous_conduct",
                    },
                    {
                        "defender_player_id": "player-a",
                        "response": "accept",
                        "form": "explicit",
                    },
                ],
            },
            "tricks": tricks,
        }
    )
    _set_exact_exposed_cards(data)
    return data


@pytest.mark.parametrize(
    ("completed_tricks", "current_cards", "expected_plays"),
    [(0, 0, 0), (0, 1, 1), (0, 2, 2), (4, 0, 12), (4, 1, 13), (4, 2, 14)],
)
def test_zero_complete_and_incomplete_play_prefixes_are_supported(
    completed_tricks: int,
    current_cards: int,
    expected_plays: int,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_exposure_prefix(
            completed_trick_count=completed_tricks,
            current_trick_card_count=current_cards,
        )
    )

    assert summary["play_prefix_summary"]["played_card_count"] == expected_plays
    assert summary["play_prefix_summary"]["current_trick_card_count"] == current_cards
    assert ("incomplete_current_trick" in summary) is bool(current_cards)
    assert summary["historical_game_end_summary"]["card_reconciliation"] == "confirmed"


def test_twenty_nine_plays_require_a_remaining_declarer_card_and_thirty_are_rejected() -> None:
    data = build_exposure_prefix(completed_trick_count=9)
    final_trick = copy.deepcopy(load_historical_data()["tricks"][9])
    final_trick["plays"] = final_trick["plays"][:2]
    data["tricks"].append(final_trick)
    data["game_end"]["exposure"]["exposed_cards"] = ["D9"]

    with pytest.raises(ValueError, match="non-empty reconstructed declarer hand"):
        build_historical_game_summary_from_input(data)

    data = build_exposure_prefix()
    data["tricks"] = copy.deepcopy(load_historical_data()["tricks"])
    with pytest.raises(ValueError, match="after all 30 playable cards"):
        build_historical_game_summary_from_input(data)


def test_twenty_nine_plays_are_supported_when_the_declarer_has_the_last_card() -> None:
    data = build_exposure_prefix(completed_trick_count=9)
    final_trick = copy.deepcopy(load_historical_data()["tricks"][9])
    final_trick["plays"] = final_trick["plays"][:2]
    data["tricks"].append(final_trick)
    player_b = next(
        player for player in data["players"] if player["player_id"] == "player-b"
    )
    player_b["initial_hand"] = [
        "D8" if card == "SK" else "D7" if card == "SQ" else card
        for card in player_b["initial_hand"]
    ]
    data["skat"] = ["SK", "SQ"]
    data["declarer_player_id"] = "player-c"
    data["discarded_cards"] = ["SK", "SQ"]
    data["game_end"]["defender_responses"] = [
        {"defender_player_id": "player-b", "response": "accept", "form": "explicit"},
        {
            "defender_player_id": "player-a",
            "response": "accept",
            "form": "unambiguous_conduct",
        },
    ]
    _set_exact_exposed_cards(data)

    summary = build_historical_game_summary_from_input(data)

    assert summary["play_prefix_summary"]["played_card_count"] == 29
    assert summary["historical_game_end_summary"]["exposed_cards"] == ["D9"]
    assert summary["historical_game_end_summary"]["card_reconciliation"] == "confirmed"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data.pop("game_end"), "game_end is required"),
        (
            lambda data: data["game_end"].update({"kind": "defender_concession"}),
            "kind must match",
        ),
        (
            lambda data: data["game_end"].update({"schema_version": 2}),
            "schema_version must be exactly 1",
        ),
        (lambda data: data["game_end"].update({"statement": "I am done"}), "unsupported"),
        (
            lambda data: data["game_end"]["defender_responses"][0].update(
                {"response": "continue"}
            ),
            "separate future work",
        ),
    ],
)
def test_event_union_is_strict_and_rejects_continuation(mutation, message: str) -> None:
    data = build_exposure_prefix()
    mutation(data)

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


@pytest.mark.parametrize("exposure_form", ["laid_open", "shown_to_defender"])
def test_exposure_forms_are_supported_and_serialized_with_stable_ids(
    exposure_form: str,
) -> None:
    summary = build_historical_game_summary_from_input(
        build_exposure_prefix(
            completed_trick_count=4,
            current_trick_card_count=2,
            exposure_form=exposure_form,
        )
    )
    event = summary["record"]["game_end"]
    end = summary["historical_game_end_summary"]

    assert event["exposure"]["form"] == exposure_form
    assert end["shown_to_defender_player_id"] == (
        "player-a" if exposure_form == "shown_to_defender" else None
    )
    serialized = json.dumps(summary)
    for relative_identity in ('"me"', '"left"', '"right"'):
        assert relative_identity not in serialized


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("exposure", "shown_to_defender_player_id"), "player-b", "stable defender"),
        (("exposure", "shown_to_defender_player_id"), "unknown", "stable defender"),
        (("exposure", "shown_to_defender_player_id"), "left", "relative"),
        (("defender_responses", 0, "defender_player_id"), "player-b", "stable defender"),
        (("defender_responses", 0, "defender_player_id"), "player-a", "exactly once"),
        (("defender_responses", 0, "form"), "ambiguous", "unambiguous_conduct"),
    ],
)
def test_shown_player_and_acceptances_require_exact_stable_defenders(
    path: tuple[object, ...], value: object, message: str
) -> None:
    data = build_exposure_prefix(exposure_form="shown_to_defender")
    target: object = data["game_end"]
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    with pytest.raises(ValueError, match=message):
        build_historical_game_record(data)


def test_response_and_card_order_are_canonicalized_by_seat_and_deck_order() -> None:
    data = build_exposure_prefix(completed_trick_count=4, current_trick_card_count=2)
    supplied_cards = data["game_end"]["exposure"]["exposed_cards"]
    data["game_end"]["exposure"]["exposed_cards"] = list(reversed(supplied_cards))
    summary = build_historical_game_summary_from_input(data)

    assert summary["record"]["game_end"]["defender_responses"] == [
        {"defender_player_id": "player-a", "response": "accept", "form": "explicit"},
        {
            "defender_player_id": "player-c",
            "response": "accept",
            "form": "unambiguous_conduct",
        },
    ]
    assert summary["record"]["game_end"]["exposure"]["exposed_cards"] == [
        "H10",
        "HK",
        "HQ",
        "D8",
        "D7",
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda cards: cards.pop(), "exact_historical_play_prefix"),
        (lambda cards: cards.append("C9"), "defender_owned_cards"),
        (lambda cards: cards.append("SJ"), "completed_tricks"),
        (lambda cards: cards.append("HA"), "current_trick"),
        (lambda cards: cards.append("SK"), "discarded_cards"),
    ],
)
def test_exposed_cards_must_exactly_match_replay_and_reject_unavailable_cards(
    mutation, message: str
) -> None:
    data = build_exposure_prefix(completed_trick_count=4, current_trick_card_count=2)
    mutation(data["game_end"]["exposure"]["exposed_cards"])

    with pytest.raises(ValueError, match=message):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize("invalid_cards", [[], ["HQ", "HQ"], ["X1"]])
def test_empty_duplicate_and_invalid_exposed_card_lists_are_rejected(
    invalid_cards: list[str],
) -> None:
    data = build_exposure_prefix()
    data["game_end"]["exposure"]["exposed_cards"] = invalid_cards

    with pytest.raises(ValueError, match="exposed_cards"):
        build_historical_game_record(data)


def test_hand_skat_cards_are_rejected_as_exposed() -> None:
    data = build_exposure_prefix()
    data["declaration"]["hand_game"] = True
    data["discarded_cards"] = []
    _set_exact_exposed_cards(data)
    data["game_end"]["exposure"]["exposed_cards"][-1] = "D8"

    with pytest.raises(ValueError, match="Hand-skat"):
        build_historical_game_summary_from_input(data)


def test_observed_and_unresolved_points_reconcile_without_assignment_or_defender_hands() -> None:
    summary = build_historical_game_summary_from_input(
        load_historical_data(EXPOSURE_EXAMPLE_PATH)
    )
    points = summary["point_accounting"]

    assert points == {
        "completed_trick_declarer_points": 15,
        "completed_trick_defender_points": 25,
        "skat_points": 7,
        "observed_declarer_points": 22,
        "observed_defender_points": 25,
        "unresolved_current_trick_points": 14,
        "unresolved_remaining_hand_points": 59,
        "total_unresolved_points": 73,
        "total_card_points": 120,
    }
    assert summary["game_result_summary"]["remaining_points_recipient"] is None
    assert summary["game_result_summary"]["remaining_points_assigned"] == 0
    assert "remaining_hands" not in json.dumps(summary)
    assert set(summary["historical_game_end_summary"]["exposed_cards"]) == {
        "H10",
        "HK",
        "HQ",
        "D8",
        "D7",
    }


@pytest.mark.parametrize("game_type", ["clubs", "spades", "hearts", "diamonds", "grand"])
@pytest.mark.parametrize("claimed_level", ["simple", "schneider", "schwarz"])
def test_suit_and_grand_claimed_levels_settle_without_achieved_labels(
    game_type: str, claimed_level: str
) -> None:
    data = build_exposure_prefix(claimed_play_level=claimed_level)
    data["declaration"]["game_type"] = game_type
    summary = build_historical_game_summary_from_input(data)
    basis = summary["final_settlement_summary"]["settlement_basis"]

    assert summary["winner"] == "declarer"
    assert basis["accepted_claimed_schneider_applied"] is (claimed_level != "simple")
    assert basis["accepted_claimed_schwarz_applied"] is (claimed_level == "schwarz")
    assert basis["achieved_schneider_applied"] is False
    assert basis["achieved_schwarz_applied"] is False
    assert summary["schneider_status"] == "not_applicable"


@pytest.mark.parametrize(
    "declaration_updates",
    [
        {"hand_game": True},
        {"hand_game": True, "schneider_announced": True},
        {
            "hand_game": True,
            "schneider_announced": True,
            "schwarz_announced": True,
        },
        {
            "hand_game": True,
            "schneider_announced": True,
            "schwarz_announced": True,
            "ouvert": True,
        },
    ],
)
def test_hand_announcements_and_ouvert_preserve_mandatory_levels(
    declaration_updates: dict,
) -> None:
    data = build_exposure_prefix(claimed_play_level="simple")
    data["declaration"].update(declaration_updates)
    data["discarded_cards"] = []
    _set_exact_exposed_cards(data)
    summary = build_historical_game_summary_from_input(data)
    basis = summary["final_settlement_summary"]["settlement_basis"]

    assert summary["winner"] == "declarer"
    mandatory_level = any(
        declaration_updates.get(field, False)
        for field in ("schneider_announced", "schwarz_announced", "ouvert")
    )
    assert basis["declared_mandatory_schneider_applied"] is mandatory_level
    assert basis["declared_mandatory_schwarz_applied"] is any(
        declaration_updates.get(field, False) for field in ("schwarz_announced", "ouvert")
    )
    assert basis["achieved_schneider_applied"] is False


@pytest.mark.parametrize(
    ("bid_value", "claim", "expected_winner"),
    [
        (49, "simple", "defenders"),
        (49, "schneider", "declarer"),
        (73, "schneider", "defenders"),
        (73, "schwarz", "declarer"),
    ],
)
def test_supported_overbid_requirements_must_be_covered_by_the_accepted_level(
    bid_value: int, claim: str, expected_winner: str
) -> None:
    data = build_exposure_prefix(claimed_play_level=claim)
    data["declaration"]["bid_value"] = bid_value
    summary = build_historical_game_summary_from_input(data)

    assert summary["winner"] == expected_winner
    assert summary["game_result_summary"]["overbid_required_value_applied"] is True
    assert summary["game_result_summary"]["overbid_requirement_covered"] is (
        expected_winner == "declarer"
    )


def test_overbid_requirement_beyond_schwarz_is_rejected() -> None:
    data = build_exposure_prefix(claimed_play_level="schwarz")
    data["declaration"]["bid_value"] = 121

    with pytest.raises(ValueError, match="beyond Schwarz"):
        build_historical_game_summary_from_input(data)


@pytest.mark.parametrize(
    ("hand_game", "ouvert", "expected_value"),
    [(False, False, 23), (True, False, 35), (False, True, 46), (True, True, 59)],
)
def test_all_four_null_variants_use_simple_claim_and_preserve_prior_trick_loss(
    hand_game: bool, ouvert: bool, expected_value: int
) -> None:
    win_data = build_exposure_prefix()
    win_data["declaration"] = {
        "game_type": "null",
        "hand_game": hand_game,
        "ouvert": ouvert,
        "bid_value": 18,
    }
    win_data["discarded_cards"] = [] if hand_game else ["SK", "SQ"]
    _set_exact_exposed_cards(win_data)
    win = build_historical_game_summary_from_input(win_data)

    loss_data = copy.deepcopy(win_data)
    loss_data["declarer_player_id"] = "player-a"
    loss_data["discarded_cards"] = [] if hand_game else ["C8", "C7"]
    loss_data["tricks"] = copy.deepcopy(load_historical_data()["tricks"][:1])
    loss_data["game_end"]["exposure"]["form"] = "laid_open"
    loss_data["game_end"]["exposure"].pop("shown_to_defender_player_id", None)
    loss_data["game_end"]["defender_responses"] = [
        {"defender_player_id": "player-b", "response": "accept", "form": "explicit"},
        {
            "defender_player_id": "player-c",
            "response": "accept",
            "form": "unambiguous_conduct",
        },
    ]
    _set_exact_exposed_cards(loss_data)
    loss = build_historical_game_summary_from_input(loss_data)

    assert win["final_settlement_summary"]["settlement_score"] == expected_value
    assert loss["final_settlement_summary"]["settlement_score"] == -2 * expected_value
    assert loss["game_result_summary"]["winner_basis"] == "preexisting_game_decision"


def test_null_rejects_claimed_schneider() -> None:
    data = build_exposure_prefix(claimed_play_level="schneider")
    data["declaration"] = {"game_type": "null", "bid_value": 18}

    with pytest.raises(ValueError, match="claimed_play_level='simple'"):
        build_historical_game_summary_from_input(data)


def _build_changed_declarer_prefix(declarer_id: str, completed_tricks: int) -> dict:
    data = build_exposure_prefix(completed_trick_count=completed_tricks)
    data["declarer_player_id"] = declarer_id
    data["discarded_cards"] = ["C8", "C7"]
    data["game_end"]["defender_responses"] = [
        {
            "defender_player_id": player_id,
            "response": "accept",
            "form": "explicit",
        }
        for player_id in ("player-a", "player-b", "player-c")
        if player_id != declarer_id
    ]
    _set_exact_exposed_cards(data)
    return data


@pytest.mark.parametrize(
    ("data", "expected_state", "expected_winner"),
    [
        (build_exposure_prefix(), "undecided", "declarer"),
        (_build_changed_declarer_prefix("player-a", 6), "declarer_already_won", "declarer"),
        (build_exposure_prefix(completed_trick_count=6), "defenders_already_won", "defenders"),
    ],
)
def test_undecided_and_preexisting_results_are_preserved(
    data: dict, expected_state: str, expected_winner: str
) -> None:
    summary = build_historical_game_summary_from_input(data)

    assert summary["historical_game_end_summary"]["decision_state_before_shortening"] == (
        expected_state
    )
    assert summary["winner"] == expected_winner
    assert summary["final_settlement_summary"]["winner"] == expected_winner


def test_historical_result_and_settlement_match_flat_accepted_exposure() -> None:
    summary = build_historical_game_summary_from_input(
        build_exposure_prefix(
            completed_trick_count=4,
            current_trick_card_count=2,
            claimed_play_level="schneider",
        )
    )
    completed_tricks = [
        {"winner_role": trick["winner_side"]} for trick in summary["derived_tricks"]
    ]
    raw_result = build_game_result_summary_from_score_summary(
        {
            "total_declarer_points": summary["declarer_points"],
            "total_defender_points": summary["defender_points"],
        },
        game_type="grand",
        completed_tricks=completed_tricks,
        game_end_reason="declarer_card_exposure",
    )
    exposed_cards = tuple(summary["record"]["game_end"]["exposure"]["exposed_cards"])
    flat = adjudicate_accepted_declarer_card_exposure(
        DeclarerCardExposure(
            1,
            "declarer_card_exposure",
            DeclarerCardExposureDetails("laid_open", exposed_cards),
            "schneider",
            (
                DefenderExposureResponse("left", "accept", "explicit"),
                DefenderExposureResponse("right", "accept", "unambiguous_conduct"),
            ),
        ),
        raw_result,
        summary["game_value_summary"],
        summary["overbid_summary"],
        completed_tricks,
        DeclarerExposedCardEvidence(
            "me",
            exposed_cards,
            DeclarerCardCountEvidence(len(exposed_cards), "exact_historical_play_prefix"),
            (),
        ),
    )
    flat_settlement = build_final_settlement_summary(
        summary["game_value_summary"],
        flat.game_result_summary,
        summary["overbid_summary"],
        completed_tricks,
    )

    assert flat.game_result_summary == summary["game_result_summary"]
    assert flat_settlement == summary["final_settlement_summary"]


def _decision_state(snapshot) -> dict:
    state = asdict(snapshot)
    state.pop("source_game_id", None)
    state.pop("source_played_at", None)
    return state


def test_shared_prefix_parity_and_terminal_fact_changes_do_not_affect_decisions() -> None:
    normal = build_historical_input()
    exposure = build_exposure_prefix(completed_trick_count=4, current_trick_card_count=2)
    exposure["played_at"] = normal.get("played_at")
    exposure_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(exposure)
    )
    normal_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(normal)
    )
    assert [_decision_state(row) for row in exposure_snapshots.snapshots] == [
        _decision_state(row) for row in normal_snapshots.snapshots[:14]
    ]

    for shortened in (
        build_concession_prefix(completed_trick_count=4, current_trick_card_count=2),
        build_defender_concession_prefix(
            completed_trick_count=4, current_trick_card_count=2
        ),
    ):
        shortened["played_at"] = exposure["played_at"]
        snapshots = build_historical_decision_snapshots(
            build_historical_game_summary_from_input(shortened)
        )
        assert [_decision_state(row) for row in snapshots.snapshots] == [
            _decision_state(row) for row in exposure_snapshots.snapshots
        ]

    changed = copy.deepcopy(exposure)
    changed_event = changed["game_end"]
    changed_event["exposure"] = {
        "form": "shown_to_defender",
        "shown_to_defender_player_id": "player-c",
        "exposed_cards": list(reversed(changed_event["exposure"]["exposed_cards"])),
    }
    changed_event["claimed_play_level"] = "schwarz"
    changed_event["defender_responses"].reverse()
    changed_event["defender_responses"][0]["form"] = "explicit"
    changed_snapshots = build_historical_decision_snapshots(
        build_historical_game_summary_from_input(changed)
    )
    assert [_decision_state(row) for row in changed_snapshots.snapshots] == [
        _decision_state(row) for row in exposure_snapshots.snapshots
    ]


def test_review_and_external_profile_review_use_only_actual_card_decisions(monkeypatch) -> None:
    monkeypatch.setattr(
        "skat_ai.historical_game_review.recommend_card_by_expected_value",
        stub_expected_value_recommendation,
    )
    data = load_historical_data(EXPOSURE_EXAMPLE_PATH)
    record = build_historical_game_record(data)
    summary = build_historical_game_summary_from_input(data)
    snapshots = build_historical_decision_snapshots(summary)
    statistics = load_opponent_statistics_from_json(
        str(PROJECT_ROOT / "examples" / "historical_opponent_statistics.json")
    )
    bindings = resolve_historical_opponent_profile_bindings(
        record,
        statistics,
        statistics_input_file="examples/historical_opponent_statistics.json",
    )
    review = build_historical_game_review_summary(
        snapshots,
        record,
        sample_count=1,
        base_random_seed=42,
        opponent_profile_bindings=bindings,
    )

    assert snapshots.snapshot_count == 14
    assert review["decision_count"] == 14
    assert len(review["decisions"]) == 14
    assert "declarer_card_exposure" not in json.dumps(review["decisions"])


def test_training_samples_partition_audit_and_information_safety_are_variable() -> None:
    normal = build_historical_input()
    exposure = build_exposure_prefix(completed_trick_count=4, current_trick_card_count=2)
    zero = build_exposure_prefix()
    dataset = build_training_dataset_input(
        build_training_input([normal, exposure, zero], ["train", "validation", "test"])
    )
    training = build_training_dataset_summary(dataset)
    audit = audit_training_dataset_partitions(dataset, "known_opponent")

    assert [record["sample_count"] for record in training["records"]] == [30, 14, 0]
    assert training["feature_generation_version"] == 1
    assert training["target"] == "actual_card_played"
    assert [sample["features"] for sample in training["records"][1]["samples"]] == [
        sample["features"] for sample in training["records"][0]["samples"][:14]
    ]
    serialized_samples = json.dumps(training["records"][1]["samples"])
    for forbidden in (
        "declarer_card_exposure",
        "claimed_play_level",
        "defender_responses",
        "accepting_defender_player_ids",
        "final_settlement_summary",
    ):
        assert forbidden not in serialized_samples
    assert audit.partition_summary["test"]["distinct_player_count"] == 3


def test_zero_play_statistics_and_export_count_one_settlement_authoritative_game() -> None:
    exposure = build_exposure_prefix()
    exposure["played_at"] = "2026-07-10T12:00:00Z"
    dataset = build_training_dataset_input(build_training_input([exposure], ["train"]))
    aggregation = aggregate_historical_opponent_statistics(dataset)
    exported = build_exportable_opponent_statistics_input(aggregation)
    records = {
        record.statistics_record.player_id: record.statistics_record
        for record in aggregation.records
    }

    assert aggregation.source_game_count == 1
    assert all(record.games_played == 1 for record in exported.records)
    assert records["player-b"].exact_counts.solo_games_won == 1
    assert records["player-a"].exact_counts.defender_games_won == 0
    assert records["player-c"].exact_counts.defender_games_won == 0


@pytest.mark.parametrize("loss_kind", ["preexisting", "overbid"])
def test_defender_wins_count_for_both_defenders(loss_kind: str) -> None:
    data = (
        build_exposure_prefix(completed_trick_count=6)
        if loss_kind == "preexisting"
        else build_exposure_prefix()
    )
    if loss_kind == "overbid":
        data["declaration"]["bid_value"] = 49
    data["played_at"] = "2026-07-10T12:00:00Z"
    dataset = build_training_dataset_input(build_training_input([data], ["train"]))
    aggregation = aggregate_historical_opponent_statistics(dataset)
    records = {
        record.statistics_record.player_id: record.statistics_record
        for record in aggregation.records
    }

    assert records["player-b"].exact_counts.solo_games_won == 0
    assert records["player-a"].exact_counts.defender_games_won == 1
    assert records["player-c"].exact_counts.defender_games_won == 1


@pytest.mark.parametrize("target_play_count", [0, 14])
def test_rolling_uses_exposure_as_one_source_and_only_actual_target_plays(
    target_play_count: int,
) -> None:
    source = build_exposure_prefix()
    source["played_at"] = "2026-07-10T12:00:00Z"
    complete_tricks, current_cards = divmod(target_play_count, 3)
    target = build_exposure_prefix(
        completed_trick_count=complete_tricks,
        current_trick_card_count=current_cards,
        exposure_form="shown_to_defender",
        shown_to_defender_player_id="player-c",
        claimed_play_level="schneider",
    )
    target["played_at"] = "2026-07-11T12:00:00Z"
    dataset = build_training_dataset_input(
        build_training_input([source, target], ["train", "validation"])
    )
    result = build_serializable_rolling_opponent_policy_evaluation(
        evaluate_rolling_opponent_policy_predictions(dataset)
    )
    target_summary = result["target_games"][0]

    assert target_summary["as_of_source_game_count"] == 1
    assert target_summary["decision_count"] == target_play_count
    assert len(target_summary["decisions"]) == target_play_count
    assert result["selection"]["target_decision_count"] == target_play_count
    serialized_decisions = json.dumps(target_summary["decisions"])
    assert "exposure" not in serialized_decisions
    assert "accept" not in serialized_decisions


def test_package_version_is_0_9_0() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.9.0"' in pyproject
