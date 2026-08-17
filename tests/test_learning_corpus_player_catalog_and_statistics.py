import ast
import hashlib
import json
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest
from test_match_capture_contracts import _participants
from test_match_workspace_contracts import _definition
from test_opponent_statistics import (
    add_valid_exact_counts,
    build_historical_source,
    build_valid_record,
)

import skat_ai
import skat_ai.api.v1 as api_v1
import skat_ai.cli as cli
import skat_ai.learning_corpus_current_snapshots as current_snapshots_module
import skat_ai.learning_corpus_player_catalog as player_catalog_module
import skat_ai.learning_corpus_player_statistics as player_statistics_module
import skat_ai.match_player_statistics_context as context_module
from scripts.validate_generated_outputs_schema import SCENARIOS
from skat_ai.api.v1.contracts import WorkflowV1
from skat_ai.errors import SkatAIValidationError
from skat_ai.learning_corpus_catalog import (
    build_learning_corpus_catalog_v1,
    build_learning_corpus_current_match_selection_v1,
    build_learning_corpus_match_snapshot_catalog_entry_v1,
    create_empty_learning_corpus_catalog_v1,
)
from skat_ai.learning_corpus_identity import (
    LEARNING_CORPUS_PLAYER_IDENTITY_POLICY,
    build_learning_corpus_canonical_json_bytes_v1,
)
from skat_ai.learning_corpus_match_snapshot import (
    build_learning_corpus_match_snapshot_v1,
)
from skat_ai.learning_corpus_persistence_codec import (
    build_learning_corpus_catalog_persistence_document_v1,
)
from skat_ai.learning_corpus_persistence_contracts import (
    LEARNING_CORPUS_PERSISTENCE_VERSION,
    LearningCorpusStoreResumeResultV1,
)
from skat_ai.learning_corpus_player_aliases import (
    LEARNING_CORPUS_PLATFORM_ALIAS_CONFLICT_POLICY,
    LEARNING_CORPUS_PLATFORM_ALIAS_HISTORY_POLICY,
    LEARNING_CORPUS_PLATFORM_ALIAS_RESOLUTION_STATUSES,
    LEARNING_CORPUS_PLATFORM_ALIAS_SOURCES,
    LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
    LearningCorpusPlatformAliasConflictV1,
    LearningCorpusPlatformAliasObservationV1,
    LearningCorpusPlatformAliasResolutionV1,
    resolve_learning_corpus_platform_alias_v1,
)
from skat_ai.learning_corpus_player_catalog import (
    LEARNING_CORPUS_PLAYER_CATALOG_DERIVATION_POLICY,
    LEARNING_CORPUS_PLAYER_CATALOG_PRIVACY_POLICY,
    LEARNING_CORPUS_PLAYER_CATALOG_SOURCE_POLICY,
    LEARNING_CORPUS_PLAYER_CATALOG_VERSION,
    LEARNING_CORPUS_PLAYER_LABEL_HISTORY_POLICY,
    LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION,
    LearningCorpusPlayerCatalogEntryV1,
    LearningCorpusPlayerCatalogV1,
    LearningCorpusPlayerMatchObservationV1,
    build_learning_corpus_player_catalog_v1,
)
from skat_ai.learning_corpus_player_statistics import (
    LEARNING_CORPUS_PLAYER_STATISTICS_COMBINATION_POLICY,
    LEARNING_CORPUS_PLAYER_STATISTICS_EXPLICIT_POLICY,
    LEARNING_CORPUS_PLAYER_STATISTICS_HISTORY_POLICY,
    LEARNING_CORPUS_PLAYER_STATISTICS_LATEST_POLICY,
    LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION,
    LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_MODES,
    LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_STATUSES,
    LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION,
    LEARNING_CORPUS_PLAYER_STATISTICS_TEMPORAL_POLICY,
    LEARNING_CORPUS_PLAYER_STATISTICS_UNAVAILABLE_REASONS,
    LearningCorpusPlayerStatisticsObservationV1,
    LearningCorpusPlayerStatisticsSelectionV1,
    build_learning_corpus_player_statistics_record_fingerprint_v1,
    select_learning_corpus_player_statistics_as_of_v1,
)
from skat_ai.match_player_snapshot import (
    MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION,
    MatchParticipantV1,
    MatchPlayerStatisticsSnapshotV1,
)
from skat_ai.match_player_statistics_context import (
    MATCH_PLAYER_STATISTICS_CONTEXT_VERSION,
    classify_match_player_statistics_temporal_status_v1,
)
from skat_ai.match_workspace_contracts import create_match_workspace_v1
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)
from skat_ai.opponent_statistics import (
    OPPONENT_STATISTICS_SCHEMA_VERSION,
    OpponentStatisticsInput,
    build_opponent_statistics_input,
    build_serializable_opponent_statistics_input,
)
from skat_ai.training_dataset import (
    TRAINING_DATASET_SCHEMA_VERSION,
    TRAINING_FEATURE_GENERATION_VERSION,
    TRAINING_TARGET,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _hash(domain: bytes, value: object) -> str:
    return hashlib.sha256(domain + build_learning_corpus_canonical_json_bytes_v1(value)).hexdigest()


def _record(
    player_id: str,
    *,
    captured_at: str = "2026-07-23T10:00:00Z",
    source_type: str = "online_platform",
    source_name: str = "Example platform",
    source_player_id: str | None = "platform-user",
    player_label: str | None = None,
    games_played: int = 127,
    notes: str | None = "Observed source",
):
    data = build_valid_record()
    data["player_id"] = player_id
    if player_label is None:
        data.pop("player_label", None)
    else:
        data["player_label"] = player_label
    data["games_played"] = games_played
    if source_type == "historical_games":
        data["source"] = build_historical_source()
        data["source"]["source_player_id"] = player_id
    else:
        source = {
            "source_type": source_type,
            "source_name": source_name,
            "captured_at": captured_at,
        }
        if source_player_id is not None:
            source["source_player_id"] = source_player_id
        if notes is not None:
            source["notes"] = notes
        data["source"] = source
    return build_opponent_statistics_input({"schema_version": 1, "records": [data]}).records[0]


def _statistics_snapshot(
    player_id: str,
    snapshot_id: str,
    *,
    observed_at: str = "2026-07-23T10:00:00Z",
    **record_options,
) -> MatchPlayerStatisticsSnapshotV1:
    return MatchPlayerStatisticsSnapshotV1(
        snapshot_id=snapshot_id,
        observed_at=observed_at,
        statistics_record=_record(player_id, **record_options),
    )


def _participant(
    player_id: str,
    table_place: str,
    *,
    label: str | None,
    platform_player_id: str | None,
    statistics_snapshot: MatchPlayerStatisticsSnapshotV1 | None = None,
) -> MatchParticipantV1:
    return MatchParticipantV1(
        player_id=player_id,
        player_label=label,
        platform_player_id=platform_player_id,
        table_place=table_place,
        statistics_snapshot=statistics_snapshot,
    )


def _match_snapshot(
    match_id: str,
    *,
    played_at: str | None = "2026-08-09T18:00:00Z",
    participants: tuple[MatchParticipantV1, ...] | None = None,
    game_platform: str = "EuroSkat",
    title: str | None = None,
):
    definition = _definition(
        match_id=match_id,
        title=title or f"Match {match_id}",
        played_at=played_at,
        game_platform=game_platform,
        external_match_id=f"external-{match_id}",
        participants=(_participants(snapshots=False) if participants is None else participants),
    )
    document = build_match_workspace_persistence_document_v1(create_match_workspace_v1(definition))
    return build_learning_corpus_match_snapshot_v1(document)


def _store(
    *snapshots,
    current=(),
    revision: int = 1,
    orphans: tuple[str, ...] = (),
) -> LearningCorpusStoreResumeResultV1:
    if not snapshots:
        catalog = create_empty_learning_corpus_catalog_v1("corpus-173")
        document = build_learning_corpus_catalog_persistence_document_v1(catalog)
        return LearningCorpusStoreResumeResultV1(
            document=document,
            match_snapshots=(),
            orphan_match_snapshot_ids=orphans,
        )
    entries = tuple(
        build_learning_corpus_match_snapshot_catalog_entry_v1(snapshot) for snapshot in snapshots
    )
    selections = tuple(
        build_learning_corpus_current_match_selection_v1(
            match_id=snapshot.match_id,
            match_snapshot_id=snapshot.match_snapshot_id,
        )
        for snapshot in current
    )
    catalog = build_learning_corpus_catalog_v1(
        corpus_id="corpus-173",
        revision=revision,
        match_snapshots=entries,
        current_matches=selections,
    )
    snapshots_by_id = {item.match_snapshot_id: item for item in snapshots}
    ordered_snapshots = tuple(
        snapshots_by_id[entry.match_snapshot_id] for entry in catalog.match_snapshots
    )
    return LearningCorpusStoreResumeResultV1(
        document=build_learning_corpus_catalog_persistence_document_v1(catalog),
        match_snapshots=ordered_snapshots,
        orphan_match_snapshot_ids=orphans,
    )


def _three_players(
    *,
    player_a_label: str | None = "Alice",
    player_a_platform: str | None = "platform-a",
    player_a_statistics: MatchPlayerStatisticsSnapshotV1 | None = None,
    player_b_id: str = "player-b",
    player_b_label: str | None = None,
    player_b_platform: str | None = "platform-b",
    player_b_statistics: MatchPlayerStatisticsSnapshotV1 | None = None,
) -> tuple[MatchParticipantV1, ...]:
    return (
        _participant(
            "player-a",
            "place_1",
            label=player_a_label,
            platform_player_id=player_a_platform,
            statistics_snapshot=player_a_statistics,
        ),
        _participant(
            player_b_id,
            "place_2",
            label=player_b_label,
            platform_player_id=player_b_platform,
            statistics_snapshot=player_b_statistics,
        ),
        _participant(
            "player-c",
            "place_3",
            label="Carol",
            platform_player_id=None,
        ),
    )


def _catalog_with_player_history(*snapshot_options):
    snapshots = tuple(
        _match_snapshot(
            f"match-{index}",
            participants=_three_players(
                player_a_statistics=_statistics_snapshot(
                    "player-a",
                    f"statistics-{index}",
                    **{
                        key: value
                        for key, value in options.items()
                        if key != "source_match_played_at"
                    },
                )
            ),
            played_at=options.get("source_match_played_at", "2026-08-09T18:00:00Z"),
        )
        for index, options in enumerate(snapshot_options, start=1)
    )
    return build_learning_corpus_player_catalog_v1(_store(*snapshots, current=snapshots))


def test_versions_tuples_reasons_policies_and_fields_are_exact() -> None:
    assert (
        LEARNING_CORPUS_PLAYER_CATALOG_VERSION,
        LEARNING_CORPUS_PLAYER_MATCH_OBSERVATION_VERSION,
        LEARNING_CORPUS_PLATFORM_ALIAS_VERSION,
        LEARNING_CORPUS_PLAYER_STATISTICS_OBSERVATION_VERSION,
        LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_VERSION,
    ) == (1, 1, 1, 1, 1)
    assert LEARNING_CORPUS_PLATFORM_ALIAS_SOURCES == (
        "match_participant",
        "statistics_source",
    )
    assert LEARNING_CORPUS_PLATFORM_ALIAS_RESOLUTION_STATUSES == (
        "not_observed",
        "resolved",
        "conflict",
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_MODES == (
        "latest_unambiguous",
        "explicit_observation",
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_SELECTION_STATUSES == (
        "available",
        "unavailable",
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_UNAVAILABLE_REASONS == (
        "player_not_found",
        "target_time_unavailable",
        "no_statistics_history",
        "no_prior_snapshot",
        "explicit_observation_not_found",
        "explicit_observation_not_before_target",
        "ambiguous_latest_instant",
    )
    assert LEARNING_CORPUS_PLAYER_IDENTITY_POLICY == ("exact_stable_player_ids_without_fuzzy_merge")
    assert LEARNING_CORPUS_PLAYER_CATALOG_SOURCE_POLICY == ("explicit_current_match_snapshots_only")
    assert LEARNING_CORPUS_PLAYER_LABEL_HISTORY_POLICY == (
        "retain_observed_labels_without_canonicalization"
    )
    assert LEARNING_CORPUS_PLATFORM_ALIAS_HISTORY_POLICY == (
        "retain_exact_observed_aliases_without_merge"
    )
    assert LEARNING_CORPUS_PLATFORM_ALIAS_CONFLICT_POLICY == (
        "same_exact_alias_multiple_player_ids_reported"
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_HISTORY_POLICY == (
        "retain_match_bound_observations_without_merge"
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_TEMPORAL_POLICY == ("captured_strictly_before_target")
    assert LEARNING_CORPUS_PLAYER_STATISTICS_LATEST_POLICY == (
        "latest_unambiguous_content_at_latest_eligible_instant"
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_EXPLICIT_POLICY == (
        "explicit_observation_requires_temporal_eligibility"
    )
    assert LEARNING_CORPUS_PLAYER_STATISTICS_COMBINATION_POLICY == (
        "no_merge_no_weighting_no_averaging"
    )
    assert LEARNING_CORPUS_PLAYER_CATALOG_DERIVATION_POLICY == (
        "rebuild_from_strict_store_without_persistence"
    )
    assert LEARNING_CORPUS_PLAYER_CATALOG_PRIVACY_POLICY == (
        "private_local_unredacted_player_history"
    )
    assert tuple(field.name for field in fields(LearningCorpusPlayerCatalogV1)) == (
        "learning_corpus_player_catalog_version",
        "player_catalog_fingerprint",
        "corpus_id",
        "source_catalog_revision",
        "source_catalog_fingerprint",
        "source_catalog_content_fingerprint",
        "current_match_snapshot_ids",
        "retained_match_snapshot_count",
        "current_match_count",
        "orphan_match_snapshot_count",
        "player_count",
        "match_observation_count",
        "statistics_observation_count",
        "players",
        "platform_alias_conflicts",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlayerMatchObservationV1)) == (
        "learning_corpus_player_match_observation_version",
        "player_match_observation_id",
        "player_id",
        "match_id",
        "match_snapshot_id",
        "player_observation_id",
        "workspace_revision",
        "table_place",
        "player_label",
        "game_platform",
        "platform_player_id",
        "match_title",
        "external_match_id",
        "played_at",
        "source_kind",
        "source_title",
        "perspective_player",
        "statistics_snapshot_id",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlayerCatalogEntryV1)) == (
        "learning_corpus_player_catalog_version",
        "player_id",
        "match_observations",
        "platform_alias_observations",
        "statistics_observations",
        "observed_labels",
        "match_ids",
        "current_match_snapshot_ids",
        "match_count",
        "statistics_observation_count",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlatformAliasObservationV1)) == (
        "learning_corpus_platform_alias_version",
        "platform_alias_observation_id",
        "alias_source",
        "player_id",
        "match_id",
        "match_snapshot_id",
        "player_match_observation_id",
        "statistics_observation_id",
        "platform_name",
        "platform_player_id",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlatformAliasConflictV1)) == (
        "learning_corpus_platform_alias_version",
        "platform_alias_conflict_id",
        "platform_name",
        "platform_player_id",
        "player_ids",
        "platform_alias_observation_ids",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlatformAliasResolutionV1)) == (
        "learning_corpus_platform_alias_version",
        "status",
        "platform_name",
        "platform_player_id",
        "player_id",
        "player_ids",
        "platform_alias_observation_ids",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlayerStatisticsObservationV1)) == (
        "learning_corpus_player_statistics_observation_version",
        "statistics_observation_id",
        "statistics_record_fingerprint",
        "player_id",
        "match_id",
        "match_snapshot_id",
        "player_match_observation_id",
        "player_observation_id",
        "statistics_snapshot_id",
        "observed_at",
        "captured_at",
        "source_match_played_at",
        "source_match_temporal_status",
        "eligible_for_source_match_analysis",
        "statistics_record",
    )
    assert tuple(field.name for field in fields(LearningCorpusPlayerStatisticsSelectionV1)) == (
        "learning_corpus_player_statistics_selection_version",
        "status",
        "selection_mode",
        "unavailable_reason",
        "player_id",
        "target_played_at",
        "requested_statistics_observation_id",
        "candidate_observation_ids",
        "selected_observation",
        "equivalent_observation_ids",
        "ambiguous_observation_ids",
    )


def test_empty_catalog_is_deterministic_path_free_and_fingerprinted() -> None:
    source = _store()
    first = build_learning_corpus_player_catalog_v1(source)
    second = build_learning_corpus_player_catalog_v1(source)
    assert first == second
    assert first.corpus_id == "corpus-173"
    assert first.source_catalog_revision == 0
    assert first.source_catalog_fingerprint == source.document.catalog_fingerprint
    assert first.source_catalog_content_fingerprint == source.document.content_fingerprint
    assert first.current_match_snapshot_ids == ()
    assert (
        first.retained_match_snapshot_count,
        first.current_match_count,
        first.orphan_match_snapshot_count,
        first.player_count,
        first.match_observation_count,
        first.statistics_observation_count,
    ) == (0, 0, 0, 0, 0, 0)
    material = first.to_dict()
    del material["player_catalog_fingerprint"]
    assert first.player_catalog_fingerprint == _hash(
        b"skat-ai\0learning_corpus_player_catalog_v1\0",
        material,
    )
    serialized = json.dumps(first.to_dict())
    assert "path" not in serialized.lower()
    assert "profile" not in serialized.lower()


def test_multi_match_catalog_groups_exact_player_ids_and_label_history() -> None:
    first = _match_snapshot(
        "match-b",
        participants=_three_players(player_a_label="Alice"),
    )
    second = _match_snapshot(
        "match-a",
        participants=_three_players(
            player_a_label="ALICE",
            player_b_id="Player-A",
            player_b_label="Alice",
            player_b_platform="different-platform-id",
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(
        _store(first, second, current=(first, second), orphans=("f" * 64,))
    )
    assert catalog.current_match_snapshot_ids == (
        second.match_snapshot_id,
        first.match_snapshot_id,
    )
    assert (
        catalog.retained_match_snapshot_count,
        catalog.current_match_count,
        catalog.orphan_match_snapshot_count,
        catalog.player_count,
        catalog.match_observation_count,
    ) == (2, 2, 1, 4, 6)
    assert tuple(player.player_id for player in catalog.players) == (
        "Player-A",
        "player-a",
        "player-b",
        "player-c",
    )
    player_a = next(player for player in catalog.players if player.player_id == "player-a")
    assert player_a.observed_labels == ("ALICE", "Alice")
    assert player_a.match_ids == ("match-a", "match-b")
    assert player_a.match_count == 2
    other = next(player for player in catalog.players if player.player_id == "Player-A")
    assert other.observed_labels == ("Alice",)
    assert not hasattr(player_a, "canonical_label")


def test_player_match_observation_uses_exact_identity_domain_and_metadata() -> None:
    snapshot = _match_snapshot("match-observation")
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    observation = next(
        player for player in catalog.players if player.player_id == "player-a"
    ).match_observations[0]
    source = snapshot.player_observations[0]
    material = {
        "learning_corpus_player_match_observation_version": 1,
        "match_snapshot_id": snapshot.match_snapshot_id,
        "player_observation_id": source.player_observation_id,
        "player_id": "player-a",
    }
    assert observation.player_match_observation_id == _hash(
        b"skat-ai\0learning_corpus_player_match_observation_v1\0",
        material,
    )
    assert observation.match_title == "Match match-observation"
    assert observation.external_match_id == "external-match-observation"
    assert observation.source_kind == "youtube_video"
    assert observation.source_title == "EuroSkat 36er Standard Match"
    assert observation.perspective_player is True
    assert observation.statistics_snapshot_id is None
    assert "source_url" not in observation.to_dict()


def test_only_explicit_current_snapshot_contributes_and_selection_changes_view() -> None:
    old = _match_snapshot(
        "match-revisions",
        participants=_three_players(
            player_a_label="Old label",
            player_a_statistics=_statistics_snapshot(
                "player-a",
                "old-statistics",
                source_player_id="old-source",
            ),
        ),
    )
    current = _match_snapshot(
        "match-revisions",
        participants=_three_players(
            player_a_label="Current label",
            player_a_statistics=_statistics_snapshot(
                "player-a",
                "current-statistics",
                source_player_id="current-source",
            ),
        ),
    )
    current_catalog = build_learning_corpus_player_catalog_v1(
        _store(old, current, current=(current,), orphans=("e" * 64,))
    )
    old_catalog = build_learning_corpus_player_catalog_v1(
        _store(old, current, current=(old,), orphans=("e" * 64,))
    )
    current_player = next(
        player for player in current_catalog.players if player.player_id == "player-a"
    )
    assert current_catalog.retained_match_snapshot_count == 2
    assert current_catalog.current_match_count == 1
    assert current_catalog.orphan_match_snapshot_count == 1
    assert current_player.observed_labels == ("Current label",)
    assert tuple(
        item.statistics_snapshot_id for item in current_player.statistics_observations
    ) == ("current-statistics",)
    assert current_catalog.player_catalog_fingerprint != old_catalog.player_catalog_fingerprint
    old_player = next(player for player in old_catalog.players if player.player_id == "player-a")
    assert old_player.observed_labels == ("Old label",)


def test_match_and_online_statistics_aliases_are_exact_and_linked() -> None:
    statistics = _statistics_snapshot(
        "player-a",
        "statistics-online",
        source_name="Platform Name",
        source_player_id="Source-ID",
    )
    snapshot = _match_snapshot(
        "match-alias",
        game_platform="platform name",
        participants=_three_players(
            player_a_platform="Participant-ID",
            player_a_statistics=statistics,
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    player = next(item for item in catalog.players if item.player_id == "player-a")
    assert tuple(
        (
            item.platform_name,
            item.platform_player_id,
            item.alias_source,
        )
        for item in player.platform_alias_observations
    ) == (
        ("Platform Name", "Source-ID", "statistics_source"),
        ("platform name", "Participant-ID", "match_participant"),
    )
    participant_alias, source_alias = (
        next(item for item in player.platform_alias_observations if item.alias_source == source)
        for source in ("match_participant", "statistics_source")
    )
    assert participant_alias.statistics_observation_id is None
    assert source_alias.statistics_observation_id == (
        player.statistics_observations[0].statistics_observation_id
    )
    source_material = source_alias.to_dict()
    del source_material["platform_alias_observation_id"]
    assert source_alias.platform_alias_observation_id == _hash(
        b"skat-ai\0learning_corpus_platform_alias_observation_v1\0",
        source_material,
    )
    assert (
        resolve_learning_corpus_platform_alias_v1(
            catalog,
            platform_name="Platform Name",
            platform_player_id="Source-ID",
        ).status
        == "resolved"
    )
    assert (
        resolve_learning_corpus_platform_alias_v1(
            catalog,
            platform_name="platform name",
            platform_player_id="Source-ID",
        ).status
        == "not_observed"
    )


@pytest.mark.parametrize("source_type", ("manual_entry", "historical_games"))
def test_manual_and_historical_statistics_sources_create_no_alias(
    source_type: str,
) -> None:
    if source_type == "historical_games":
        statistics = _statistics_snapshot(
            "player-a",
            "statistics-history",
            observed_at="2026-07-20T17:00:00Z",
            source_type=source_type,
        )
    else:
        statistics = _statistics_snapshot(
            "player-a",
            "statistics-manual",
            source_type=source_type,
            source_player_id="manual-source-id",
        )
    snapshot = _match_snapshot(
        f"match-{source_type}",
        participants=_three_players(
            player_a_platform=None,
            player_a_statistics=statistics,
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    player = next(item for item in catalog.players if item.player_id == "player-a")
    assert player.platform_alias_observations == ()
    assert len(player.statistics_observations) == 1


def test_online_statistics_without_source_player_id_creates_no_source_alias() -> None:
    snapshot = _match_snapshot(
        "match-online-without-source-id",
        participants=_three_players(
            player_a_platform=None,
            player_a_statistics=_statistics_snapshot(
                "player-a",
                "statistics-online-without-source-id",
                source_player_id=None,
            ),
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    player = next(item for item in catalog.players if item.player_id == "player-a")
    assert player.platform_alias_observations == ()


def test_alias_conflict_is_canonical_and_never_merges_players() -> None:
    first = _match_snapshot(
        "match-conflict-a",
        participants=_three_players(player_a_platform="shared-id"),
    )
    second = _match_snapshot(
        "match-conflict-b",
        participants=_three_players(
            player_a_platform=None,
            player_b_platform="shared-id",
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(
        _store(first, second, current=(first, second))
    )
    assert len(catalog.platform_alias_conflicts) == 1
    conflict = catalog.platform_alias_conflicts[0]
    assert conflict.platform_name == "EuroSkat"
    assert conflict.platform_player_id == "shared-id"
    assert conflict.player_ids == ("player-a", "player-b")
    assert conflict.platform_alias_observation_ids == tuple(
        sorted(conflict.platform_alias_observation_ids)
    )
    material = conflict.to_dict()
    del material["platform_alias_conflict_id"]
    assert conflict.platform_alias_conflict_id == _hash(
        b"skat-ai\0learning_corpus_platform_alias_conflict_v1\0",
        material,
    )
    resolution = resolve_learning_corpus_platform_alias_v1(
        catalog,
        platform_name="EuroSkat",
        platform_player_id="shared-id",
    )
    assert resolution.status == "conflict"
    assert resolution.player_id is None
    assert resolution.player_ids == ("player-a", "player-b")
    assert len(catalog.players) == 3
    assert resolve_learning_corpus_platform_alias_v1(
        catalog,
        platform_name="EuroSkat",
        platform_player_id="missing",
    ).to_dict() == {
        "learning_corpus_platform_alias_version": 1,
        "status": "not_observed",
        "platform_name": "EuroSkat",
        "platform_player_id": "missing",
        "player_id": None,
        "player_ids": [],
        "platform_alias_observation_ids": [],
    }


def test_repeated_consistent_alias_resolves_and_platform_name_separates_keys() -> None:
    first = _match_snapshot(
        "match-alias-repeat-a",
        participants=_three_players(player_a_platform="same-id"),
        game_platform="Platform A",
    )
    second = _match_snapshot(
        "match-alias-repeat-b",
        participants=_three_players(player_a_platform="same-id"),
        game_platform="Platform A",
    )
    third = _match_snapshot(
        "match-alias-repeat-c",
        participants=_three_players(player_a_platform="same-id"),
        game_platform="Platform B",
    )
    catalog = build_learning_corpus_player_catalog_v1(
        _store(first, second, third, current=(first, second, third))
    )
    resolution = resolve_learning_corpus_platform_alias_v1(
        catalog,
        platform_name="Platform A",
        platform_player_id="same-id",
    )
    assert resolution.status == "resolved"
    assert resolution.player_id == "player-a"
    assert len(resolution.platform_alias_observation_ids) == 2
    assert catalog.platform_alias_conflicts == ()
    assert (
        resolve_learning_corpus_platform_alias_v1(
            catalog,
            platform_name="Platform B",
            platform_player_id="same-id",
        ).status
        == "resolved"
    )


def test_statistics_record_fingerprint_is_complete_defensive_and_domain_separated() -> None:
    record = _record("player-a")
    repeated = build_learning_corpus_player_statistics_record_fingerprint_v1(record)
    exact_record = build_serializable_opponent_statistics_input(
        OpponentStatisticsInput(
            schema_version=1,
            records=(record,),
        )
    )["opponent_statistics_input"]["records"][0]
    assert repeated == _hash(
        b"skat-ai\0learning_corpus_player_statistics_record_v1\0",
        exact_record,
    )
    assert repeated == build_learning_corpus_player_statistics_record_fingerprint_v1(
        _record("player-a")
    )
    changed = (
        _record("player-a", games_played=128),
        _record("player-a", source_type="manual_entry"),
        _record("player-a", source_name="Different source"),
        _record("player-a", source_player_id="different-id"),
        _record("player-a", captured_at="2026-07-24T10:00:00Z"),
        _record("player-a", notes="Different notes"),
        _record("player-a", player_label="Source label"),
    )
    assert all(
        build_learning_corpus_player_statistics_record_fingerprint_v1(item) != repeated
        for item in changed
    )
    with pytest.raises(ValueError, match="exact OpponentStatisticsRecord"):
        build_learning_corpus_player_statistics_record_fingerprint_v1(object())

    percentage_source = build_valid_record()
    percentage_source["player_id"] = "player-a"
    percentage_source.pop("player_label", None)
    changed_percentage_source = json.loads(json.dumps(percentage_source))
    changed_percentage_source["statistics"]["solo_games_won_percent"] = 59
    percentage_records = tuple(
        build_opponent_statistics_input({"schema_version": 1, "records": [item]}).records[0]
        for item in (percentage_source, changed_percentage_source)
    )
    assert build_learning_corpus_player_statistics_record_fingerprint_v1(
        percentage_records[0]
    ) != build_learning_corpus_player_statistics_record_fingerprint_v1(percentage_records[1])

    exact_count_source = json.loads(json.dumps(percentage_source))
    add_valid_exact_counts(exact_count_source)
    changed_exact_count_source = json.loads(json.dumps(exact_count_source))
    changed_exact_count_source["exact_counts"]["solo_games_won"] = 24
    exact_count_records = tuple(
        build_opponent_statistics_input({"schema_version": 1, "records": [item]}).records[0]
        for item in (exact_count_source, changed_exact_count_source)
    )
    assert build_learning_corpus_player_statistics_record_fingerprint_v1(
        exact_count_records[0]
    ) != build_learning_corpus_player_statistics_record_fingerprint_v1(exact_count_records[1])

    historical_source = build_valid_record()
    historical_source["player_id"] = "player-a"
    historical_source.pop("player_label", None)
    historical_source["source"] = build_historical_source()
    historical_source["source"]["source_player_id"] = "player-a"
    changed_historical_source = json.loads(json.dumps(historical_source))
    changed_historical_source["source"]["historical_aggregation"]["dataset_id"] = "changed-dataset"
    historical_records = tuple(
        build_opponent_statistics_input({"schema_version": 1, "records": [item]}).records[0]
        for item in (historical_source, changed_historical_source)
    )
    assert build_learning_corpus_player_statistics_record_fingerprint_v1(
        historical_records[0]
    ) != build_learning_corpus_player_statistics_record_fingerprint_v1(historical_records[1])


def test_statistics_observation_retains_exact_record_identity_and_temporal_status() -> None:
    statistics = _statistics_snapshot(
        "player-a",
        "statistics-offset",
        observed_at="2026-07-23T12:00:00+02:00",
        captured_at="2026-07-23T10:00:00Z",
        player_label="Source Alice",
    )
    snapshot = _match_snapshot(
        "match-statistics",
        played_at="2026-07-23T10:00:00Z",
        participants=_three_players(
            player_a_label=None,
            player_a_statistics=statistics,
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    player = next(item for item in catalog.players if item.player_id == "player-a")
    observation = player.statistics_observations[0]
    assert observation.observed_at == "2026-07-23T12:00:00+02:00"
    assert observation.captured_at == "2026-07-23T10:00:00Z"
    assert observation.source_match_played_at == "2026-07-23T10:00:00Z"
    assert observation.source_match_temporal_status == "captured_not_before_match"
    assert observation.eligible_for_source_match_analysis is False
    assert observation.statistics_record == statistics.statistics_record
    assert observation.statistics_record is not statistics.statistics_record
    assert player.observed_labels == ("Source Alice",)
    identity_material = {
        "learning_corpus_player_statistics_observation_version": 1,
        "match_snapshot_id": snapshot.match_snapshot_id,
        "player_id": "player-a",
        "statistics_snapshot_id": "statistics-offset",
        "observed_at": "2026-07-23T12:00:00+02:00",
        "statistics_record_fingerprint": observation.statistics_record_fingerprint,
    }
    assert observation.statistics_observation_id == _hash(
        b"skat-ai\0learning_corpus_player_statistics_observation_v1\0",
        identity_material,
    )
    assert "normalized_profile" not in observation.to_dict()


@pytest.mark.parametrize(
    ("played_at", "expected_status", "eligible"),
    (
        (None, "match_time_unavailable", False),
        ("2026-07-23T10:00:01Z", "eligible", True),
        ("2026-07-23T09:59:59Z", "captured_not_before_match", False),
    ),
)
def test_statistics_observation_uses_shared_source_match_temporal_status(
    played_at: str | None,
    expected_status: str,
    eligible: bool,
) -> None:
    snapshot = _match_snapshot(
        f"match-temporal-{expected_status}",
        played_at=played_at,
        participants=_three_players(
            player_a_statistics=_statistics_snapshot(
                "player-a",
                f"statistics-{expected_status}",
            )
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    observation = next(
        player for player in catalog.players if player.player_id == "player-a"
    ).statistics_observations[0]
    assert observation.source_match_temporal_status == expected_status
    assert observation.eligible_for_source_match_analysis is eligible


@pytest.mark.parametrize(
    ("captured_at", "played_at", "expected"),
    (
        ("2026-07-23T10:00:00Z", None, "match_time_unavailable"),
        ("2026-07-23T10:00:00Z", "2026-07-23T10:00:01Z", "eligible"),
        (
            "2026-07-23T10:00:00Z",
            "2026-07-23T12:00:00+02:00",
            "captured_not_before_match",
        ),
        (
            "2026-07-23T10:00:01Z",
            "2026-07-23T10:00:00Z",
            "captured_not_before_match",
        ),
    ),
)
def test_temporal_helper_is_strict_offset_aware_and_profile_free(
    monkeypatch,
    captured_at: str,
    played_at: str | None,
    expected: str,
) -> None:
    monkeypatch.setattr(
        context_module,
        "derive_opponent_profile",
        lambda *_args, **_kwargs: pytest.fail("Profile derivation is forbidden."),
    )
    assert (
        classify_match_player_statistics_temporal_status_v1(
            captured_at=captured_at,
            played_at=played_at,
        )
        == expected
    )


def test_latest_selection_status_precedence_and_strict_boundary() -> None:
    catalog = _catalog_with_player_history(
        {
            "observed_at": "2026-07-20T10:00:00Z",
            "captured_at": "2026-07-20T10:00:00Z",
        },
        {
            "observed_at": "2026-07-23T12:00:00+02:00",
            "captured_at": "2026-07-23T10:00:00Z",
        },
    )
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="missing",
            target_played_at="2026-08-01T00:00:00Z",
            selection_mode="latest_unambiguous",
        ).unavailable_reason
        == "player_not_found"
    )
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="missing",
            target_played_at=None,
            selection_mode="latest_unambiguous",
        ).unavailable_reason
        == "player_not_found"
    )
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="missing",
            target_played_at="malformed",
            selection_mode="latest_unambiguous",
        ).unavailable_reason
        == "player_not_found"
    )
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at=None,
            selection_mode="latest_unambiguous",
        ).unavailable_reason
        == "target_time_unavailable"
    )
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-b",
            target_played_at="2026-08-01T00:00:00Z",
            selection_mode="latest_unambiguous",
        ).unavailable_reason
        == "no_statistics_history"
    )
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at="2026-07-20T10:00:00Z",
            selection_mode="latest_unambiguous",
        ).unavailable_reason
        == "no_prior_snapshot"
    )
    equal_offset = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-23T12:00:00+02:00",
        selection_mode="latest_unambiguous",
    )
    assert equal_offset.status == "available"
    assert equal_offset.selected_observation.captured_at == "2026-07-20T10:00:00Z"
    latest = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-23T10:00:01Z",
        selection_mode="latest_unambiguous",
    )
    assert latest.selected_observation.captured_at == "2026-07-23T10:00:00Z"
    assert latest.candidate_observation_ids == tuple(
        item.statistics_observation_id
        for item in next(
            player for player in catalog.players if player.player_id == "player-a"
        ).statistics_observations
    )
    with pytest.raises(ValueError, match="valid RFC 3339"):
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at="invalid",
            selection_mode="latest_unambiguous",
        )
    with pytest.raises(ValueError, match="non-empty, non-padded string"):
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at=1,
            selection_mode="latest_unambiguous",
        )


