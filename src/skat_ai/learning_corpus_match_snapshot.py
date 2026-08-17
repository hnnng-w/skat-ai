from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from skat_ai.errors import SkatAIInvariantError, SkatAIValidationError
from skat_ai.learning_corpus_identity import (
    LEARNING_CORPUS_OBJECT_KINDS,
    _build_match_snapshot_id_v1,
)
from skat_ai.learning_corpus_references import (
    LearningCorpusCommentaryReferenceV1,
    LearningCorpusDecisionReferenceV1,
    LearningCorpusGameReferenceV1,
    LearningCorpusPlayerObservationV1,
    LearningCorpusResponseReferenceV1,
    _build_commentary_reference_v1,
    _build_decision_reference_v1,
    _build_game_reference_identity_v1,
    _build_player_observation_v1,
    _build_response_reference_v1,
    build_learning_corpus_game_content_fingerprint_v1,
)
from skat_ai.match_workspace_contracts import MatchWorkspaceV1
from skat_ai.match_workspace_persistence_codec import (
    resume_match_workspace_document_v1,
)
from skat_ai.match_workspace_persistence_contracts import (
    MATCH_WORKSPACE_DOCUMENT_KIND,
    MATCH_WORKSPACE_PERSISTENCE_VERSION,
    MatchWorkspacePersistenceDocumentV1,
)

LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION = 1

_MATCH_SNAPSHOT_OBJECT_KIND = LEARNING_CORPUS_OBJECT_KINDS[0]


@dataclass(frozen=True, slots=True, kw_only=True, init=False)
class LearningCorpusMatchSnapshotV1:
    """One immutable content-addressed copy of an exact validated Workspace."""

    learning_corpus_match_snapshot_version: int = LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION
    object_kind: str
    match_snapshot_id: str
    match_id: str
    workspace_revision: int
    source_workspace_fingerprint: str
    source_content_fingerprint: str
    workspace: MatchWorkspaceV1
    player_observations: tuple[LearningCorpusPlayerObservationV1, ...]
    game_references: tuple[LearningCorpusGameReferenceV1, ...]
    decision_references: tuple[LearningCorpusDecisionReferenceV1, ...]
    commentary_references: tuple[LearningCorpusCommentaryReferenceV1, ...]
    response_references: tuple[LearningCorpusResponseReferenceV1, ...]

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError(
            "LearningCorpusMatchSnapshotV1 must be constructed by its focused builder."
        )

    @classmethod
    def _from_validated(
        cls,
        *,
        match_snapshot_id: str,
        match_id: str,
        workspace_revision: int,
        source_workspace_fingerprint: str,
        source_content_fingerprint: str,
        workspace: MatchWorkspaceV1,
        player_observations: tuple[LearningCorpusPlayerObservationV1, ...],
        game_references: tuple[LearningCorpusGameReferenceV1, ...],
        decision_references: tuple[LearningCorpusDecisionReferenceV1, ...],
        commentary_references: tuple[LearningCorpusCommentaryReferenceV1, ...],
        response_references: tuple[LearningCorpusResponseReferenceV1, ...],
    ) -> LearningCorpusMatchSnapshotV1:
        value = object.__new__(cls)
        for field_name, field_value in (
            (
                "learning_corpus_match_snapshot_version",
                LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION,
            ),
            ("object_kind", _MATCH_SNAPSHOT_OBJECT_KIND),
            ("match_snapshot_id", match_snapshot_id),
            ("match_id", match_id),
            ("workspace_revision", workspace_revision),
            ("source_workspace_fingerprint", source_workspace_fingerprint),
            ("source_content_fingerprint", source_content_fingerprint),
            ("workspace", workspace),
            ("player_observations", player_observations),
            ("game_references", game_references),
            ("decision_references", decision_references),
            ("commentary_references", commentary_references),
            ("response_references", response_references),
        ):
            object.__setattr__(value, field_name, field_value)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_corpus_match_snapshot_version": (
                self.learning_corpus_match_snapshot_version
            ),
            "object_kind": self.object_kind,
            "match_snapshot_id": self.match_snapshot_id,
            "match_id": self.match_id,
            "workspace_revision": self.workspace_revision,
            "source_workspace_fingerprint": self.source_workspace_fingerprint,
            "source_content_fingerprint": self.source_content_fingerprint,
            "workspace": self.workspace.to_dict(),
            "player_observations": [item.to_dict() for item in self.player_observations],
            "game_references": [item.to_dict() for item in self.game_references],
            "decision_references": [item.to_dict() for item in self.decision_references],
            "commentary_references": [
                item.to_dict() for item in self.commentary_references
            ],
            "response_references": [item.to_dict() for item in self.response_references],
        }


