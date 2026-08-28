from __future__ import annotations

from collections.abc import Mapping

from skatmind.api.v1.contracts import WorkflowV1
from skatmind.application.provenance import (
    ApplicationProvenanceAttachment,
    ApplicationProvenanceBundle,
)
from skatmind.errors import SkatMindValidationError
from skatmind.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceSourceReference,
    resolve_json_pointer,
)
from skatmind.field_provenance_policy import InformationUseContext
from skatmind.fixed_three_player_historical_list import (
    build_serializable_fixed_three_player_historical_list,
    build_serializable_fixed_three_player_historical_list_entry_fact,
)
from skatmind.fixed_three_player_historical_list_aggregation import (
    FixedThreePlayerHistoricalListAggregation,
    build_serializable_fixed_three_player_historical_list_aggregation,
)
from skatmind.fixed_three_player_historical_list_request import (
    FixedThreePlayerHistoricalListAnalysisRequest,
    FixedThreePlayerHistoricalListComparisonRequest,
)
from skatmind.retrospective_review_provenance import (
    _entry,
    _reference,
    build_complete_provenance_attachment,
)
from skatmind.v1_information_provenance_sources import exact_v1_json_equal

HISTORICAL_LIST_PROVENANCE_VERSION = 1

_RANKING_FIELDS = ("total_performance_points", "own_games_won", "own_games_lost")


def _context(workflow: str) -> InformationUseContext:
    return InformationUseContext(
        workflow=workflow,
        stage="offline_review",
        perspective_player_id=None,
        perspective_side=None,
        decision_index=None,
        event_index=None,
    )


def _serialize_request(
    request: FixedThreePlayerHistoricalListAnalysisRequest,
) -> dict[str, object]:
    return {
        "schema_version": request.schema_version,
        "historical_list": build_serializable_fixed_three_player_historical_list(
            request.historical_list
        ),
        "lot_order": None if request.lot_order is None else list(request.lot_order),
    }


def _serialize_comparison_request(
    request: FixedThreePlayerHistoricalListComparisonRequest,
) -> dict[str, object]:
    return {
        "schema_version": request.schema_version,
        "lists": [_serialize_request(source) for source in request.lists],
    }


def _list_reference(list_id: str) -> FieldProvenanceSourceReference:
    return _reference("external_record", f"historical_list/{list_id}")


def _entry_reference(
    list_id: str,
    entry_number: int,
) -> FieldProvenanceSourceReference:
    return _reference("external_record", f"historical_list/{list_id}/entry/{entry_number}")


def _list_entry(
    path: str,
    *,
    origin: str,
    derivation: str,
    references: tuple[FieldProvenanceSourceReference, ...],
    availability: str = "offline_review",
    dependencies: tuple[str, ...] = (),
) -> FieldProvenanceEntry:
    return _entry(
        path,
        origin=origin,
        visibility="post_game_only",
        available_from=availability,
        derivation=derivation,
        decision_index=None,
        perspective_player_id=None,
        source_references=references,
        dependency_paths=dependencies,
    )


def _input_attachment(
    request: FixedThreePlayerHistoricalListAnalysisRequest,
    *,
    source_document: Mapping[str, object],
    name: str = "historical_list/input",
    workflow: str = "fixed_three_player_historical_list",
) -> ApplicationProvenanceAttachment:
    list_id = request.historical_list.list_id
    document = _serialize_request(request)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        try:
            source_value = resolve_json_pointer(source_document, path)
            retained_value = resolve_json_pointer(document, path)
        except SkatMindValidationError:
            exact_source = False
        else:
            exact_source = exact_v1_json_equal(source_value, retained_value)
        if exact_source and tokens and tokens[0] == "historical_list":
            references = (
                FieldProvenanceSourceReference(
                    reference_type="external_record",
                    reference_id=f"historical_list/{list_id}",
                    field_path=path,
                    visibility="public",
                ),
            )
            origin = "validated_copy"
            derivation = "validated"
        elif exact_source:
            references = (
                FieldProvenanceSourceReference(
                    reference_type="request",
                    reference_id="historical_list_input",
                    field_path=path,
                    visibility="public",
                ),
            )
            origin = "caller_supplied"
            derivation = "direct"
        else:
            references = (
                _reference(
                    "rule_contract",
                    "fixed_three_player_historical_list_normalization_v1",
                ),
            )
            origin = "rule_derived"
            derivation = "deterministic_rule"
        return _list_entry(
            path,
            origin=origin,
            derivation=derivation,
            references=references,
        )

    return build_complete_provenance_attachment(
        name=name,
        document_role="consumed_input",
        document=document,
        information_use_context=_context(workflow),
        entry_builder=build,
    )


