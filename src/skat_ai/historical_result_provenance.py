from __future__ import annotations

from collections.abc import Mapping

from skat_ai.application.provenance import ApplicationProvenanceAttachment
from skat_ai.errors import SkatAIInformationPolicyError
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceLedger,
    parse_json_pointer,
)
from skat_ai.field_provenance_coverage import (
    build_field_provenance_coverage_summary,
    enumerate_json_leaf_paths,
)
from skat_ai.field_provenance_policy import InformationUseContext
from skat_ai.settlement_result_provenance import (
    COMPLETE_RESULT_PROVENANCE_VERSION as COMPLETE_RESULT_PROVENANCE_VERSION,
)
from skat_ai.settlement_result_provenance import (
    build_game_value_result_entry,
    build_overbid_result_entry,
    build_settlement_result_entry,
    leaf_paths_below,
    result_provenance_entry,
    result_source_reference,
)

HISTORICAL_RESULT_KEYS = frozenset(
    {
        "input_file",
        "historical_game_summary",
        "historical_opponent_profile_application_summary",
    }
)

_HISTORICAL_SUMMARY_KEYS = frozenset(
    {
        "schema_version",
        "game_id",
        "played_at",
        "status",
        "record",
        "derived_tricks",
        "incomplete_current_trick",
        "play_prefix_summary",
        "point_accounting",
        "declarer_trick_points",
        "defender_trick_points",
        "skat_points",
        "declarer_points",
        "defender_points",
        "winner",
        "schneider_status",
        "schwarz_status",
        "game_result_summary",
        "game_value_summary",
        "overbid_summary",
        "final_settlement_summary",
        "historical_game_end_summary",
        "historical_game_events_summary",
        "decision_snapshot_summary",
        "historical_game_review_summary",
        "historical_search_review_summary",
        "historical_replay_coaching_summary",
    }
)

_REVIEW_BRANCHES = frozenset(
    {
        "decision_snapshot_summary",
        "historical_game_review_summary",
        "historical_search_review_summary",
        "historical_replay_coaching_summary",
    }
)

_RAW_RESULT_FIELDS = frozenset(
    {
        "declarer_points",
        "defender_points",
        "points_remaining",
        "is_complete",
        "winner",
        "status",
        "raw_schneider_status",
        "raw_schwarz_status",
        "effective_schneider_status",
        "effective_schwarz_status",
        "thresholds",
    }
)

_HISTORICAL_END_RULES = {
    "normal_completion": "historical.terminal.normal_completion",
    "declarer_concession": "historical.terminal.declarer_concession",
    "defender_concession": "historical.terminal.defender_concession",
    "declarer_card_exposure": "historical.terminal.declarer_card_exposure",
    "defender_open_play": "historical.terminal.defender_open_play",
    "open_card_throw": "historical.terminal.open_card_throw",
    "party_wide_all_remaining_tricks_claim": (
        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
    ),
}

_HISTORICAL_CONTINUATION_RULES = {
    "declarer_card_exposure_continuation": (
        "historical.continuation.declarer_card_exposure_then_normal_completion"
    ),
    "defender_open_play_continuation": (
        "historical.continuation.defender_open_play_then_normal_completion"
    ),
}


def _request_reference(
    field_path: str | None = None,
    *,
    visibility: str = "public",
):
    return result_source_reference(
        "request",
        "historical_game_request",
        field_path=field_path,
        visibility=visibility,
    )


def _historical_reference(
    game_id: str,
    field_path: str | None = None,
    *,
    visibility: str = "public",
):
    return result_source_reference(
        "historical_game",
        game_id,
        field_path=field_path,
        visibility=visibility,
    )


def _historical_input(
    source_document: Mapping[str, object] | None,
) -> Mapping[str, object]:
    if source_document is None:
        return {}
    value = source_document.get("historical_game_input")
    return value if isinstance(value, Mapping) else {}


def _game_id(result: Mapping[str, object]) -> str:
    summary = result.get("historical_game_summary")
    if isinstance(summary, Mapping):
        value = summary.get("game_id")
        if isinstance(value, str) and value:
            return value
    return "historical_game_result"


def _summary(result: Mapping[str, object]) -> Mapping[str, object]:
    value = result.get("historical_game_summary")
    if not isinstance(value, Mapping):
        raise ValueError("historical_game_summary must be an object.")
    unknown = sorted(set(value) - _HISTORICAL_SUMMARY_KEYS)
    if unknown:
        raise ValueError(f"Untracked Historical Game summary keys: {unknown}")
    return value


def _record(summary: Mapping[str, object]) -> Mapping[str, object]:
    value = summary.get("record")
    return value if isinstance(value, Mapping) else {}


def _recorded_play_count(summary: Mapping[str, object]) -> int:
    record = _record(summary)
    tricks = record.get("tricks", ())
    if not isinstance(tricks, (list, tuple)):
        return 0
    return sum(
        len(trick.get("plays", ()))
        for trick in tricks
        if isinstance(trick, Mapping) and isinstance(trick.get("plays", ()), (list, tuple))
    )