def _match_snapshot_identity_material_v1(
    *,
    source_workspace_fingerprint: str,
    source_content_fingerprint: str,
    workspace: MatchWorkspaceV1,
) -> dict[str, Any]:
    return {
        "learning_corpus_match_snapshot_version": (
            LEARNING_CORPUS_MATCH_SNAPSHOT_VERSION
        ),
        "object_kind": _MATCH_SNAPSHOT_OBJECT_KIND,
        "source_workspace_fingerprint": source_workspace_fingerprint,
        "source_content_fingerprint": source_content_fingerprint,
        "workspace": workspace.to_dict(),
    }


def _require_unique_reference_ids(values: tuple[object, ...], field_name: str) -> None:
    ids = tuple(getattr(value, field_name) for value in values)
    if len(ids) != len(set(ids)):
        raise ValueError(f"Derived {field_name} values must be unique within one Snapshot.")


def _validate_closed_reference_reconciliation_v1(
    *,
    match_snapshot_id: str,
    match_id: str,
    player_observations: tuple[LearningCorpusPlayerObservationV1, ...],
    game_references: tuple[LearningCorpusGameReferenceV1, ...],
    decision_references: tuple[LearningCorpusDecisionReferenceV1, ...],
    commentary_references: tuple[LearningCorpusCommentaryReferenceV1, ...],
    response_references: tuple[LearningCorpusResponseReferenceV1, ...],
) -> None:
    if len(player_observations) != 3:
        raise ValueError("A Match Snapshot must derive exactly three Player observations.")
    _require_unique_reference_ids(player_observations, "player_observation_id")
    _require_unique_reference_ids(game_references, "game_reference_id")
    _require_unique_reference_ids(decision_references, "decision_reference_id")
    _require_unique_reference_ids(commentary_references, "commentary_reference_id")
    _require_unique_reference_ids(response_references, "response_reference_id")

    all_values = (
        *player_observations,
        *game_references,
        *decision_references,
        *commentary_references,
        *response_references,
    )
    if any(value.match_snapshot_id != match_snapshot_id for value in all_values):
        raise ValueError("Every derived reference must be closed to the same Snapshot.")

    games_by_reference_id = {item.game_reference_id: item for item in game_references}
    decisions_by_id = {item.decision_reference_id: item for item in decision_references}
    commentaries_by_id = {
        item.commentary_reference_id: item for item in commentary_references
    }
    decisions_by_game: dict[str, list[str]] = {
        game_reference_id: [] for game_reference_id in games_by_reference_id
    }
    commentaries_by_game: dict[str, list[str]] = {
        game_reference_id: [] for game_reference_id in games_by_reference_id
    }
    responses_by_game: dict[str, list[str]] = {
        game_reference_id: [] for game_reference_id in games_by_reference_id
    }

    for decision in decision_references:
        game = games_by_reference_id.get(decision.game_reference_id)
        if (
            game is None
            or decision.match_id != match_id
            or decision.game_id != game.game_id
            or decision.match_position != game.match_position
        ):
            raise ValueError("Decision references must close to their exact Game reference.")
        decisions_by_game[decision.game_reference_id].append(decision.decision_reference_id)

    for commentary in commentary_references:
        subject = decisions_by_id.get(commentary.subject_decision_reference_id)
        if (
            commentary.game_reference_id not in games_by_reference_id
            or subject is None
            or subject.game_reference_id != commentary.game_reference_id
        ):
            raise ValueError("Commentary references must close to a same-Game Decision.")
        commentaries_by_game[commentary.game_reference_id].append(
            commentary.commentary_reference_id
        )

    for response in response_references:
        commentary = commentaries_by_id.get(response.commentary_reference_id)
        decision = decisions_by_id.get(response.response_decision_reference_id)
        if (
            response.game_reference_id not in games_by_reference_id
            or commentary is None
            or decision is None
            or commentary.game_reference_id != response.game_reference_id
            or decision.game_reference_id != response.game_reference_id
        ):
            raise ValueError(
                "Response references must close to same-Game Commentary and Decision."
            )
        responses_by_game[response.game_reference_id].append(response.response_reference_id)

    for game in game_references:
        if game.match_id != match_id:
            raise ValueError("Game references must retain the Snapshot Match ID.")
        if game.decision_reference_ids != tuple(decisions_by_game[game.game_reference_id]):
            raise ValueError("Game Decision reference IDs do not reconcile.")
        if game.commentary_reference_ids != tuple(
            commentaries_by_game[game.game_reference_id]
        ):
            raise ValueError("Game Commentary reference IDs do not reconcile.")
        if game.response_reference_ids != tuple(responses_by_game[game.game_reference_id]):
            raise ValueError("Game Response reference IDs do not reconcile.")