def _entry_fact_attachment(
    aggregation: FixedThreePlayerHistoricalListAggregation,
    source_index: int,
) -> ApplicationProvenanceAttachment:
    fact = aggregation.progression[source_index].entry_fact
    document = build_serializable_fixed_three_player_historical_list_entry_fact(fact)
    entry_reference = _entry_reference(aggregation.list_id, fact.entry_number)
    references = [entry_reference]
    if fact.game_id is not None:
        references.append(_reference("historical_game", fact.game_id))
    source_references = tuple(references)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        direct_references: tuple[FieldProvenanceSourceReference, ...] | None = None
        if tokens in {("entry_id",), ("entry_kind",), ("played_at",)}:
            source_path = (
                "/historical_game/played_at"
                if tokens == ("played_at",) and fact.game_id is not None
                else path
            )
            direct_references = (
                FieldProvenanceSourceReference(
                    reference_type="external_record",
                    reference_id=(
                        f"historical_list/{aggregation.list_id}/entry/{fact.entry_number}"
                    ),
                    field_path=source_path,
                    visibility="public",
                ),
            )
        elif tokens == ("list_id",):
            direct_references = (
                FieldProvenanceSourceReference(
                    reference_type="external_record",
                    reference_id=f"historical_list/{aggregation.list_id}",
                    field_path="/historical_list/list_id",
                    visibility="public",
                ),
            )
        elif tokens == ("game_id",) and fact.game_id is not None:
            direct_references = (
                FieldProvenanceSourceReference(
                    reference_type="historical_game",
                    reference_id=fact.game_id,
                    field_path="/game_id",
                    visibility="public",
                ),
            )
        rule_derived = bool(
            tokens
            and tokens[0]
            in {
                "entry_number",
                "round_number",
                "dealer_player_id",
                "seat_assignment",
                "player_contributions",
            }
        )
        outcome = bool(
            tokens
            and tokens[0]
            in {
                "entry_outcome",
                "game_end_reason",
                "declarer_player_id",
                "settlement_score",
            }
        )
        return _list_entry(
            path,
            origin=(
                "validated_copy"
                if direct_references is not None
                else "rule_derived"
                if rule_derived
                else "historical_aggregation"
                if outcome
                else "rule_derived"
            ),
            derivation=(
                "validated"
                if direct_references is not None
                else "deterministic_rule"
                if rule_derived
                else "exact_aggregate"
                if outcome
                else "deterministic_rule"
            ),
            references=(
                direct_references
                if direct_references is not None
                else source_references
            ),
            availability="offline_review",
        )

    return build_complete_provenance_attachment(
        name=f"historical_list/entry/{fact.entry_number}",
        document_role="result",
        document=document,
        information_use_context=_context("fixed_three_player_historical_list"),
        entry_builder=build,
    )


def _ranking_dependencies(prefix: str) -> tuple[str, ...]:
    return tuple(
        f"{prefix}/{player_index}/{field_name}"
        for player_index in range(3)
        for field_name in _RANKING_FIELDS
    )