def test_same_instant_exact_equivalents_choose_lexical_representative() -> None:
    catalog = _catalog_with_player_history(
        {
            "observed_at": "2026-07-23T10:00:00Z",
            "captured_at": "2026-07-23T10:00:00Z",
        },
        {
            "observed_at": "2026-07-23T12:00:00+02:00",
            "captured_at": "2026-07-23T10:00:00Z",
        },
    )
    result = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-24T00:00:00Z",
        selection_mode="latest_unambiguous",
    )
    assert result.status == "available"
    assert len(result.equivalent_observation_ids) == 2
    assert result.equivalent_observation_ids == tuple(sorted(result.equivalent_observation_ids))
    assert (
        result.selected_observation.statistics_observation_id
        == (result.equivalent_observation_ids[0])
    )


def test_latest_same_instant_content_ambiguity_has_no_older_fallback() -> None:
    catalog = _catalog_with_player_history(
        {
            "observed_at": "2026-07-20T10:00:00Z",
            "captured_at": "2026-07-20T10:00:00Z",
        },
        {
            "observed_at": "2026-07-23T10:00:00Z",
            "captured_at": "2026-07-23T10:00:00Z",
            "games_played": 127,
        },
        {
            "observed_at": "2026-07-23T12:00:00+02:00",
            "captured_at": "2026-07-23T10:00:00Z",
            "games_played": 128,
        },
    )
    player = next(item for item in catalog.players if item.player_id == "player-a")
    result = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-24T00:00:00Z",
        selection_mode="latest_unambiguous",
    )
    assert result.status == "unavailable"
    assert result.unavailable_reason == "ambiguous_latest_instant"
    assert result.selected_observation is None
    assert len(result.candidate_observation_ids) == 3
    assert set(result.ambiguous_observation_ids) == {
        item.statistics_observation_id
        for item in player.statistics_observations
        if item.captured_at != "2026-07-20T10:00:00Z"
    }
    assert player.statistics_observations[0].statistics_observation_id not in (
        result.ambiguous_observation_ids
    )