def _derive_learning_corpus_references_v1(
    workspace: MatchWorkspaceV1,
    *,
    match_snapshot_id: str,
) -> tuple[
    tuple[LearningCorpusPlayerObservationV1, ...],
    tuple[LearningCorpusGameReferenceV1, ...],
    tuple[LearningCorpusDecisionReferenceV1, ...],
    tuple[LearningCorpusCommentaryReferenceV1, ...],
    tuple[LearningCorpusResponseReferenceV1, ...],
]:
    definition = workspace.match_definition
    match_id = definition.match_id
    player_observations = tuple(
        _build_player_observation_v1(
            match_snapshot_id=match_snapshot_id,
            player_id=participant.player_id,
            table_place=participant.table_place,
            player_label=participant.player_label,
            game_platform=definition.game_platform,
            platform_player_id=participant.platform_player_id,
            statistics_snapshot_id=(
                None
                if participant.statistics_snapshot is None
                else participant.statistics_snapshot.snapshot_id
            ),
        )
        for participant in definition.participants
    )

    game_references: list[LearningCorpusGameReferenceV1] = []
    decision_references: list[LearningCorpusDecisionReferenceV1] = []
    commentary_references: list[LearningCorpusCommentaryReferenceV1] = []
    response_references: list[LearningCorpusResponseReferenceV1] = []

    for slot in workspace.slots:
        game = slot.observed_game
        if game is None:
            continue
        game_content_fingerprint = build_learning_corpus_game_content_fingerprint_v1(game)
        game_reference_id = _build_game_reference_identity_v1(
            game_content_fingerprint=game_content_fingerprint,
            match_snapshot_id=match_snapshot_id,
            match_id=match_id,
            match_position=slot.match_position,
            game_id=game.game_id,
        )

        game_decisions: list[LearningCorpusDecisionReferenceV1] = []
        decisions_by_index: dict[int, LearningCorpusDecisionReferenceV1] = {}
        for play in game.plays:
            if play.decision_index in decisions_by_index:
                raise ValueError("Observed Play Decision indexes must be unique.")
            decision = _build_decision_reference_v1(
                match_snapshot_id=match_snapshot_id,
                game_reference_id=game_reference_id,
                match_id=match_id,
                game_id=game.game_id,
                match_position=slot.match_position,
                decision_index=play.decision_index,
                acting_player_id=play.player_id,
            )
            decisions_by_index[play.decision_index] = decision
            game_decisions.append(decision)

        game_commentaries: list[LearningCorpusCommentaryReferenceV1] = []
        commentaries_by_source_id: dict[str, LearningCorpusCommentaryReferenceV1] = {}
        for commentary in game.commentaries:
            if commentary.commentary_id in commentaries_by_source_id:
                raise ValueError("Observed Commentary IDs must be unique within one Game.")
            subject = decisions_by_index.get(commentary.decision_index)
            if subject is None:
                raise ValueError("Observed Commentary must reference one retained Decision.")
            reference = _build_commentary_reference_v1(
                match_snapshot_id=match_snapshot_id,
                game_reference_id=game_reference_id,
                commentary_id=commentary.commentary_id,
                subject_decision_reference_id=subject.decision_reference_id,
            )
            commentaries_by_source_id[commentary.commentary_id] = reference
            game_commentaries.append(reference)

        game_responses: list[LearningCorpusResponseReferenceV1] = []
        source_link_ids: set[str] = set()
        for link in game.response_links:
            if link.link_id in source_link_ids:
                raise ValueError("Observed Response Link IDs must be unique within one Game.")
            source_link_ids.add(link.link_id)
            commentary = commentaries_by_source_id.get(link.commentary_id)
            response_decision = decisions_by_index.get(link.response_decision_index)
            if commentary is None or response_decision is None:
                raise ValueError(
                    "Observed Response Links must close to retained Commentary and Decision."
                )
            game_responses.append(
                _build_response_reference_v1(
                    match_snapshot_id=match_snapshot_id,
                    game_reference_id=game_reference_id,
                    link_id=link.link_id,
                    commentary_reference_id=commentary.commentary_reference_id,
                    response_decision_reference_id=(
                        response_decision.decision_reference_id
                    ),
                )
            )

        game_reference = LearningCorpusGameReferenceV1._from_validated(
            game_reference_id=game_reference_id,
            game_content_fingerprint=game_content_fingerprint,
            match_snapshot_id=match_snapshot_id,
            match_id=match_id,
            match_position=slot.match_position,
            game_id=game.game_id,
            decision_reference_ids=tuple(
                item.decision_reference_id for item in game_decisions
            ),
            commentary_reference_ids=tuple(
                item.commentary_reference_id for item in game_commentaries
            ),
            response_reference_ids=tuple(
                item.response_reference_id for item in game_responses
            ),
        )
        game_references.append(game_reference)
        decision_references.extend(game_decisions)
        commentary_references.extend(game_commentaries)
        response_references.extend(game_responses)

    result = (
        player_observations,
        tuple(game_references),
        tuple(decision_references),
        tuple(commentary_references),
        tuple(response_references),
    )
    _validate_closed_reference_reconciliation_v1(
        match_snapshot_id=match_snapshot_id,
        match_id=match_id,
        player_observations=result[0],
        game_references=result[1],
        decision_references=result[2],
        commentary_references=result[3],
        response_references=result[4],
    )
    return result