def _aggregation_entry_builder(
    document: Mapping[str, object],
    list_id: str,
):
    progression = document["progression"]
    assert isinstance(progression, list)
    player_totals = document["player_totals"]
    assert isinstance(player_totals, list)

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        dependencies: tuple[str, ...] = ()
        references: tuple[FieldProvenanceSourceReference, ...] = (
            _reference("aggregate", f"historical_list/{list_id}/aggregation"),
        )
        origin = "historical_aggregation"
        derivation = "exact_aggregate"

        if len(tokens) >= 2 and tokens[0] == "progression":
            progression_index = int(tokens[1])
            snapshot = progression[progression_index]
            assert isinstance(snapshot, Mapping)
            entry_number = progression_index + 1
            references = (_entry_reference(list_id, entry_number),)
            if len(tokens) >= 3 and tokens[2] == "entry_fact":
                origin = "rule_derived"
                derivation = "deterministic_rule"
            elif len(tokens) >= 5 and tokens[2] == "cumulative_player_totals":
                player_index = int(tokens[3])
                field_name = tokens[4]
                current_dependencies: list[str] = []
                entry_fact = snapshot["entry_fact"]
                assert isinstance(entry_fact, Mapping)
                contributions = entry_fact["player_contributions"]
                assert isinstance(contributions, list)
                contribution = contributions[player_index]
                assert isinstance(contribution, Mapping)
                if field_name in contribution:
                    current_dependencies.append(
                        f"/progression/{progression_index}/entry_fact/"
                        f"player_contributions/{player_index}/{field_name}"
                    )
                if progression_index > 0:
                    current_dependencies.append(
                        f"/progression/{progression_index - 1}/"
                        f"cumulative_player_totals/{player_index}/{field_name}"
                    )
                dependencies = tuple(current_dependencies)
            elif len(tokens) >= 5 and tokens[2] == "provisional_standings":
                standing_index = int(tokens[3])
                standing = snapshot["provisional_standings"][standing_index]
                assert isinstance(standing, Mapping)
                if tokens[4] == "rank":
                    dependencies = _ranking_dependencies(
                        f"/progression/{progression_index}/cumulative_player_totals"
                    )
                elif len(tokens) >= 7 and tokens[4] == "player_totals":
                    standing_totals = standing["player_totals"]
                    assert isinstance(standing_totals, Mapping)
                    player_id = standing_totals["player_id"]
                    cumulative = snapshot["cumulative_player_totals"]
                    assert isinstance(cumulative, list)
                    cumulative_index = next(
                        index
                        for index, row in enumerate(cumulative)
                        if isinstance(row, Mapping) and row["player_id"] == player_id
                    )
                    dependencies = (
                        f"/progression/{progression_index}/cumulative_player_totals/"
                        f"{cumulative_index}/{tokens[6]}",
                    )
            elif len(tokens) >= 3 and tokens[2] == "tied_player_ids":
                dependencies = _ranking_dependencies(
                    f"/progression/{progression_index}/cumulative_player_totals"
                )
        elif len(tokens) >= 3 and tokens[0] == "player_totals":
            player_index = int(tokens[1])
            dependencies = (
                f"/progression/{len(progression) - 1}/cumulative_player_totals/"
                f"{player_index}/{tokens[2]}",
            )
        elif tokens and tokens[0] in {
            "entry_count",
            "round_count",
            "played_game_count",
            "passed_deal_count",
            "declarer_win_count",
            "declarer_loss_count",
        }:
            dependency_field = {
                "entry_count": "entry_number",
                "round_count": "round_number",
                "played_game_count": "entry_kind",
                "passed_deal_count": "entry_kind",
                "declarer_win_count": "entry_outcome",
                "declarer_loss_count": "entry_outcome",
            }[tokens[0]]
            dependencies = tuple(
                f"/progression/{index}/entry_fact/{dependency_field}"
                for index in range(len(progression))
            )
        elif tokens and tokens[0] in {
            "ranking_status",
            "tied_player_ids",
            "lot_required_player_ids",
        }:
            dependencies = _ranking_dependencies("/player_totals")
        elif tokens and tokens[0] == "applied_lot_order":
            origin = "caller_supplied"
            derivation = "direct"
            references = (
                FieldProvenanceSourceReference(
                    reference_type="request",
                    reference_id="historical_list_input",
                    field_path="/lot_order",
                    visibility="public",
                ),
            )
        elif len(tokens) >= 3 and tokens[0] == "final_standings":
            standing_index = int(tokens[1])
            standings = document["final_standings"]
            assert isinstance(standings, list)
            standing = standings[standing_index]
            assert isinstance(standing, Mapping)
            standing_totals = standing["player_totals"]
            assert isinstance(standing_totals, Mapping)
            if tokens[2] == "rank":
                dependencies = _ranking_dependencies("/player_totals")
                if document["applied_lot_order"] is not None:
                    applied_lot = document["applied_lot_order"]
                    assert isinstance(applied_lot, list)
                    dependencies = (
                        *dependencies,
                        *(f"/applied_lot_order/{index}" for index in range(len(applied_lot))),
                    )
            elif len(tokens) >= 5 and tokens[2] == "player_totals":
                player_id = standing_totals["player_id"]
                total_index = next(
                    index
                    for index, row in enumerate(player_totals)
                    if isinstance(row, Mapping) and row["player_id"] == player_id
                )
                dependencies = (f"/player_totals/{total_index}/{tokens[4]}",)

        return _list_entry(
            path,
            origin=origin,
            derivation=derivation,
            references=references,
            dependencies=dependencies,
        )

    return build