def test_explicit_selection_resolves_ambiguity_but_never_time_boundary() -> None:
    catalog = _catalog_with_player_history(
        {
            "observed_at": "2026-07-23T10:00:00Z",
            "captured_at": "2026-07-23T10:00:00Z",
            "games_played": 127,
        },
        {
            "observed_at": "2026-07-23T12:00:00+02:00",
            "captured_at": "2026-07-23T10:00:00Z",
            "games_played": 128,
        },
    )
    player = next(item for item in catalog.players if item.player_id == "player-a")
    requested = player.statistics_observations[1]
    available = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-24T00:00:00Z",
        selection_mode="explicit_observation",
        statistics_observation_id=requested.statistics_observation_id,
    )
    assert available.status == "available"
    assert available.selected_observation is requested
    assert available.equivalent_observation_ids == ()
    equal = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-23T10:00:00Z",
        selection_mode="explicit_observation",
        statistics_observation_id=requested.statistics_observation_id,
    )
    assert equal.unavailable_reason == "explicit_observation_not_before_target"
    later = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-07-23T09:59:59Z",
        selection_mode="explicit_observation",
        statistics_observation_id=requested.statistics_observation_id,
    )
    assert later.unavailable_reason == "explicit_observation_not_before_target"
    assert (
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at="2026-07-24T00:00:00Z",
            selection_mode="explicit_observation",
            statistics_observation_id="f" * 64,
        ).unavailable_reason
        == "explicit_observation_not_found"
    )
    other_player_observation = next(
        item for item in catalog.players if item.player_id == "player-b"
    ).statistics_observations
    assert other_player_observation == ()
    with pytest.raises(ValueError, match="requires one observation ID"):
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at="2026-07-24T00:00:00Z",
            selection_mode="explicit_observation",
        )
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        select_learning_corpus_player_statistics_as_of_v1(
            catalog,
            player_id="player-a",
            target_played_at="2026-07-24T00:00:00Z",
            selection_mode="explicit_observation",
            statistics_observation_id="not-a-hash",
        )


