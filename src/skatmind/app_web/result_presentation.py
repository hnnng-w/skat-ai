from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from skatmind.api.v1 import ExecutionResultV1
from skatmind.information_set_search_workflow import (
    INFORMATION_SET_SEARCH_EFFECTIVE_METHOD,
)
from skatmind.recommendation_workflow import COMPATIBLE_WORLD_MINIMAX_METHOD

RESULT_SECTION_TITLES_V1 = (
    "Summary",
    "Recommendation",
    "Alternatives",
    "Evidence and limits",
    "Technical details",
)
TEXTUAL_NORMAL_RESULT_STATES_V1 = (
    "complete",
    "partial",
    "timeout",
    "unavailable",
    "final",
    "lot_required",
    "not_assessable",
)

_POSITION_WORKFLOW = "position_analysis"
_HISTORICAL_WORKFLOW = "historical_game"
_NOT_AVAILABLE = "Not available"
_SAFE_LIMITATION_FORBIDDEN_FRAGMENTS = (
    "private",
    "hidden",
    "ownership",
    "world_states",
    "exact_states",
    "fingerprint",
    "input_file",
    "provenance",
)


def _require_text(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be non-empty text.")


@dataclass(frozen=True, slots=True)
class ResultDetailV1:
    label: str
    value: str

    def __post_init__(self) -> None:
        _require_text(self.label, "Result detail label")
        _require_text(self.value, "Result detail value")


@dataclass(frozen=True, slots=True)
class ResultTableV1:
    caption: str
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        _require_text(self.caption, "Result table caption")
        columns = tuple(self.columns)
        rows = tuple(tuple(row) for row in self.rows)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "rows", rows)
        if not columns or any(type(column) is not str or not column for column in columns):
            raise ValueError("Result table columns must be non-empty text.")
        if any(len(row) != len(columns) for row in rows):
            raise ValueError("Every Result table row must match the column count.")
        if any(type(cell) is not str or not cell for row in rows for cell in row):
            raise ValueError("Result table cells must be non-empty text.")


@dataclass(frozen=True, slots=True)
class ResultSectionV1:
    title: str
    paragraphs: tuple[str, ...] = ()
    details: tuple[ResultDetailV1, ...] = ()
    items: tuple[str, ...] = ()
    tables: tuple[ResultTableV1, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.title, "Result section title")
        paragraphs = tuple(self.paragraphs)
        details = tuple(self.details)
        items = tuple(self.items)
        tables = tuple(self.tables)
        object.__setattr__(self, "paragraphs", paragraphs)
        object.__setattr__(self, "details", details)
        object.__setattr__(self, "items", items)
        object.__setattr__(self, "tables", tables)
        if any(type(value) is not str or not value for value in (*paragraphs, *items)):
            raise ValueError("Result section text must be non-empty.")
        if any(type(detail) is not ResultDetailV1 for detail in details):
            raise ValueError("Result section details must be exact Result details.")
        if any(type(table) is not ResultTableV1 for table in tables):
            raise ValueError("Result section tables must be exact Result tables.")