def validate_historical_list_progression_dependencies(
    entries: tuple[FieldProvenanceEntry, ...],
) -> None:
    """Rejects any progression field that depends on a later snapshot."""
    for entry in entries:
        tokens = entry.field_path.split("/")
        if len(tokens) < 3 or tokens[1] != "progression" or not tokens[2].isdecimal():
            continue
        current_index = int(tokens[2])
        for dependency in entry.dependency_paths:
            dependency_tokens = dependency.split("/")
            if (
                len(dependency_tokens) >= 3
                and dependency_tokens[1] == "progression"
                and dependency_tokens[2].isdecimal()
                and int(dependency_tokens[2]) > current_index
            ):
                raise ValueError("Historical-list progression cannot depend on a later entry.")


def _aggregation_attachment(
    aggregation: FixedThreePlayerHistoricalListAggregation,
) -> ApplicationProvenanceAttachment:
    document = build_serializable_fixed_three_player_historical_list_aggregation(aggregation)
    attachment = build_complete_provenance_attachment(
        name="historical_list/aggregation",
        document_role="result",
        document=document,
        information_use_context=_context("fixed_three_player_historical_list"),
        entry_builder=_aggregation_entry_builder(document, aggregation.list_id),
    )
    validate_historical_list_progression_dependencies(attachment.ledger.entries)
    return attachment


def _root_attachment(
    result: Mapping[str, object],
    *,
    name: str,
    workflow: str,
    aggregate_id: str,
) -> ApplicationProvenanceAttachment:
    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        if tokens == ("input_file",):
            return _list_entry(
                path,
                origin="caller_supplied",
                derivation="direct",
                references=(_reference("request", "application_input_reference"),),
            )
        return _list_entry(
            path,
            origin="historical_aggregation",
            derivation="exact_aggregate",
            references=(_reference("aggregate", aggregate_id),),
        )

    return build_complete_provenance_attachment(
        name=name,
        document_role="result",
        document=result,
        information_use_context=_context(workflow),
        entry_builder=build,
    )


class HistoricalListProvenanceCollector:
    """Consumes one retained list request and aggregation."""

    def __init__(self) -> None:
        self._request: FixedThreePlayerHistoricalListAnalysisRequest | None = None
        self._aggregation: FixedThreePlayerHistoricalListAggregation | None = None

    def capture(
        self,
        request: FixedThreePlayerHistoricalListAnalysisRequest,
        aggregation: FixedThreePlayerHistoricalListAggregation,
    ) -> None:
        self._request = request
        self._aggregation = aggregation

    def build_bundle(
        self,
        root_result: Mapping[str, object],
        *,
        source_document: Mapping[str, object],
    ) -> ApplicationProvenanceBundle:
        if self._request is None or self._aggregation is None:
            raise ValueError("Historical-list provenance did not capture its values.")
        attachments: list[ApplicationProvenanceAttachment] = [
            _input_attachment(self._request, source_document=source_document),
            *(
                _entry_fact_attachment(self._aggregation, source_index)
                for source_index in range(len(self._aggregation.progression))
            ),
            _aggregation_attachment(self._aggregation),
            _root_attachment(
                root_result,
                name="historical_list_result",
                workflow="fixed_three_player_historical_list",
                aggregate_id=f"historical_list/{self._aggregation.list_id}/aggregation",
            ),
        ]
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST,
            attachments=tuple(attachments),
        )