def _strictly_verify_source_document_v1(
    document: MatchWorkspacePersistenceDocumentV1,
) -> None:
    try:
        resumed = resume_match_workspace_document_v1(document.to_dict())
    except (SkatAIValidationError, AttributeError, KeyError, TypeError, ValueError) as error:
        path = error.path if isinstance(error, SkatAIValidationError) else ""
        raise SkatAIInvariantError(
            "Internally supplied Match Workspace persistence document is inconsistent.",
            path=path,
        ) from error
    if resumed.document != document or resumed.document.to_dict() != document.to_dict():
        raise SkatAIInvariantError(
            "Strictly resumed Match Workspace persistence document disagreed internally.",
            path="",
        )


def build_learning_corpus_match_snapshot_v1(
    document: MatchWorkspacePersistenceDocumentV1,
) -> LearningCorpusMatchSnapshotV1:
    """Builds one immutable Snapshot from one exact in-memory persistence document."""
    if type(document) is not MatchWorkspacePersistenceDocumentV1:
        raise ValueError(
            "document must be an exact MatchWorkspacePersistenceDocumentV1."
        )
    _strictly_verify_source_document_v1(document)
    workspace = document.workspace
    try:
        match_snapshot_id = _build_match_snapshot_id_v1(
            _match_snapshot_identity_material_v1(
                source_workspace_fingerprint=document.workspace_fingerprint,
                source_content_fingerprint=document.content_fingerprint,
                workspace=workspace,
            )
        )
        references = _derive_learning_corpus_references_v1(
            workspace,
            match_snapshot_id=match_snapshot_id,
        )
        return LearningCorpusMatchSnapshotV1._from_validated(
            match_snapshot_id=match_snapshot_id,
            match_id=workspace.match_definition.match_id,
            workspace_revision=workspace.revision,
            source_workspace_fingerprint=document.workspace_fingerprint,
            source_content_fingerprint=document.content_fingerprint,
            workspace=workspace,
            player_observations=references[0],
            game_references=references[1],
            decision_references=references[2],
            commentary_references=references[3],
            response_references=references[4],
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Learning Corpus Match Snapshot derivation disagreed with its source document.",
            path="/workspace",
        ) from error


def validate_learning_corpus_match_snapshot_v1(
    snapshot: LearningCorpusMatchSnapshotV1,
) -> None:
    """Rebuilds and verifies one internally supplied Match Snapshot."""
    if type(snapshot) is not LearningCorpusMatchSnapshotV1:
        raise ValueError("snapshot must be an exact LearningCorpusMatchSnapshotV1.")
    try:
        source_document = MatchWorkspacePersistenceDocumentV1(
            match_workspace_persistence_version=MATCH_WORKSPACE_PERSISTENCE_VERSION,
            document_kind=MATCH_WORKSPACE_DOCUMENT_KIND,
            workspace_fingerprint=snapshot.source_workspace_fingerprint,
            content_fingerprint=snapshot.source_content_fingerprint,
            workspace=snapshot.workspace,
        )
        rebuilt = build_learning_corpus_match_snapshot_v1(source_document)
    except SkatAIInvariantError:
        raise
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SkatAIInvariantError(
            "Internally supplied Learning Corpus Match Snapshot is inconsistent.",
            path="",
        ) from error
    if rebuilt != snapshot:
        raise SkatAIInvariantError(
            "Learning Corpus Match Snapshot does not equal canonical derivation.",
            path="",
        )
