import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource
from test_historical_game import build_historical_input
from test_historical_game_event_chain import TERMINAL_BUILDERS, add_continuation
from test_replay_coaching_contracts import (
    _historical_fake_immediate,
    _historical_fake_search,
)
from test_replay_coaching_prioritization import (
    _historical_reverse_search,
    _zero_decision_data,
)

from skat_ai.historical_decision_snapshot import build_historical_decision_snapshots
from skat_ai.historical_game import (
    build_historical_game_record,
    build_historical_game_summary,
)
from skat_ai.replay_coaching_report import (
    build_historical_replay_coaching_public_summaries,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "schemas" / "historical_replay_coaching.schema.json"
BOUNDED_SEARCH_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "bounded_search_result.schema.json"
HISTORICAL_SEARCH_REVIEW_SCHEMA_PATH = (
    PROJECT_ROOT / "schemas" / "historical_search_review.schema.json"
)


def _load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


SCHEMA = _load_schema(SCHEMA_PATH)
BOUNDED_SEARCH_SCHEMA = _load_schema(BOUNDED_SEARCH_SCHEMA_PATH)
HISTORICAL_SEARCH_REVIEW_SCHEMA = _load_schema(
    HISTORICAL_SEARCH_REVIEW_SCHEMA_PATH
)


def _reject_remote_retrieval(uri: str):
    raise AssertionError(f"Unexpected non-local schema retrieval: {uri}")


SCHEMA_REGISTRY = Registry(retrieve=_reject_remote_retrieval).with_resources(
    [
        (
            BOUNDED_SEARCH_SCHEMA["$id"],
            Resource.from_contents(BOUNDED_SEARCH_SCHEMA),
        ),
        (
            HISTORICAL_SEARCH_REVIEW_SCHEMA["$id"],
            Resource.from_contents(HISTORICAL_SEARCH_REVIEW_SCHEMA),
        ),
    ]
)
VALIDATOR = Draft202012Validator(
    SCHEMA,
    registry=SCHEMA_REGISTRY,
    format_checker=FormatChecker(),
)


def _serialized_report(monkeypatch, data: dict, *, search=_historical_fake_search) -> dict:
    monkeypatch.setattr(
        "skat_ai.historical_search_review.solve_compatible_world_minimax",
        search,
    )
    monkeypatch.setattr(
        "skat_ai.historical_search_review.recommend_card_by_expected_value",
        _historical_fake_immediate,
    )
    record = build_historical_game_record(data)
    snapshots = build_historical_decision_snapshots(
        build_historical_game_summary(record)
    )
    public = build_historical_replay_coaching_public_summaries(
        snapshots,
        record,
        base_search_seed=41,
        immediate_sample_count=1,
    )
    return public["historical_replay_coaching_summary"]


def _contract_data(game_type: str, hand_game: bool, ouvert: bool) -> dict:
    data = _zero_decision_data()
    declaration = {
        "game_type": game_type,
        "hand_game": hand_game,
        "ouvert": ouvert,
        "bid_value": 18,
    }
    if game_type != "null":
        declaration.update(
            {
                "schneider_announced": False,
                "schwarz_announced": False,
                "matadors": 1,
            }
        )
    data["declaration"] = declaration
    if hand_game:
        data["discarded_cards"] = []
    return data


@pytest.fixture
def normal_report(monkeypatch) -> dict:
    return _serialized_report(monkeypatch, build_historical_input())


def test_schema_is_valid_draft_2020_12_with_stable_public_id() -> None:
    Draft202012Validator.check_schema(SCHEMA)

    assert SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert SCHEMA["$id"] == (
        "https://example.local/skat-ai/historical_replay_coaching.schema.json"
    )


def test_schema_accepts_representative_serialized_public_report(
    normal_report: dict,
) -> None:
    VALIDATOR.validate(normal_report)

    assert len(normal_report["game_context"]["players"]) == 3
    assert len(normal_report["player_summaries"]) == 3
    assert len(normal_report["role_summaries"]) == 2
    assert len(normal_report["phase_summaries"]) == 3
    assert len(normal_report["contract_summaries"]) == 1


def test_schema_accepts_zero_decision_report(monkeypatch) -> None:
    report = _serialized_report(monkeypatch, _zero_decision_data())

    VALIDATOR.validate(report)
    assert report["decision_assessments"] == []
    assert report["prioritization"]["key_decisions"] == []
    assert report["guidance"]["decision_recommendations"] == []
    assert report["guidance"]["pattern_recommendations"] == []


@pytest.mark.parametrize(
    ("game_type", "hand_game", "ouvert"),
    [
        ("clubs", False, False),
        ("spades", False, False),
        ("hearts", False, False),
        ("diamonds", False, False),
        ("grand", False, False),
        ("null", False, False),
        ("null", True, False),
        ("null", False, True),
        ("null", True, True),
    ],
)
def test_schema_accepts_suit_grand_and_all_null_variants(
    monkeypatch,
    game_type: str,
    hand_game: bool,
    ouvert: bool,
) -> None:
    report = _serialized_report(
        monkeypatch,
        _contract_data(game_type, hand_game, ouvert),
    )

    VALIDATOR.validate(report)
    assert report["game_context"]["game_type"] == game_type
    assert report["contract_summaries"][0]["scope_value"] == game_type


@pytest.mark.parametrize("end_reason", ["normal_completion", *TERMINAL_BUILDERS])
def test_schema_accepts_every_supported_normal_and_shortened_outcome(
    monkeypatch,
    end_reason: str,
) -> None:
    data = (
        build_historical_input()
        if end_reason == "normal_completion"
        else TERMINAL_BUILDERS[end_reason]()
    )
    report = _serialized_report(monkeypatch, data)

    VALIDATOR.validate(report)
    assert report["outcome_context"]["game_end_reason"] == end_reason


@pytest.mark.parametrize(
    "continuation_kind",
    (
        "defender_open_play_continuation",
        "declarer_card_exposure_continuation",
    ),
)
def test_schema_accepts_both_supported_continuation_outcomes(
    monkeypatch,
    continuation_kind: str,
) -> None:
    data = add_continuation(
        TERMINAL_BUILDERS["defender_concession"](),
        continuation_kind,
    )
    report = _serialized_report(monkeypatch, data)

    VALIDATOR.validate(report)
    events = report["outcome_context"]["historical_game_events_summary"]
    assert events["events"][0]["kind"] == continuation_kind


@pytest.mark.parametrize(
    ("location", "property_name", "value"),
    [
        ((), "initial_hands", {"player-a": ["CA"]}),
        (("game_context",), "skat", ["CA", "SA"]),
        (("game_context", "players", 0), "initial_hand", ["CA"]),
        (("game_context", "declaration"), "discarded_cards", ["CA", "SA"]),
        (("outcome_context", "game_result_summary", "thresholds"), "private_skat", []),
        (("decision_assessments", 0, "decision_time_evidence"), "ownership", {}),
        (
            (
                "decision_assessments",
                0,
                "decision_time_evidence",
                "bounded_search_result",
            ),
            "selected_worlds",
            [],
        ),
        (("coverage_summary", "assessment_status_counts", 0), "unknown_count", 0),
        (("player_summaries", 0), "rating", 1000),
    ],
)
def test_schema_recursively_rejects_unknown_and_private_properties(
    normal_report: dict,
    location: tuple[str | int, ...],
    property_name: str,
    value: object,
) -> None:
    changed = copy.deepcopy(normal_report)
    target = changed
    for segment in location:
        target = target[segment]
    target[property_name] = value

    with pytest.raises(ValidationError):
        VALIDATOR.validate(changed)


@pytest.mark.parametrize(
    ("field", "operation"),
    [
        ("player_summaries", "remove"),
        ("role_summaries", "append"),
        ("phase_summaries", "remove"),
        ("contract_summaries", "append"),
    ],
)
def test_schema_enforces_exact_scope_summary_cardinalities(
    normal_report: dict,
    field: str,
    operation: str,
) -> None:
    changed = copy.deepcopy(normal_report)
    if operation == "remove":
        changed[field].pop()
    else:
        changed[field].append(copy.deepcopy(changed[field][-1]))

    with pytest.raises(ValidationError):
        VALIDATOR.validate(changed)


def test_schema_enforces_exact_player_context_cardinality(normal_report: dict) -> None:
    changed = copy.deepcopy(normal_report)
    changed["game_context"]["players"].pop()

    with pytest.raises(ValidationError):
        VALIDATOR.validate(changed)


def test_schema_enforces_decision_key_and_recommendation_maxima(monkeypatch) -> None:
    report = _serialized_report(
        monkeypatch,
        build_historical_input(),
        search=_historical_reverse_search,
    )
    VALIDATOR.validate(report)
    assert len(report["prioritization"]["key_decisions"]) == 5
    assert len(report["guidance"]["decision_recommendations"]) == 5
    assert report["guidance"]["pattern_recommendations"]

    mutations = (
        ("decision_assessments", report["decision_assessments"][0]),
        ("key_decisions", report["prioritization"]["key_decisions"][0]),
        (
            "decision_recommendations",
            report["guidance"]["decision_recommendations"][0],
        ),
        (
            "pattern_recommendations",
            report["guidance"]["pattern_recommendations"][0],
        ),
    )
    for field, item in mutations:
        changed = copy.deepcopy(report)
        if field == "decision_assessments":
            changed[field].append(copy.deepcopy(item))
        elif field == "key_decisions":
            changed["prioritization"][field].append(copy.deepcopy(item))
        else:
            target = changed["guidance"][field]
            while len(target) <= 5:
                target.append(copy.deepcopy(item))
        with pytest.raises(ValidationError):
            VALIDATOR.validate(changed)