def _comparison_input_attachment(
    request: FixedThreePlayerHistoricalListComparisonRequest,
    *,
    source_document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    document = _serialize_comparison_request(request)

    def build(path: str, _tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        try:
            source_value = resolve_json_pointer(source_document, path)
            retained_value = resolve_json_pointer(document, path)
        except SkatMindValidationError:
            exact_source = False
        else:
            exact_source = exact_v1_json_equal(source_value, retained_value)
        return _list_entry(
            path,
            origin="validated_copy" if exact_source else "rule_derived",
            derivation="validated" if exact_source else "deterministic_rule",
            references=(
                FieldProvenanceSourceReference(
                    reference_type="request",
                    reference_id="historical_list_comparison_input",
                    field_path=path,
                    visibility="public",
                )
                if exact_source
                else _reference(
                    "rule_contract",
                    "fixed_three_player_historical_list_normalization_v1",
                ),
            ),
        )

    return build_complete_provenance_attachment(
        name="historical_list_comparison/input",
        document_role="consumed_input",
        document=document,
        information_use_context=_context("fixed_three_player_historical_list_comparison"),
        entry_builder=build,
    )


def _comparison_source_attachment(
    source_index: int,
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    list_id = str(document["list_id"])
    return build_complete_provenance_attachment(
        name=f"historical_list_comparison/source/{source_index}",
        document_role="result",
        document=document,
        information_use_context=_context("fixed_three_player_historical_list_comparison"),
        entry_builder=lambda path, _tokens: _list_entry(
            path,
            origin="historical_aggregation",
            derivation="exact_aggregate",
            references=(_reference("aggregate", f"historical_list/{list_id}/aggregation"),),
        ),
    )


def _comparison_pair_attachment(
    pair_index: int,
    document: Mapping[str, object],
) -> ApplicationProvenanceAttachment:
    reference_id = str(document["reference_list_id"])
    comparison_id = str(document["comparison_list_id"])

    def build(path: str, tokens: tuple[str, ...]) -> FieldProvenanceEntry:
        origin = "historical_aggregation"
        derivation = "exact_aggregate"
        dependencies: tuple[str, ...] = ()
        if "deltas" in tokens or (tokens and tokens[-1].endswith("_delta")):
            origin = "rule_derived"
            derivation = "deterministic_rule"
        if len(tokens) == 1 and tokens[0].endswith("_count_delta"):
            source_field = tokens[0].removesuffix("_delta")
            dependencies = (
                f"/reference_summary/{source_field}",
                f"/comparison_summary/{source_field}",
            )
        elif len(tokens) == 4 and tokens[0] == "player_comparisons" and tokens[2] == "deltas":
            player_index = tokens[1]
            field_name = tokens[3]
            dependencies = (
                f"/player_comparisons/{player_index}/reference_totals/{field_name}",
                f"/player_comparisons/{player_index}/comparison_totals/{field_name}",
            )
        elif (
            len(tokens) == 3
            and tokens[0] == "player_comparisons"
            and tokens[2] == "rank_position_change"
        ):
            player_index = tokens[1]
            dependencies = (
                f"/player_comparisons/{player_index}/reference_rank",
                f"/player_comparisons/{player_index}/comparison_rank",
            )
        return _list_entry(
            path,
            origin=origin,
            derivation=derivation,
            references=(
                _reference("aggregate", f"historical_list/{reference_id}/aggregation"),
                _reference("aggregate", f"historical_list/{comparison_id}/aggregation"),
            ),
            dependencies=dependencies,
        )

    return build_complete_provenance_attachment(
        name=f"historical_list_comparison/pair/{pair_index}",
        document_role="result",
        document=document,
        information_use_context=_context("fixed_three_player_historical_list_comparison"),
        entry_builder=build,
    )


class HistoricalListComparisonProvenanceCollector:
    """Builds ordered source and pair provenance from one retained comparison."""

    def __init__(self) -> None:
        self._request: FixedThreePlayerHistoricalListComparisonRequest | None = None

    def capture_request(
        self,
        request: FixedThreePlayerHistoricalListComparisonRequest,
    ) -> None:
        self._request = request

    def build_bundle(
        self,
        root_result: Mapping[str, object],
        *,
        source_document: Mapping[str, object],
    ) -> ApplicationProvenanceBundle:
        if self._request is None:
            raise ValueError("Historical-list comparison provenance captured no request.")
        summary = root_result["fixed_three_player_historical_list_comparison_summary"]
        assert isinstance(summary, Mapping)
        sources = summary["source_lists"]
        pairs = summary["comparisons"]
        assert isinstance(sources, list)
        assert isinstance(pairs, list)
        attachments: list[ApplicationProvenanceAttachment] = [
            _comparison_input_attachment(
                self._request,
                source_document=source_document,
            ),
            *(
                _comparison_source_attachment(source_index, source)
                for source_index, source in enumerate(sources)
                if isinstance(source, Mapping)
            ),
            *(
                _comparison_pair_attachment(pair_index, pair)
                for pair_index, pair in enumerate(pairs)
                if isinstance(pair, Mapping)
            ),
            _root_attachment(
                root_result,
                name="historical_list_comparison_result",
                workflow="fixed_three_player_historical_list_comparison",
                aggregate_id="historical_list_comparison",
            ),
        ]
        return ApplicationProvenanceBundle(
            workflow=WorkflowV1.FIXED_THREE_PLAYER_HISTORICAL_LIST_COMPARISON,
            attachments=tuple(attachments),
        )