def test_explicit_observation_must_belong_to_selected_player() -> None:
    snapshot = _match_snapshot(
        "match-explicit-owner",
        participants=_three_players(
            player_a_statistics=_statistics_snapshot(
                "player-a",
                "statistics-owner-a",
            ),
            player_b_statistics=_statistics_snapshot(
                "player-b",
                "statistics-owner-b",
            ),
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    player_b = next(item for item in catalog.players if item.player_id == "player-b")
    result = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-08-01T00:00:00Z",
        selection_mode="explicit_observation",
        statistics_observation_id=(player_b.statistics_observations[0].statistics_observation_id),
    )
    assert result.unavailable_reason == "explicit_observation_not_found"


def test_source_match_ineligible_observation_can_be_selected_for_later_target() -> None:
    catalog = _catalog_with_player_history(
        {
            "observed_at": "2026-07-23T10:00:00Z",
            "captured_at": "2026-07-23T10:00:00Z",
            "source_match_played_at": "2026-07-23T10:00:00Z",
        }
    )
    observation = next(
        player for player in catalog.players if player.player_id == "player-a"
    ).statistics_observations[0]
    assert observation.source_match_temporal_status == "captured_not_before_match"
    result = select_learning_corpus_player_statistics_as_of_v1(
        catalog,
        player_id="player-a",
        target_played_at="2026-08-01T00:00:00Z",
        selection_mode="latest_unambiguous",
    )
    assert result.status == "available"
    assert result.selected_observation is observation


def test_values_are_frozen_slotted_and_defensively_serialized() -> None:
    snapshot = _match_snapshot(
        "match-defensive",
        participants=_three_players(
            player_a_statistics=_statistics_snapshot(
                "player-a",
                "statistics-defensive",
            )
        ),
    )
    catalog = build_learning_corpus_player_catalog_v1(_store(snapshot, current=(snapshot,)))
    player = next(item for item in catalog.players if item.player_id == "player-a")
    values = (
        catalog,
        player,
        player.match_observations[0],
        player.platform_alias_observations[0],
        player.statistics_observations[0],
        resolve_learning_corpus_platform_alias_v1(
            catalog,
            platform_name="EuroSkat",
            platform_player_id="platform-a",
        ),
    )
    assert all(not hasattr(value, "__dict__") for value in values)
    with pytest.raises(FrozenInstanceError):
        catalog.player_count = 0
    first = catalog.to_dict()
    first["players"][0]["match_observations"][0]["match_title"] = "Changed"
    first["players"][0]["statistics_observations"][0]["statistics_record"]["games_played"] = 1
    assert catalog.to_dict()["players"][0]["match_observations"][0]["match_title"] != "Changed"
    assert (
        catalog.to_dict()["players"][0]["statistics_observations"][0]["statistics_record"][
            "games_played"
        ]
        == 127
    )


def test_build_strictly_revalidates_source_catalog_fingerprints() -> None:
    snapshot = _match_snapshot("match-tampered-store")
    store = _store(snapshot, current=(snapshot,))
    object.__setattr__(store.document, "catalog_fingerprint", "0" * 64)
    with pytest.raises(SkatAIValidationError, match="catalog_fingerprint"):
        build_learning_corpus_player_catalog_v1(store)


def test_build_is_in_memory_bounded_and_does_not_mutate_source(
    monkeypatch,
) -> None:
    snapshots = (
        _match_snapshot(
            "match-count-a",
            participants=_three_players(
                player_a_statistics=_statistics_snapshot(
                    "player-a",
                    "statistics-count-a",
                )
            ),
        ),
        _match_snapshot("match-count-b"),
    )
    store = _store(*snapshots, current=snapshots)
    before = store.to_dict()
    match_calls = 0
    store_validation_calls = 0
    document_resume_calls = 0
    statistics_prepare_calls = 0
    catalog_fingerprint_calls = 0
    original_match_builder = player_catalog_module._build_player_match_observation_v1
    original_store_validation = LearningCorpusStoreResumeResultV1._validate_structure
    original_document_resume = current_snapshots_module.resume_learning_corpus_catalog_document_v1
    original_statistics_prepare = player_statistics_module._prepare_statistics_record_v1
    original_identifier = player_catalog_module._build_identifier

    def count_match(*args, **kwargs):
        nonlocal match_calls
        match_calls += 1
        return original_match_builder(*args, **kwargs)

    def count_store_validation(self, *args, **kwargs):
        nonlocal store_validation_calls
        store_validation_calls += 1
        return original_store_validation(self, *args, **kwargs)

    def count_document_resume(*args, **kwargs):
        nonlocal document_resume_calls
        document_resume_calls += 1
        return original_document_resume(*args, **kwargs)

    def count_statistics_prepare(*args, **kwargs):
        nonlocal statistics_prepare_calls
        statistics_prepare_calls += 1
        return original_statistics_prepare(*args, **kwargs)

    def count_identifier(domain, value):
        nonlocal catalog_fingerprint_calls
        if domain == player_catalog_module._PLAYER_CATALOG_FINGERPRINT_DOMAIN:
            catalog_fingerprint_calls += 1
        return original_identifier(domain, value)

    monkeypatch.setattr(
        player_catalog_module,
        "_build_player_match_observation_v1",
        count_match,
    )
    monkeypatch.setattr(
        LearningCorpusStoreResumeResultV1,
        "_validate_structure",
        count_store_validation,
    )
    monkeypatch.setattr(
        current_snapshots_module,
        "resume_learning_corpus_catalog_document_v1",
        count_document_resume,
    )
    monkeypatch.setattr(
        player_statistics_module,
        "_prepare_statistics_record_v1",
        count_statistics_prepare,
    )
    monkeypatch.setattr(
        player_catalog_module,
        "_build_identifier",
        count_identifier,
    )
    monkeypatch.setattr(
        "builtins.open",
        lambda *_args, **_kwargs: pytest.fail("Player Catalog build must perform no I/O."),
    )
    catalog = build_learning_corpus_player_catalog_v1(store)
    assert match_calls == 6
    assert store_validation_calls == 1
    assert document_resume_calls == 1
    assert statistics_prepare_calls == 1
    assert catalog_fingerprint_calls == 1
    assert catalog.match_observation_count == 6
    assert catalog.statistics_observation_count == 1
    assert store.to_dict() == before


def test_new_modules_have_no_cli_browser_analysis_dataset_or_api_imports() -> None:
    forbidden = (
        "skat_ai.api",
        "skat_ai.application",
        "skat_ai.capture_web",
        "skat_ai.cli",
        "skat_ai.match_analysis",
        "skat_ai.training_dataset",
    )
    paths = (
        PROJECT_ROOT / "src/skat_ai/learning_corpus_current_snapshots.py",
        PROJECT_ROOT / "src/skat_ai/learning_corpus_player_catalog.py",
        PROJECT_ROOT / "src/skat_ai/learning_corpus_player_aliases.py",
        PROJECT_ROOT / "src/skat_ai/learning_corpus_player_statistics.py",
    )
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = ()
            if isinstance(node, ast.Import):
                modules = tuple(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                modules = (node.module,)
            for module in modules:
                if module.startswith(forbidden):
                    violations.append((path.name, node.lineno, module))
    assert violations == []


def test_compatibility_baselines_and_public_boundaries_remain_unchanged() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    assert pyproject["project"]["version"] == "0.15.0"
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["scripts"] == {"skat-ai": "skat_ai.cli:main"}
    assert LEARNING_CORPUS_PERSISTENCE_VERSION == 1
    assert MATCH_PLAYER_STATISTICS_SNAPSHOT_VERSION == 1
    assert MATCH_PLAYER_STATISTICS_CONTEXT_VERSION == 1
    assert OPPONENT_STATISTICS_SCHEMA_VERSION == 1
    assert TRAINING_DATASET_SCHEMA_VERSION == 1
    assert TRAINING_FEATURE_GENERATION_VERSION == 1
    assert TRAINING_TARGET == "actual_card_played"
    assert len(WorkflowV1) == 7
    assert len(SCENARIOS) == 85
    assert len(tuple((PROJECT_ROOT / "schemas").glob("*.schema.json"))) == 63
    assert len(tuple((PROJECT_ROOT / "src/skat_ai/schema_resources").glob("*.schema.json"))) == 63
    assert len(tuple((PROJECT_ROOT / "examples").glob("session_*.json"))) == 6
    assert not tuple((PROJECT_ROOT / "schemas").glob("*player_catalog*.schema.json"))
    for namespace in (skat_ai, api_v1, cli):
        assert not hasattr(namespace, "LearningCorpusPlayerCatalogV1")
        assert not hasattr(
            namespace,
            "select_learning_corpus_player_statistics_as_of_v1",
        )