def _has_historical_event(summary: Mapping[str, object]) -> bool:
    events = _record(summary).get("game_events", ())
    return isinstance(events, (list, tuple)) and bool(events)


def _review_decision_index(
    result: Mapping[str, object],
    tokens: tuple[str, ...],
) -> int:
    for family in ("snapshots", "decisions"):
        if family not in tokens:
            continue
        family_index = tokens.index(family)
        if family_index + 1 >= len(tokens) or not tokens[family_index + 1].isdecimal():
            continue
        value: object = result
        for token in tokens[: family_index + 2]:
            if isinstance(value, Mapping):
                value = value[token]
            elif isinstance(value, (list, tuple)):
                value = value[int(token)]
            else:
                return 0
        if isinstance(value, Mapping):
            decision_index = value.get("decision_index")
            if type(decision_index) is int:
                return decision_index
    return 0


def _review_entry(
    path: str,
    tokens: tuple[str, ...],
    *,
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    total_play_count: int,
    external_reference: str | None,
) -> FieldProvenanceEntry:
    top = tokens[0]
    if top == "historical_opponent_profile_application_summary":
        references = (
            (
                result_source_reference(
                    "external_record",
                    external_reference,
                    visibility="engine_private",
                ),
            )
            if external_reference is not None
            else (result_source_reference("algorithm", "historical_profile_application"),)
        )
        return result_provenance_entry(
            path,
            origin="external_source",
            visibility="public",
            available_from="current_decision",
            derivation="validated",
            source_references=references,
            decision_index=total_play_count,
        )
    branch = tokens[1]
    decision_index = _review_decision_index(result, tokens)
    is_actual = tokens[-1] in {"actual_card", "actual_card_played"}
    if branch == "historical_replay_coaching_summary":
        if "outcome_context" in tokens:
            context_index = tokens.index("outcome_context")
            context_branch = tokens[context_index + 1] if context_index + 1 < len(tokens) else ""
            source_root = {
                "source_game_id": "/historical_game_summary/game_id",
                "game_end_reason": "/historical_game_summary/record/game_end_reason",
                "status": "/historical_game_summary/status",
                "game_result_summary": "/historical_game_summary/game_result_summary",
                "game_value_summary": "/historical_game_summary/game_value_summary",
                "overbid_summary": "/historical_game_summary/overbid_summary",
                "final_settlement_summary": ("/historical_game_summary/final_settlement_summary"),
                "historical_game_end_summary": (
                    "/historical_game_summary/historical_game_end_summary"
                ),
                "historical_game_events_summary": (
                    "/historical_game_summary/historical_game_events_summary"
                ),
            }.get(context_branch)
            source_suffix = "/".join(tokens[context_index + 2 :])
            source_prefixes = (
                ((f"{source_root}/{source_suffix}" if source_suffix else source_root),)
                if source_root is not None
                else ()
            )
            return result_provenance_entry(
                path,
                origin="rule_derived",
                visibility="post_game_only",
                available_from="game_end",
                derivation="deterministic_rule",
                source_references=(
                    result_source_reference(
                        "algorithm",
                        "historical_replay_coaching_v1",
                    ),
                ),
                dependency_paths=leaf_paths_below(leaf_paths, *source_prefixes),
            )
        return result_provenance_entry(
            path,
            origin="heuristic_analysis",
            visibility="public",
            available_from="offline_review",
            derivation="heuristic",
            source_references=(
                result_source_reference("algorithm", "historical_replay_coaching_v1"),
            ),
        )
    return result_provenance_entry(
        path,
        origin="retrospective_attachment" if is_actual else "historical_aggregation",
        visibility="public",
        available_from="after_actual_play" if is_actual else "offline_review",
        derivation="retrospective" if is_actual else "deterministic_rule",
        source_references=(result_source_reference("aggregate", "historical_review_summary"),),
        decision_index=decision_index if is_actual else None,
    )