@dataclass(frozen=True, slots=True)
class BrowserSafeResultPresentationV1:
    workflow: str
    sections: tuple[ResultSectionV1, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.workflow not in {_POSITION_WORKFLOW, _HISTORICAL_WORKFLOW}:
            raise ValueError("Result presentation workflow is not supported.")
        sections = tuple(self.sections)
        warnings = tuple(self.warnings)
        object.__setattr__(self, "sections", sections)
        object.__setattr__(self, "warnings", warnings)
        if any(type(section) is not ResultSectionV1 for section in sections):
            raise ValueError("sections must contain exact Result sections.")
        if tuple(section.title for section in sections) != RESULT_SECTION_TITLES_V1:
            raise ValueError("Result sections must use the exact canonical order.")
        if any(type(warning) is not str or not warning for warning in warnings):
            raise ValueError("warnings must contain non-empty text.")


def _object(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _objects(value: object) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, (tuple, list)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _values(value: object) -> tuple[object, ...]:
    if isinstance(value, (tuple, list)):
        return tuple(value)
    return ()


def _text(value: object) -> str:
    if value is None:
        return _NOT_AVAILABLE
    if type(value) is bool:
        return "Yes" if value else "No"
    if type(value) is float:
        return f"{value:.6g}"
    if type(value) in {str, int}:
        rendered = str(value)
        return rendered if rendered else _NOT_AVAILABLE
    return _NOT_AVAILABLE


def _percentage(value: object) -> str:
    if type(value) not in {int, float}:
        return _NOT_AVAILABLE
    return f"{float(value) * 100:.2f}%"


def _cards(value: object) -> str:
    cards = tuple(_text(card) for card in _values(value))
    return ", ".join(cards) if cards else "None"


def _detail(label: str, value: object) -> ResultDetailV1:
    return ResultDetailV1(label=label, value=_text(value))


def _optional_detail(
    details: list[ResultDetailV1],
    label: str,
    source: Mapping[str, object],
    key: str,
) -> None:
    if key in source:
        details.append(_detail(label, source[key]))


def _analysis_candidate_table(rows: object) -> ResultTableV1 | None:
    candidates = _objects(rows)
    if not candidates:
        return None
    return ResultTableV1(
        caption="Card comparisons in public Result order",
        columns=(
            "Card",
            "Recommended",
            "Win rate",
            "Expected point swing",
            "Average trick points",
        ),
        rows=tuple(
            (
                _text(candidate.get("card")),
                _text(candidate.get("is_recommended")),
                _percentage(candidate.get("win_rate")),
                _text(candidate.get("expected_point_swing")),
                _text(candidate.get("average_trick_points")),
            )
            for candidate in candidates
        ),
    )


def _search_candidate_table(rows: object) -> ResultTableV1 | None:
    candidates = _objects(rows)
    if not candidates:
        return None
    return ResultTableV1(
        caption="Search Candidate comparisons in public Result order",
        columns=(
            "Card",
            "Rank",
            "Recommended",
            "Completed worlds",
            "Contract success rate",
            "Mean side game score",
            "Mean card-point margin",
        ),
        rows=tuple(
            (
                _text(candidate.get("card")),
                _text(candidate.get("rank")),
                _text(candidate.get("is_recommended")),
                _text(candidate.get("completed_world_count")),
                _percentage(candidate.get("local_contract_success_rate")),
                _text(candidate.get("mean_local_side_game_score")),
                _text(candidate.get("mean_local_side_card_point_margin")),
            )
            for candidate in candidates
        ),
    )


def _position_alternatives(document: Mapping[str, object]) -> ResultSectionV1:
    method = _object(document.get("recommendation_method_summary"))
    effective_method = method.get("effective_method")
    information_set = _object(document.get("information_set_search_result"))
    bounded = _object(document.get("bounded_search_result"))
    if effective_method == INFORMATION_SET_SEARCH_EFFECTIVE_METHOD or (
        not method and information_set
    ):
        table = _search_candidate_table(information_set.get("candidate_results"))
    elif effective_method == COMPATIBLE_WORLD_MINIMAX_METHOD or (not method and bounded):
        table = _search_candidate_table(bounded.get("candidate_results"))
    else:
        table = _analysis_candidate_table(document.get("analysis_report"))
    if table is None:
        return ResultSectionV1(
            title="Alternatives",
            paragraphs=("No Candidate comparison is available for this Result.",),
        )
    return ResultSectionV1(title="Alternatives", tables=(table,))


def _search_evidence(
    document: Mapping[str, object],
) -> tuple[list[ResultDetailV1], list[ResultDetailV1]]:
    method = _object(document.get("recommendation_method_summary"))
    information_set = _object(document.get("information_set_search_result"))
    bounded = _object(document.get("bounded_search_result"))
    search = information_set or bounded
    consumed = _object(search.get("consumed_budget"))
    requested = _object(search.get("requested_budget"))

    evidence: list[ResultDetailV1] = []
    technical: list[ResultDetailV1] = []
    for label, key in (
        ("Requested method", "requested_method"),
        ("Effective method", "effective_method"),
        ("Fallback used", "fallback_used"),
        ("Fallback method", "fallback_method"),
    ):
        _optional_detail(evidence, label, method, key)
    for label, key in (
        ("Search status", "status"),
        ("Stop reason", "stop_reason"),
        ("World coverage", "world_coverage"),
        ("Compatible world count", "compatible_world_count"),
    ):
        _optional_detail(evidence, label, search, key)
    for label, key in (
        ("Selected worlds", "selected_world_count"),
        ("Completed worlds", "completed_world_count"),
        ("Sampled worlds", "sampled_world_count"),
        ("Unique sampled worlds", "unique_sampled_world_count"),
    ):
        _optional_detail(evidence, label, consumed, key)

    for label, key in (
        ("Search method", "search_method"),
        ("Solution claim", "solution_claim"),
        ("Policy claim", "policy_claim"),
        ("Policy consistency", "policy_consistency"),
        ("Controlled policy decisions", "controlled_policy_decision_count"),
    ):
        _optional_detail(technical, label, search, key)
    for label, key in (
        ("Maximum remaining Tricks", "max_remaining_tricks"),
        ("Maximum depth plies", "max_depth_plies"),
        ("Maximum selected worlds", "max_selected_worlds"),
        ("Maximum sampled worlds", "max_sampled_worlds"),
        ("Minimum comparable worlds", "minimum_comparable_worlds"),
        ("Timeout milliseconds", "wall_clock_timeout_ms"),
    ):
        _optional_detail(technical, label, requested, key)
    for label, key in (
        ("Depth reached", "depth_reached"),
        ("Nodes expanded", "nodes_expanded"),
        ("State nodes evaluated", "state_nodes_evaluated"),
        ("Information sets evaluated", "information_sets_evaluated"),
    ):
        _optional_detail(technical, label, consumed, key)
    return evidence, technical


def _fixed_policy_details(document: Mapping[str, object]) -> list[ResultDetailV1]:
    details: list[ResultDetailV1] = []
    for prefix, key in (
        ("General", "opponent_policy_settings"),
        ("Left", "left_opponent_policy_settings"),
        ("Right", "right_opponent_policy_settings"),
    ):
        policy = _object(document.get(key))
        if policy:
            details.append(
                ResultDetailV1(
                    label=f"{prefix} fixed policy",
                    value=(
                        f"lead {_text(policy.get('opponent_lead_policy'))}; "
                        f"response {_text(policy.get('opponent_response_policy'))}"
                    ),
                )
            )
    return details


def _build_position_presentation(
    execution: ExecutionResultV1,
    document: Mapping[str, object],
) -> BrowserSafeResultPresentationV1:
    position = _object(document.get("position"))
    declaration = _object(document.get("game_declaration"))
    information = _object(document.get("information_policy_summary"))
    settings = _object(document.get("settings"))
    recommendation = _object(document.get("recommendation"))
    review = _object(document.get("post_game_review_summary"))

    summary_details = [
        _detail("Analysis mode", information.get("analysis_mode")),
        _detail("Contract", declaration.get("game_type", position.get("game_type"))),
        _detail("Player role", position.get("player_role")),
        _detail("Player seat", position.get("player_position")),
        _detail("Next player", position.get("next_player")),
        _detail("Current Trick", _cards(position.get("current_trick"))),
        _detail("Completed Tricks", len(_objects(position.get("completed_tricks")))),
        _detail("Legal Cards", _cards(document.get("legal_cards"))),
    ]
    for label, key in (
        ("Declarer points", "declarer_points"),
        ("Defender points", "defender_points"),
    ):
        _optional_detail(summary_details, label, position, key)

    method = _object(document.get("recommendation_method_summary"))
    search_result = _object(document.get("information_set_search_result")) or _object(
        document.get("bounded_search_result")
    )
    recommendation_details = [
        _detail("Recommended Card", recommendation.get("card")),
        _detail(
            "Method",
            method.get(
                "effective_method",
                settings.get("recommendation_method", "immediate_expected_value"),
            ),
        ),
    ]
    _optional_detail(recommendation_details, "Fallback used", method, "fallback_used")
    _optional_detail(recommendation_details, "Actual Card", review, "actual_card_played")
    _optional_detail(recommendation_details, "Decision quality", review, "decision_quality")
    recommendation_paragraph = recommendation.get("reason")
    if type(recommendation_paragraph) is not str or not recommendation_paragraph:
        recommendation_paragraph = "No Card recommendation is available from this Result."

    evidence_details, technical_details = _search_evidence(document)
    _optional_detail(evidence_details, "Samples", settings, "sample_count")
    _optional_detail(evidence_details, "Information cutoff mode", information, "analysis_mode")
    _optional_detail(evidence_details, "Skat visibility", information, "skat_visibility")
    evidence_details.extend(_fixed_policy_details(document))

    for label, key in (
        ("Hand game", "hand_game"),
        ("Ouvert", "ouvert"),
        ("Schneider announced", "schneider_announced"),
        ("Schwarz announced", "schwarz_announced"),
        ("Matadors", "matadors"),
        ("Bid value", "bid_value"),
    ):
        _optional_detail(technical_details, label, declaration, key)
    _optional_detail(technical_details, "Game end reason", information, "game_end_reason")
    multi_step = _object(document.get("multi_step_result"))
    comparison = _object(document.get("policy_comparison_result"))
    for label, source, key in (
        ("Multi-Step requested Decisions", multi_step, "requested_step_count"),
        ("Multi-Step simulated Decisions", multi_step, "steps_simulated"),
        ("Multi-Step stop reason", multi_step, "stop_reason"),
        ("Multi-Step Card Policy", multi_step, "card_selection_policy"),
        ("Policy Comparison requested Decisions", comparison, "requested_step_count"),
    ):
        _optional_detail(technical_details, label, source, key)
    recommended_policy = _object(comparison.get("recommended_policy"))
    _optional_detail(
        technical_details,
        "Recommended comparison Policy",
        recommended_policy,
        "policy",
    )
    if execution.artifacts:
        technical_details.append(
            ResultDetailV1(
                label="Public artifacts",
                value=", ".join(artifact.name for artifact in execution.artifacts),
            )
        )

    limits = [
        "The analysis is bounded by its selected method, samples, and public budget.",
        "Only information available at the analysis cutoff is used.",
        "Opponent behavior follows the fixed public policy settings used for this analysis.",
        "Search is not a perfect-play claim.",
        "Compatible-world counts and samples are evidence coverage, not calibrated probability.",
    ]
    if review.get("actual_card_played") is not None:
        limits.append("The actual Card is observed retrospective evidence, not ground truth.")

    return BrowserSafeResultPresentationV1(
        workflow=_POSITION_WORKFLOW,
        warnings=execution.result.warnings,
        sections=(
            ResultSectionV1(
                title="Summary",
                details=(
                    _detail("Result status", search_result.get("status", "complete")),
                    *summary_details,
                ),
            ),
            ResultSectionV1(
                title="Recommendation",
                paragraphs=(recommendation_paragraph,),
                details=tuple(recommendation_details),
            ),
            _position_alternatives(document),
            ResultSectionV1(
                title="Evidence and limits",
                details=tuple(evidence_details),
                items=tuple(limits),
            ),
            ResultSectionV1(
                title="Technical details",
                details=tuple(technical_details),
            ),
        ),
    )


def _immediate_review_table(review: Mapping[str, object]) -> ResultTableV1 | None:
    decisions = _objects(review.get("decisions"))
    if not decisions:
        return None
    rows = []
    for decision in decisions:
        recommendation = _object(decision.get("recommendation"))
        comparison = _object(decision.get("post_game_review_summary"))
        rows.append(
            (
                _text(decision.get("decision_index")),
                _text(decision.get("trick_number")),
                _text(decision.get("play_index")),
                _text(decision.get("acting_player_id")),
                _text(decision.get("actual_card_played")),
                _text(recommendation.get("card")),
                _text(comparison.get("decision_quality", decision.get("status"))),
            )
        )
    return ResultTableV1(
        caption="Immediate review comparisons in chronological Result order",
        columns=("Decision", "Trick", "Play", "Player", "Actual", "Recommended", "Review"),
        rows=tuple(rows),
    )


def _search_review_table(review: Mapping[str, object]) -> ResultTableV1 | None:
    decisions = _objects(review.get("decisions"))
    if not decisions:
        return None
    rows = []
    for decision in decisions:
        search = _object(decision.get("bounded_search_result"))
        immediate = _object(decision.get("immediate_baseline"))
        immediate_recommendation = _object(immediate.get("recommendation"))
        comparison = _object(decision.get("search_actual_card_comparison"))
        rows.append(
            (
                _text(decision.get("decision_index")),
                _text(decision.get("trick_number")),
                _text(decision.get("play_index")),
                _text(decision.get("actual_card")),
                _text(search.get("recommended_card")),
                _text(immediate_recommendation.get("card")),
                _text(search.get("status")),
                _text(comparison.get("is_available")),
            )
        )
    return ResultTableV1(
        caption="Bounded Search review comparisons in chronological Result order",
        columns=(
            "Decision",
            "Trick",
            "Play",
            "Actual",
            "Search",
            "Immediate",
            "Status",
            "Comparison available",
        ),
        rows=tuple(rows),
    )


def _information_set_review_table(review: Mapping[str, object]) -> ResultTableV1 | None:
    decisions = _objects(review.get("decisions"))
    if not decisions:
        return None
    rows = []
    for decision in decisions:
        search = _object(decision.get("information_set_search_result"))
        pimc = _object(decision.get("same_selection_pimc_result"))
        immediate = _object(decision.get("immediate_baseline"))
        comparison = _object(decision.get("comparison"))
        rows.append(
            (
                _text(decision.get("decision_index")),
                _text(decision.get("trick_number")),
                _text(decision.get("play_index")),
                _text(decision.get("actual_card")),
                _text(search.get("recommended_card")),
                _text(pimc.get("recommended_card")),
                _text(immediate.get("recommended_card")),
                _text(search.get("status", "not_assessable")),
                _text(comparison.get("comparison_status")),
            )
        )
    return ResultTableV1(
        caption="Information-set review comparisons in chronological Result order",
        columns=(
            "Decision",
            "Trick",
            "Play",
            "Actual",
            "Information-set",
            "PIMC",
            "Immediate",
            "Status",
            "Comparison",
        ),
        rows=tuple(rows),
    )


def _historical_alternatives(summary: Mapping[str, object]) -> ResultSectionV1:
    immediate = _object(summary.get("historical_game_review_summary"))
    search = _object(summary.get("historical_search_review_summary"))
    information_set = _object(summary.get("historical_information_set_search_review_summary"))
    tables = tuple(
        table
        for table in (
            _immediate_review_table(immediate),
            _search_review_table(search),
            _information_set_review_table(information_set),
        )
        if table is not None
    )
    if not tables:
        return ResultSectionV1(
            title="Alternatives",
            paragraphs=("No chronological Decision comparison was requested.",),
        )
    return ResultSectionV1(title="Alternatives", tables=tables)


def _status_count_details(
    details: list[ResultDetailV1],
    prefix: str,
    counts: Mapping[str, object],
) -> None:
    for status in ("complete", "partial", "timeout", "unavailable", "not_available"):
        if status in counts:
            details.append(_detail(f"{prefix} {status}", counts[status]))


def _safe_public_limitations(value: object, prefix: str) -> tuple[str, ...]:
    limitations = []
    for item in _values(value):
        if type(item) is not str or not item:
            continue
        lowered = item.lower()
        if any(fragment in lowered for fragment in _SAFE_LIMITATION_FORBIDDEN_FRAGMENTS):
            continue
        limitations.append(f"{prefix}: {item}")
    return tuple(limitations)


def _historical_evidence(
    summary: Mapping[str, object],
) -> tuple[list[ResultDetailV1], list[str]]:
    immediate = _object(summary.get("historical_game_review_summary"))
    search = _object(summary.get("historical_search_review_summary"))
    information_set = _object(summary.get("historical_information_set_search_review_summary"))
    replay = _object(summary.get("historical_replay_coaching_summary"))
    information_coaching = _object(
        summary.get("historical_information_set_replay_coaching_summary")
    )
    tactical = _object(summary.get("historical_tactical_motif_review_summary"))
    ending = _object(summary.get("historical_game_end_summary"))
    exact_proof = _object(ending.get("exact_proof"))

    details: list[ResultDetailV1] = []
    for label, source, key in (
        ("Immediate Decisions", immediate, "decision_count"),
        ("Immediate reviewed Decisions", immediate, "reviewed_decision_count"),
        ("Immediate unavailable Decisions", immediate, "unavailable_decision_count"),
        (
            "Information-set Decisions",
            information_set,
            "decision_count",
        ),
        ("Tactical observations", tactical, "observation_count"),
        ("Tactical motif occurrences", tactical, "motif_occurrence_count"),
    ):
        _optional_detail(details, label, source, key)
    search_counts = _object(search.get("decision_counts"))
    _optional_detail(details, "Bounded Search Decisions", search_counts, "decision_count")
    _status_count_details(details, "Bounded Search", _object(search.get("status_counts")))
    _status_count_details(
        details,
        "Information-set Search",
        _object(information_set.get("status_counts")),
    )
    coverage = _object(search.get("coverage"))
    for label, key in (
        ("Exact coverage Decisions", "exact_coverage_decision_count"),
        ("Sampled coverage Decisions", "sampled_coverage_decision_count"),
        ("No coverage Decisions", "no_coverage_decision_count"),
    ):
        _optional_detail(details, label, coverage, key)
    for label, key in (
        ("Selected worlds", "selected_world_count_total"),
        ("Sampled worlds", "sampled_world_count_total"),
    ):
        _optional_detail(details, label, information_set, key)
    _optional_detail(details, "Claim proof status", exact_proof, "status")
    _optional_detail(
        details,
        "Claim maximum unresolved Tricks",
        ending,
        "proof_maximum_unresolved_tricks",
    )

    limits = [
        "Historical comparisons use only information available at each Decision cutoff.",
        "Search is bounded and is not a perfect-play claim.",
        "Opponent behavior follows the fixed public policy settings used for each review.",
        "Compatible-world counts and samples are evidence coverage, not calibrated probability.",
        "Observed Cards are retrospective evidence, not ground truth.",
    ]
    if replay:
        limits.append(
            "Replay Coaching is bounded to retained review evidence and makes no causal claim."
        )
        limits.extend(_safe_public_limitations(replay.get("limitations"), "Replay Coaching"))
    if information_coaching:
        limits.append("Information-set Coaching uses complete Candidate evidence without fallback.")
        limits.extend(
            _safe_public_limitations(
                information_coaching.get("limitations"),
                "Information-set Coaching",
            )
        )
    if tactical:
        limits.append(
            "Tactical motifs are structural observations, not quality, intent, signaling, "
            "communication, or causal claims."
        )
        limits.extend(_safe_public_limitations(tactical.get("limitations"), "Tactical Review"))
    if ending.get("kind") == "party_wide_all_remaining_tricks_claim":
        limits.append(
            "Claim adjudication is limited to the bounded party-wide all-remaining-Tricks form."
        )
    return details, limits


def _historical_technical_details(
    execution: ExecutionResultV1,
    summary: Mapping[str, object],
) -> list[ResultDetailV1]:
    game_result = _object(summary.get("game_result_summary"))
    game_value = _object(summary.get("game_value_summary"))
    overbid = _object(summary.get("overbid_summary"))
    settlement = _object(summary.get("final_settlement_summary"))
    ending = _object(summary.get("historical_game_end_summary"))
    proof = _object(ending.get("exact_proof"))
    details = [_detail("Public API contract version", execution.api_contract_version)]
    record = _object(summary.get("record"))
    player_ids = tuple(
        player.get("player_id")
        for player in _objects(record.get("players"))
        if type(player.get("player_id")) is str
    )
    if player_ids:
        details.append(_detail("Player IDs", ", ".join(player_ids)))
    for label, source, key in (
        ("Historical schema version", summary, "schema_version"),
        ("Played at", summary, "played_at"),
        ("Result status", game_result, "status"),
        ("Schneider status", summary, "schneider_status"),
        ("Schwarz status", summary, "schwarz_status"),
        ("Game value", game_value, "game_value"),
        ("Effective game value", settlement, "effective_game_value"),
        ("Overbid required game value", overbid, "required_game_value"),
        ("Settlement complete", settlement, "is_complete"),
        ("Settlement score", settlement, "settlement_score"),
        ("Claim proof states evaluated", proof, "evaluated_state_count"),
        ("Claim proof terminal states", proof, "terminal_state_count"),
    ):
        _optional_detail(details, label, source, key)
    for label, key, method_key in (
        ("Immediate review method", "historical_game_review_summary", "analysis_method"),
        ("Bounded Search review method", "historical_search_review_summary", "analysis_method"),
        (
            "Information-set review method",
            "historical_information_set_search_review_summary",
            "review_method",
        ),
        ("Replay Coaching method", "historical_replay_coaching_summary", "report_method"),
        (
            "Information-set Coaching method",
            "historical_information_set_replay_coaching_summary",
            "report_method",
        ),
        ("Tactical Review method", "historical_tactical_motif_review_summary", "review_method"),
    ):
        source = _object(summary.get(key))
        _optional_detail(details, label, source, method_key)
    if execution.artifacts:
        details.append(
            ResultDetailV1(
                label="Public artifacts",
                value=", ".join(artifact.name for artifact in execution.artifacts),
            )
        )
    return details


def _build_historical_presentation(
    execution: ExecutionResultV1,
    document: Mapping[str, object],
) -> BrowserSafeResultPresentationV1:
    summary = _object(document.get("historical_game_summary"))
    record = _object(summary.get("record"))
    declaration = _object(record.get("declaration"))
    game_result = _object(summary.get("game_result_summary"))
    overbid = _object(summary.get("overbid_summary"))
    settlement = _object(summary.get("final_settlement_summary"))
    ending = _object(summary.get("historical_game_end_summary"))
    end_reason = record.get(
        "game_end_reason",
        ending.get("kind", game_result.get("game_end_reason")),
    )
    players = _objects(record.get("players"))
    player_labels: dict[str, str] = {}
    visible_players = []
    for player in players:
        player_id = player.get("player_id")
        label = player.get("player_label")
        seat = player.get("seat")
        display = (
            label
            if type(label) is str and label
            else seat.replace("_", " ").title()
            if type(seat) is str and seat
            else "Unlabeled Player"
        )
        visible_players.append(display)
        if type(player_id) is str:
            player_labels[player_id] = display
    declarer_id = record.get("declarer_player_id")
    declarer = player_labels.get(declarer_id, "Unlabeled Player")

    summary_details = [
        _detail("Game", summary.get("game_id", record.get("game_id"))),
        _detail("Status", summary.get("status")),
        _detail("Players", ", ".join(visible_players) if visible_players else None),
        _detail("Declarer", declarer),
        _detail("Declaration", declaration.get("game_type")),
        _detail("Game end", end_reason),
        _detail("Completed Tricks", len(_objects(summary.get("derived_tricks")))),
        _detail("Declarer points", summary.get("declarer_points")),
        _detail("Defender points", summary.get("defender_points")),
        _detail("Winner", summary.get("winner", game_result.get("winner"))),
        _detail("Result", game_result.get("status", game_result.get("winner"))),
        _detail("Overbid", overbid.get("status")),
        _detail("Settlement", settlement.get("settlement_score")),
    ]
    for label, key in (
        ("Hand game", "hand_game"),
        ("Ouvert", "ouvert"),
        ("Bid value", "bid_value"),
        ("Matadors", "matadors"),
    ):
        _optional_detail(summary_details, label, declaration, key)
    for label, source, key in (
        (
            "Immediate review Decisions",
            _object(summary.get("historical_game_review_summary")),
            "decision_count",
        ),
        (
            "Bounded Search review Decisions",
            _object(
                _object(summary.get("historical_search_review_summary")).get("decision_counts")
            ),
            "decision_count",
        ),
        (
            "Information-set review Decisions",
            _object(summary.get("historical_information_set_search_review_summary")),
            "decision_count",
        ),
    ):
        _optional_detail(summary_details, label, source, key)

    evidence_details, limits = _historical_evidence(summary)
    technical_details = _historical_technical_details(execution, summary)
    immediate_review = _object(summary.get("historical_game_review_summary"))
    search_review = _object(summary.get("historical_search_review_summary"))
    information_review = _object(
        summary.get("historical_information_set_search_review_summary")
    )
    recommendation_details: list[ResultDetailV1] = []
    for label, source, key in (
        ("Immediate assessed Decisions", immediate_review, "reviewed_decision_count"),
        ("Immediate unavailable Decisions", immediate_review, "unavailable_decision_count"),
        (
            "Bounded Search Decisions",
            _object(search_review.get("decision_counts")),
            "decision_count",
        ),
        ("Information-set Decisions", information_review, "decision_count"),
    ):
        _optional_detail(recommendation_details, label, source, key)
    recommendation_paragraphs = [
        "A completed game has no single whole-game Card recommendation."
    ]
    if recommendation_details:
        recommendation_paragraphs.append(
            "Decision reviews remain bounded to their retained public evidence and do not "
            "establish one globally optimal game policy."
        )
    return BrowserSafeResultPresentationV1(
        workflow=_HISTORICAL_WORKFLOW,
        warnings=execution.result.warnings,
        sections=(
            ResultSectionV1(title="Summary", details=tuple(summary_details)),
            ResultSectionV1(
                title="Recommendation",
                paragraphs=tuple(recommendation_paragraphs),
                details=tuple(recommendation_details),
            ),
            _historical_alternatives(summary),
            ResultSectionV1(
                title="Evidence and limits",
                details=tuple(evidence_details),
                items=tuple(limits),
            ),
            ResultSectionV1(
                title="Technical details",
                details=tuple(technical_details),
            ),
        ),
    )


def build_result_presentation_v1(
    execution: ExecutionResultV1,
) -> BrowserSafeResultPresentationV1:
    """Projects one retained public Result into minimized browser-safe values."""

    if type(execution) is not ExecutionResultV1:
        raise ValueError("execution must be an exact ExecutionResultV1.")
    workflow = execution.result.workflow.value
    document = execution.result.document
    if workflow == _POSITION_WORKFLOW:
        return _build_position_presentation(execution, document)
    if workflow == _HISTORICAL_WORKFLOW:
        return _build_historical_presentation(execution, document)
    raise ValueError("Only Position Analysis and Historical Game Results can be presented.")