def _historical_declaration_entry(
    path: str,
    field_name: str,
    *,
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    source_document: Mapping[str, object] | None,
    game_id: str,
) -> FieldProvenanceEntry:
    source_declaration = _historical_input(source_document).get("declaration")
    if not isinstance(source_declaration, Mapping):
        source_declaration = {}
    source_path = f"/historical_game_input/declaration/{field_name}"
    if field_name == "matadors":
        references = [
            result_source_reference(
                "algorithm",
                "historical_complete_deal_matador_inference_v1",
            ),
            result_source_reference(
                "historical_game",
                game_id,
                visibility="engine_private",
            ),
        ]
        return result_provenance_entry(
            path,
            origin="structural_inference",
            visibility="post_game_only",
            available_from="game_end",
            derivation="exact_aggregate",
            source_references=tuple(references),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/historical_game_summary/record/players",
                "/historical_game_summary/record/skat",
            ),
        )
    if field_name in source_declaration:
        return result_provenance_entry(
            path,
            origin="validated_copy",
            visibility="public",
            available_from="request_start",
            derivation="validated",
            source_references=(_request_reference(source_path),),
        )
    record_declaration = _record(_summary(result)).get("declaration")
    if not isinstance(record_declaration, Mapping):
        record_declaration = {}
    implied_by = None
    if record_declaration.get(field_name) is True:
        if field_name == "hand_game":
            implied_by = next(
                (
                    candidate
                    for candidate in (
                        "schneider_announced",
                        "schwarz_announced",
                        "ouvert",
                    )
                    if record_declaration.get(candidate) is True
                ),
                None,
            )
        elif field_name == "schneider_announced":
            implied_by = next(
                (
                    candidate
                    for candidate in ("schwarz_announced", "ouvert")
                    if record_declaration.get(candidate) is True
                ),
                None,
            )
        elif field_name == "schwarz_announced" and record_declaration.get("ouvert") is True:
            implied_by = "ouvert"
    if implied_by is not None:
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="public",
            available_from="request_start",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference(
                    "rule_contract",
                    "canonical_declaration_dependencies_v1",
                ),
            ),
            dependency_paths=(f"/historical_game_summary/record/declaration/{implied_by}",),
        )
    return result_provenance_entry(
        path,
        origin="defaulted",
        visibility="public",
        available_from="request_start",
        derivation="direct",
        source_references=(result_source_reference("algorithm", "game_declaration_defaults_v1"),),
    )


def _record_entry(
    path: str,
    tokens: tuple[str, ...],
    *,
    result: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    source_document: Mapping[str, object] | None,
    game_id: str,
) -> FieldProvenanceEntry:
    record_tokens = tokens[2:]
    if len(record_tokens) >= 2 and record_tokens[0] == "declaration":
        return _historical_declaration_entry(
            path,
            record_tokens[-1],
            result=result,
            leaf_paths=leaf_paths,
            source_document=source_document,
            game_id=game_id,
        )
    private_deal = "initial_hand" in record_tokens or record_tokens[:1] in {
        ("skat",),
        ("discarded_cards",),
    }
    if private_deal:
        return result_provenance_entry(
            path,
            origin="validated_copy",
            visibility="post_game_only",
            available_from="game_end",
            derivation="validated",
            source_references=(
                _historical_reference(
                    game_id,
                    path.removeprefix("/historical_game_summary/record"),
                ),
            ),
        )
    if record_tokens[:1] == ("tricks",):
        if (
            len(record_tokens) >= 4
            and record_tokens[1].isdecimal()
            and (record_tokens[2] == "plays")
        ):
            decision_index = int(record_tokens[1]) * 3 + int(record_tokens[3]) + 1
        elif len(record_tokens) >= 2 and record_tokens[1].isdecimal():
            decision_index = int(record_tokens[1]) * 3 + 1
        else:
            decision_index = None
        return result_provenance_entry(
            path,
            origin="historical_replay",
            visibility="public" if decision_index is not None else "post_game_only",
            available_from="after_actual_play" if decision_index is not None else "game_end",
            derivation="reconstruction",
            source_references=(
                _historical_reference(
                    game_id,
                    path.removeprefix("/historical_game_summary/record"),
                ),
                result_source_reference("rule_contract", "historical_legal_replay_v1"),
            ),
            decision_index=decision_index,
        )
    if record_tokens[:1] == ("game_events",):
        return result_provenance_entry(
            path,
            origin="public_game_event",
            visibility="public",
            available_from="after_public_event",
            derivation="validated",
            source_references=(
                result_source_reference(
                    "historical_event",
                    f"{game_id}:event:0",
                ),
            ),
            event_index=0,
        )
    if record_tokens[:1] in {("game_end",), ("game_end_reason",)}:
        source_path = path.removeprefix("/historical_game_summary/record")
        return result_provenance_entry(
            path,
            origin="public_game_event",
            visibility="post_game_only",
            available_from="game_end",
            derivation="validated",
            source_references=(
                result_source_reference("historical_event", f"{game_id}:terminal"),
                _request_reference(f"/historical_game_input{source_path}"),
            ),
        )
    return result_provenance_entry(
        path,
        origin="validated_copy",
        visibility="public",
        available_from="request_start",
        derivation="validated",
        source_references=(
            _historical_reference(
                game_id,
                path.removeprefix("/historical_game_summary/record"),
            ),
        ),
    )


def _derived_trick_entry(
    path: str,
    tokens: tuple[str, ...],
    *,
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    if len(tokens) < 3 or not tokens[2].isdecimal():
        return result_provenance_entry(
            path,
            origin="historical_replay",
            visibility="post_game_only",
            available_from="game_end",
            derivation="reconstruction",
            source_references=(result_source_reference("algorithm", "historical_legal_replay_v1"),),
        )
    trick_index = int(tokens[2])
    dependencies = leaf_paths_below(
        leaf_paths,
        f"/historical_game_summary/record/tricks/{trick_index}",
        "/historical_game_summary/record/declaration/game_type",
    )
    derived_field = tokens[-1]
    rule_derived = derived_field in {
        "winner_player_id",
        "winner_side",
        "trick_points",
    }
    return result_provenance_entry(
        path,
        origin="rule_derived" if rule_derived else "historical_replay",
        visibility="public",
        available_from="after_actual_play",
        derivation="deterministic_rule" if rule_derived else "reconstruction",
        source_references=(
            result_source_reference(
                "rule_contract" if rule_derived else "historical_game",
                "trick_winner_and_point_rules" if rule_derived else game_id,
            ),
        ),
        dependency_paths=dependencies,
        decision_index=(trick_index + 1) * 3,
    )


def _incomplete_trick_entry(
    path: str,
    *,
    summary: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    completed_count = len(summary.get("derived_tricks", ()))
    total_play_count = _recorded_play_count(summary)
    return result_provenance_entry(
        path,
        origin=("rule_derived" if path.endswith("/next_player_id") else "historical_replay"),
        visibility="public",
        available_from="after_actual_play",
        derivation=("deterministic_rule" if path.endswith("/next_player_id") else "reconstruction"),
        source_references=(
            result_source_reference("algorithm", "historical_legal_replay_v1"),
            _historical_reference(game_id),
        ),
        dependency_paths=leaf_paths_below(
            leaf_paths,
            f"/historical_game_summary/record/tricks/{completed_count}",
            "/historical_game_summary/record/declaration/game_type",
        ),
        decision_index=total_play_count,
    )


def _point_entry(
    path: str,
    *,
    summary: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    references = [
        result_source_reference("rule_contract", "card_point_rules"),
        _historical_reference(game_id),
    ]
    if any(marker in path for marker in ("unresolved", "remaining_hand", "assigned_")):
        references.append(
            result_source_reference(
                "algorithm",
                "historical_remaining_card_reconstruction_v1",
                visibility="engine_private",
            )
        )
    is_party_wide_claim = _record(summary).get("game_end_reason") == (
        "party_wide_all_remaining_tricks_claim"
    )
    claim_assignment_derived = is_party_wide_claim and (
        "/assigned_" in path
        or "/final_" in path
        or path.endswith("/declarer_points")
        or path.endswith("/defender_points")
    )
    if claim_assignment_derived:
        references.extend(
            (
                result_source_reference(
                    "algorithm",
                    "party_wide_all_remaining_tricks_exact_and_or_v1",
                ),
                result_source_reference(
                    "algorithm",
                    "party_wide_claim_adjudication_v1",
                ),
            )
        )
    dependencies = list(
        leaf_paths_below(
            leaf_paths,
            "/historical_game_summary/derived_tricks",
            "/historical_game_summary/incomplete_current_trick",
            "/historical_game_summary/record/skat",
            "/historical_game_summary/record/discarded_cards",
            "/historical_game_summary/record/declaration/hand_game",
        )
    )
    if claim_assignment_derived:
        dependencies.extend(
            leaf_paths_below(
                leaf_paths,
                "/historical_game_summary/historical_game_end_summary/exact_proof/assignment",
                "/historical_game_summary/historical_game_end_summary/adjudication",
            )
        )
    return result_provenance_entry(
        path,
        origin="rule_derived",
        visibility="post_game_only",
        available_from="game_end",
        derivation="deterministic_rule",
        source_references=tuple(references),
        dependency_paths=dependencies,
    )


def _play_prefix_entry(
    path: str,
    *,
    summary: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    return result_provenance_entry(
        path,
        origin="historical_replay",
        visibility="post_game_only",
        available_from="game_end",
        derivation="reconstruction",
        source_references=(
            result_source_reference("algorithm", "historical_legal_replay_v1"),
            _historical_reference(game_id),
        ),
        dependency_paths=leaf_paths_below(
            leaf_paths,
            "/historical_game_summary/record/players",
            "/historical_game_summary/record/skat",
            "/historical_game_summary/record/discarded_cards",
            "/historical_game_summary/record/declaration",
            "/historical_game_summary/record/tricks",
        ),
        decision_index=_recorded_play_count(summary),
    )


def _party_wide_claim_terminal_entry(
    path: str,
    *,
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    terminal_prefix = "/historical_game_summary/historical_game_end_summary"
    suffix = path.removeprefix(terminal_prefix)
    references = [
        result_source_reference(
            "rule_contract",
            "claim_boundary.decision.party_wide_all_remaining_tricks_claim",
        )
    ]
    origin = "rule_derived"
    derivation = "deterministic_rule"

    if suffix.startswith("/exact_proof/"):
        references.extend(
            (
                result_source_reference(
                    "algorithm",
                    "party_wide_all_remaining_tricks_exact_and_or_v1",
                ),
                result_source_reference(
                    "aggregate",
                    "party_wide_claim_complete_world_evidence_v1",
                    visibility="engine_private",
                ),
                result_source_reference(
                    "algorithm",
                    "party_wide_claim_exact_state_v1",
                    visibility="engine_private",
                ),
            )
        )
        dependency_prefixes = (
            "/historical_game_summary/record/game_end",
            "/historical_game_summary/record/game_end_reason",
            "/historical_game_summary/record/players",
            "/historical_game_summary/record/skat",
            "/historical_game_summary/record/discarded_cards",
            "/historical_game_summary/record/declaration",
            "/historical_game_summary/record/tricks",
        )
    elif suffix.startswith("/adjudication/"):
        references.append(
            result_source_reference(
                "algorithm",
                "party_wide_claim_adjudication_v1",
            )
        )
        dependency_prefixes = (
            f"{terminal_prefix}/exact_proof",
            "/historical_game_summary/derived_tricks",
            "/historical_game_summary/incomplete_current_trick",
            "/historical_game_summary/record/skat",
            "/historical_game_summary/record/discarded_cards",
            "/historical_game_summary/record/declaration",
            "/historical_game_summary/game_value_summary",
            "/historical_game_summary/overbid_summary",
        )
    elif suffix in {"/claimant_player_id", "/claiming_party", "/kind"}:
        field_name = suffix.removeprefix("/")
        origin = "validated_copy"
        derivation = "validated"
        references.append(_historical_reference(game_id, f"/game_end/{field_name}"))
        dependency_prefixes = (f"/historical_game_summary/record/game_end/{field_name}",)
    elif suffix in {"/declarer_player_id"} or suffix.startswith("/defender_player_ids/"):
        origin = "validated_copy" if suffix == "/declarer_player_id" else "historical_replay"
        derivation = "validated" if suffix == "/declarer_player_id" else "reconstruction"
        dependency_prefixes = (
            "/historical_game_summary/record/declarer_player_id",
            "/historical_game_summary/record/players",
        )
    elif suffix == "/settlement_applied":
        references.append(result_source_reference("algorithm", "party_wide_claim_adjudication_v1"))
        dependency_prefixes = (f"{terminal_prefix}/adjudication",)
    elif suffix.startswith(("/event_", "/remaining_trick_count")):
        references.append(result_source_reference("algorithm", "historical_legal_replay_v1"))
        dependency_prefixes = (
            "/historical_game_summary/record/players",
            "/historical_game_summary/record/skat",
            "/historical_game_summary/record/discarded_cards",
            "/historical_game_summary/record/declaration",
            "/historical_game_summary/record/tricks",
        )
    else:
        dependency_prefixes = ("/historical_game_summary/record/game_end_reason",)

    return result_provenance_entry(
        path,
        origin=origin,
        visibility="post_game_only",
        available_from="game_end",
        derivation=derivation,
        source_references=tuple(references),
        dependency_paths=leaf_paths_below(leaf_paths, *dependency_prefixes),
    )


def _terminal_entry(
    path: str,
    *,
    summary: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    record_end_reason = _record(summary).get("game_end_reason")
    reference_id = _HISTORICAL_END_RULES.get(str(record_end_reason))
    if reference_id is None:
        raise ValueError(f"Unsupported Historical terminal kind: {record_end_reason}")
    if record_end_reason == "party_wide_all_remaining_tricks_claim":
        return _party_wide_claim_terminal_entry(
            path,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    references = [result_source_reference("rule_contract", reference_id)]
    if record_end_reason == "defender_open_play" and (
        "/exact_proof/" in path or path.endswith("/exact_proof") or "/proof_" in path
    ):
        references.append(
            result_source_reference(
                "algorithm",
                "defender_open_play_exact_proof_v1",
                visibility="engine_private",
            )
        )
    if record_end_reason == "open_card_throw" and (
        "theoretical_schwarz_assessment" in path or "jack_ownership_evidence" in path
    ):
        references.append(
            result_source_reference(
                "algorithm",
                "open_throw_jack_exclusion_v1",
                visibility="engine_private",
            )
        )
    return result_provenance_entry(
        path,
        origin="rule_derived",
        visibility="post_game_only",
        available_from="game_end",
        derivation="deterministic_rule",
        source_references=tuple(references),
        dependency_paths=leaf_paths_below(
            leaf_paths,
            "/historical_game_summary/record/game_end",
            "/historical_game_summary/record/game_end_reason",
            "/historical_game_summary/derived_tricks",
            "/historical_game_summary/incomplete_current_trick",
            "/historical_game_summary/point_accounting",
            "/historical_game_summary/declarer_trick_points",
            "/historical_game_summary/defender_trick_points",
            "/historical_game_summary/skat_points",
            "/historical_game_summary/record/declaration",
            "/historical_game_summary/game_value_summary",
            "/historical_game_summary/overbid_summary",
        ),
    )


def _event_summary_entry(
    path: str,
    *,
    summary: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    game_id: str,
) -> FieldProvenanceEntry:
    events_summary = summary.get("historical_game_events_summary")
    event_rows = events_summary.get("events", ()) if isinstance(events_summary, Mapping) else ()
    event_kind = None
    if isinstance(event_rows, (list, tuple)) and event_rows and isinstance(event_rows[0], Mapping):
        event_kind = event_rows[0].get("kind")
    reference_id = _HISTORICAL_CONTINUATION_RULES.get(str(event_kind))
    if reference_id is None:
        raise ValueError(f"Unsupported Historical continuation kind: {event_kind}")
    final_only = any(
        marker in path
        for marker in (
            "/actual_plays_after_event",
            "/final_game_end_reason",
            "/final_outcome_source",
        )
    )
    dependencies = list(
        leaf_paths_below(
            leaf_paths,
            "/historical_game_summary/record/game_events",
        )
    )
    if final_only:
        dependencies.extend(
            leaf_paths_below(
                leaf_paths,
                "/historical_game_summary/record/tricks",
                "/historical_game_summary/record/game_end",
                "/historical_game_summary/record/game_end_reason",
            )
        )
    return result_provenance_entry(
        path,
        origin="rule_derived" if final_only else "public_game_event",
        visibility="post_game_only" if final_only else "public",
        available_from="game_end" if final_only else "after_public_event",
        derivation="deterministic_rule" if final_only else "validated",
        source_references=(
            result_source_reference("rule_contract", reference_id),
            result_source_reference("historical_event", f"{game_id}:event:0"),
        ),
        dependency_paths=dependencies,
        event_index=None if final_only else 0,
    )


def _base_summary_entry(
    path: str,
    tokens: tuple[str, ...],
    *,
    result: Mapping[str, object],
    summary: Mapping[str, object],
    leaf_paths: tuple[str, ...],
    source_document: Mapping[str, object] | None,
    game_id: str,
) -> FieldProvenanceEntry:
    branch = tokens[1]
    if branch == "record":
        return _record_entry(
            path,
            tokens,
            result=result,
            leaf_paths=leaf_paths,
            source_document=source_document,
            game_id=game_id,
        )
    if branch == "derived_tricks":
        return _derived_trick_entry(
            path,
            tokens,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    if branch == "incomplete_current_trick":
        return _incomplete_trick_entry(
            path,
            summary=summary,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    if branch == "play_prefix_summary":
        return _play_prefix_entry(
            path,
            summary=summary,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    if branch in {
        "point_accounting",
        "declarer_trick_points",
        "defender_trick_points",
        "skat_points",
        "declarer_points",
        "defender_points",
    }:
        return _point_entry(
            path,
            summary=summary,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    if branch == "historical_game_end_summary":
        return _terminal_entry(
            path,
            summary=summary,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    if branch == "historical_game_events_summary":
        return _event_summary_entry(
            path,
            summary=summary,
            leaf_paths=leaf_paths,
            game_id=game_id,
        )
    if branch == "game_result_summary":
        field_name = tokens[2] if len(tokens) > 2 else ""
        raw = field_name in _RAW_RESULT_FIELDS
        dependencies = list(
            leaf_paths_below(
                leaf_paths,
                "/historical_game_summary/point_accounting",
                "/historical_game_summary/declarer_trick_points",
                "/historical_game_summary/defender_trick_points",
                "/historical_game_summary/skat_points",
                "/historical_game_summary/declarer_points",
                "/historical_game_summary/defender_points",
                "/historical_game_summary/derived_tricks",
                "/historical_game_summary/record/declaration/game_type",
            )
        )
        if not raw:
            dependencies.extend(
                leaf_paths_below(
                    leaf_paths,
                    "/historical_game_summary/historical_game_end_summary",
                    "/historical_game_summary/record/game_end",
                    "/historical_game_summary/record/game_end_reason",
                )
            )
        is_party_wide_claim = _record(summary).get("game_end_reason") == (
            "party_wide_all_remaining_tricks_claim"
        )
        if is_party_wide_claim:
            dependencies.extend(
                leaf_paths_below(
                    leaf_paths,
                    "/historical_game_summary/historical_game_end_summary/exact_proof",
                    "/historical_game_summary/historical_game_end_summary/adjudication",
                )
            )
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="post_game_only",
            available_from="game_end",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference(
                    "rule_contract",
                    (
                        "claim_boundary.decision.party_wide_all_remaining_tricks_claim"
                        if is_party_wide_claim
                        else "historical_raw_game_result_v1"
                        if raw
                        else "settlement_normative_matrix_v1"
                    ),
                ),
                *(
                    (
                        result_source_reference(
                            "algorithm",
                            "party_wide_claim_adjudication_v1",
                        ),
                    )
                    if is_party_wide_claim
                    else ()
                ),
            ),
            dependency_paths=dependencies,
        )
    if branch == "game_value_summary":
        return build_game_value_result_entry(
            path,
            leaf_paths=leaf_paths,
            declaration_prefix="/historical_game_summary/record/declaration",
            available_from="game_end",
            decision_index=None,
            visibility="post_game_only",
        )
    if branch == "overbid_summary":
        return build_overbid_result_entry(
            path,
            leaf_paths=leaf_paths,
            declaration_prefix="/historical_game_summary/record/declaration",
            game_value_prefix="/historical_game_summary/game_value_summary",
            ending_prefixes=("/historical_game_summary/record/game_end_reason",),
            available_from="game_end",
            decision_index=None,
            visibility="post_game_only",
        )
    if branch == "final_settlement_summary":
        return build_settlement_result_entry(
            path,
            leaf_paths=leaf_paths,
            result_prefix="/historical_game_summary/game_result_summary",
            game_value_prefix="/historical_game_summary/game_value_summary",
            overbid_prefix="/historical_game_summary/overbid_summary",
            ending_prefixes=(
                "/historical_game_summary/historical_game_end_summary",
                "/historical_game_summary/record/game_end",
            ),
            completed_trick_prefixes=("/historical_game_summary/derived_tricks",),
            visibility="post_game_only",
        )
    if branch in {"winner", "schneider_status", "schwarz_status"}:
        is_party_wide_claim = _record(summary).get("game_end_reason") == (
            "party_wide_all_remaining_tricks_claim"
        )
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="post_game_only",
            available_from="game_end",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference(
                    "algorithm" if is_party_wide_claim else "rule_contract",
                    (
                        "party_wide_claim_adjudication_v1"
                        if is_party_wide_claim
                        else "historical_game_result_v1"
                    ),
                ),
            ),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/historical_game_summary/game_result_summary",
                "/historical_game_summary/derived_tricks",
            ),
        )
    if branch in {"schema_version", "game_id", "played_at"}:
        return result_provenance_entry(
            path,
            origin="validated_copy",
            visibility="public",
            available_from="request_start",
            derivation="validated",
            source_references=(_historical_reference(game_id),),
        )
    if branch == "status":
        return result_provenance_entry(
            path,
            origin="rule_derived",
            visibility="post_game_only",
            available_from="game_end",
            derivation="deterministic_rule",
            source_references=(
                result_source_reference("algorithm", "historical_game_validation_v1"),
            ),
            dependency_paths=leaf_paths_below(
                leaf_paths,
                "/historical_game_summary/record",
                "/historical_game_summary/derived_tricks",
            ),
        )
    raise AssertionError(f"Unhandled Historical Result provenance branch: {branch}")


def build_historical_result_entries(
    result: Mapping[str, object],
    *,
    source_document: Mapping[str, object] | None,
    external_reference: str | None,
) -> tuple[FieldProvenanceEntry, ...]:
    """Builds exact all-leaf entries for one retained Historical Root Result."""
    unknown_root_keys = sorted(set(result) - HISTORICAL_RESULT_KEYS)
    if unknown_root_keys:
        raise ValueError(f"Untracked Historical Result keys: {unknown_root_keys}")
    summary = _summary(result)
    leaf_paths = enumerate_json_leaf_paths(result)
    game_id = _game_id(result)
    total_play_count = _recorded_play_count(summary)
    entries = []
    for path in leaf_paths:
        tokens = parse_json_pointer(path)
        if path == "/input_file":
            entry = result_provenance_entry(
                path,
                origin="caller_supplied",
                visibility="public",
                available_from="request_start",
                derivation="direct",
                source_references=(
                    result_source_reference("request", "application_input_reference"),
                ),
            )
        elif tokens[0] == "historical_opponent_profile_application_summary" or (
            len(tokens) >= 2 and tokens[1] in _REVIEW_BRANCHES
        ):
            entry = _review_entry(
                path,
                tokens,
                result=result,
                leaf_paths=leaf_paths,
                total_play_count=total_play_count,
                external_reference=external_reference,
            )
        else:
            entry = _base_summary_entry(
                path,
                tokens,
                result=result,
                summary=summary,
                leaf_paths=leaf_paths,
                source_document=source_document,
                game_id=game_id,
            )
        entries.append(entry)
    return tuple(entries)


_HISTORICAL_ALLOWED_DEPENDENCY_PREFIXES = {
    "derived_tricks": (
        "/historical_game_summary/record/tricks",
        "/historical_game_summary/record/declaration/game_type",
    ),
    "incomplete_current_trick": (
        "/historical_game_summary/record/tricks",
        "/historical_game_summary/record/declaration/game_type",
    ),
    "play_prefix_summary": (
        "/historical_game_summary/record/players",
        "/historical_game_summary/record/skat",
        "/historical_game_summary/record/discarded_cards",
        "/historical_game_summary/record/declaration",
        "/historical_game_summary/record/tricks",
    ),
    "point_accounting": (
        "/historical_game_summary/derived_tricks",
        "/historical_game_summary/incomplete_current_trick",
        "/historical_game_summary/record/skat",
        "/historical_game_summary/record/discarded_cards",
        "/historical_game_summary/record/declaration/hand_game",
        "/historical_game_summary/historical_game_end_summary/exact_proof/assignment",
        "/historical_game_summary/historical_game_end_summary/adjudication",
    ),
    "declarer_points": (
        "/historical_game_summary/derived_tricks",
        "/historical_game_summary/incomplete_current_trick",
        "/historical_game_summary/record/skat",
        "/historical_game_summary/record/discarded_cards",
        "/historical_game_summary/record/declaration/hand_game",
        "/historical_game_summary/historical_game_end_summary/exact_proof/assignment",
        "/historical_game_summary/historical_game_end_summary/adjudication",
    ),
    "defender_points": (
        "/historical_game_summary/derived_tricks",
        "/historical_game_summary/incomplete_current_trick",
        "/historical_game_summary/record/skat",
        "/historical_game_summary/record/discarded_cards",
        "/historical_game_summary/record/declaration/hand_game",
        "/historical_game_summary/historical_game_end_summary/exact_proof/assignment",
        "/historical_game_summary/historical_game_end_summary/adjudication",
    ),
    "game_result_summary": (
        "/historical_game_summary/point_accounting",
        "/historical_game_summary/declarer_trick_points",
        "/historical_game_summary/defender_trick_points",
        "/historical_game_summary/skat_points",
        "/historical_game_summary/declarer_points",
        "/historical_game_summary/defender_points",
        "/historical_game_summary/derived_tricks",
        "/historical_game_summary/record/declaration/game_type",
        "/historical_game_summary/historical_game_end_summary",
        "/historical_game_summary/record/game_end",
        "/historical_game_summary/record/game_end_reason",
    ),
    "game_value_summary": ("/historical_game_summary/record/declaration",),
    "overbid_summary": (
        "/historical_game_summary/record/declaration",
        "/historical_game_summary/game_value_summary",
        "/historical_game_summary/record/game_end_reason",
    ),
    "historical_game_end_summary": (
        "/historical_game_summary/record/game_end",
        "/historical_game_summary/record/game_end_reason",
        "/historical_game_summary/record/players",
        "/historical_game_summary/record/declarer_player_id",
        "/historical_game_summary/record/skat",
        "/historical_game_summary/record/discarded_cards",
        "/historical_game_summary/record/tricks",
        "/historical_game_summary/derived_tricks",
        "/historical_game_summary/incomplete_current_trick",
        "/historical_game_summary/point_accounting",
        "/historical_game_summary/declarer_trick_points",
        "/historical_game_summary/defender_trick_points",
        "/historical_game_summary/skat_points",
        "/historical_game_summary/record/declaration",
        "/historical_game_summary/game_value_summary",
        "/historical_game_summary/overbid_summary",
        "/historical_game_summary/historical_game_end_summary/exact_proof",
        "/historical_game_summary/historical_game_end_summary/adjudication",
    ),
    "historical_game_events_summary": (
        "/historical_game_summary/record/game_events",
        "/historical_game_summary/record/tricks",
        "/historical_game_summary/record/game_end",
        "/historical_game_summary/record/game_end_reason",
    ),
    "final_settlement_summary": (
        "/historical_game_summary/game_result_summary",
        "/historical_game_summary/game_value_summary",
        "/historical_game_summary/overbid_summary",
        "/historical_game_summary/historical_game_end_summary",
        "/historical_game_summary/record/game_end",
        "/historical_game_summary/derived_tricks",
    ),
}


def validate_historical_result_provenance_dependencies(
    entries: tuple[FieldProvenanceEntry, ...],
) -> None:
    """Rejects reverse, cross-domain, and later-trick Historical dependencies."""
    for entry in entries:
        tokens = parse_json_pointer(entry.field_path)
        if len(tokens) < 2 or tokens[0] != "historical_game_summary":
            continue
        branch = tokens[1]
        allowed = _HISTORICAL_ALLOWED_DEPENDENCY_PREFIXES.get(branch)
        if allowed is not None:
            for dependency in entry.dependency_paths:
                if not any(
                    dependency == prefix or dependency.startswith(f"{prefix}/")
                    for prefix in allowed
                ):
                    raise SkatAIInformationPolicyError(
                        "Historical Result provenance contains a reverse or "
                        "cross-domain dependency.",
                        path=entry.field_path,
                    )
        if branch == "derived_tricks" and len(tokens) >= 3 and tokens[2].isdecimal():
            trick_index = int(tokens[2])
            for dependency in entry.dependency_paths:
                dependency_tokens = parse_json_pointer(dependency)
                if (
                    len(dependency_tokens) >= 4
                    and dependency_tokens[:3] == ("historical_game_summary", "record", "tricks")
                    and dependency_tokens[3].isdecimal()
                    and int(dependency_tokens[3]) > trick_index
                ):
                    raise SkatAIInformationPolicyError(
                        "A Historical trick cannot depend on later play.",
                        path=entry.field_path,
                    )


def build_historical_game_result_attachment(
    result: Mapping[str, object],
    *,
    source_document: Mapping[str, object] | None = None,
    external_reference: str | None,
) -> ApplicationProvenanceAttachment:
    """Builds complete non-legacy provenance for one exact Historical Root Result."""
    summary = _summary(result)
    entries = build_historical_result_entries(
        result,
        source_document=source_document,
        external_reference=external_reference,
    )
    validate_historical_result_provenance_dependencies(entries)
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=entries,
        exemptions=(),
        limitations=(),
    )
    coverage = build_field_provenance_coverage_summary(result, ledger)
    return ApplicationProvenanceAttachment(
        name="historical_game_result",
        document_role="result",
        document=result,
        ledger=ledger,
        coverage_summary=coverage,
        information_use_context=InformationUseContext(
            workflow="historical_game",
            stage="engine_internal",
            perspective_player_id=None,
            perspective_side=None,
            decision_index=_recorded_play_count(summary),
            event_index=0 if _has_historical_event(summary) else None,
        ),
    )
