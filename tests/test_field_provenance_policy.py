from dataclasses import FrozenInstanceError

import pytest

from skat_ai.errors import SkatAIInformationPolicyError, SkatAIValidationError
from skat_ai.field_provenance import (
    FieldProvenanceEntry,
    FieldProvenanceLedger,
    FieldProvenanceSourceReference,
    build_public_serializable_field_provenance_ledger,
)
from skat_ai.field_provenance_policy import (
    INFORMATION_USE_CONTEXT_PERSPECTIVE_SIDES,
    INFORMATION_USE_CONTEXT_STAGES,
    InformationUseContext,
    build_serializable_information_use_context,
    is_field_provenance_entry_available,
    redact_field_provenance_ledger_for_public_output,
    validate_field_provenance_entry_use,
)


def _entry(
    path: str,
    *,
    visibility: str = "public",
    available_from: str = "request_start",
    decision_index: int | None = None,
    event_index: int | None = None,
    perspective_player_id: str | None = None,
    source_references: tuple[FieldProvenanceSourceReference, ...] = (),
    dependency_paths: tuple[str, ...] = (),
) -> FieldProvenanceEntry:
    return FieldProvenanceEntry(
        field_path=path,
        coverage_kind="field",
        origin="caller_supplied",
        visibility=visibility,
        available_from=available_from,
        available_from_decision_index=decision_index,
        available_from_event_index=event_index,
        derivation="direct",
        source_references=source_references,
        dependency_paths=dependency_paths,
        subject_player_id=None,
        perspective_player_id=perspective_player_id,
    )


def _context(
    stage: str,
    *,
    player_id: str | None = None,
    side: str | None = None,
    decision_index: int | None = None,
    event_index: int | None = None,
) -> InformationUseContext:
    return InformationUseContext(
        workflow="position_analysis",
        stage=stage,
        perspective_player_id=player_id,
        perspective_side=side,
        decision_index=decision_index,
        event_index=event_index,
    )


def test_information_use_context_constants_are_canonical() -> None:
    assert INFORMATION_USE_CONTEXT_STAGES == (
        "request_start",
        "decision_time",
        "after_actual_play",
        "game_end",
        "offline_review",
        "engine_internal",
    )
    assert INFORMATION_USE_CONTEXT_PERSPECTIVE_SIDES == ("declarer", "defenders")


@pytest.mark.parametrize("stage", INFORMATION_USE_CONTEXT_STAGES)
def test_information_use_context_supports_every_stage_and_is_immutable(stage: str) -> None:
    context = _context(stage)
    assert context.stage == stage
    with pytest.raises(FrozenInstanceError):
        context.stage = "game_end"  # type: ignore[misc]
    assert not hasattr(context, "__dict__")


@pytest.mark.parametrize("workflow", ("", " workflow", "workflow ", 1, None))
def test_information_use_context_rejects_invalid_workflow(workflow: object) -> None:
    with pytest.raises(SkatAIValidationError) as exc_info:
        InformationUseContext(
            workflow=workflow,  # type: ignore[arg-type]
            stage="request_start",
            perspective_player_id=None,
            perspective_side=None,
            decision_index=None,
            event_index=None,
        )
    assert getattr(exc_info.value, "path", None) == "workflow"


@pytest.mark.parametrize("index", (-1, True, "1", 1.5))
def test_information_use_context_rejects_invalid_indexes(index: object) -> None:
    with pytest.raises(SkatAIValidationError):
        _context("decision_time", decision_index=index)  # type: ignore[arg-type]


def test_public_and_private_visibility_rules() -> None:
    assert is_field_provenance_entry_available(
        _entry("/public"), _context("request_start")
    )
    local = _entry(
        "/local", visibility="local_private", perspective_player_id="player-1"
    )
    assert is_field_provenance_entry_available(
        local, _context("decision_time", player_id="player-1")
    )
    assert not is_field_provenance_entry_available(
        local, _context("decision_time", player_id="player-2")
    )
    assert is_field_provenance_entry_available(
        _entry("/declarer", visibility="declarer_private"),
        _context("decision_time", side="declarer"),
    )
    assert not is_field_provenance_entry_available(
        _entry("/declarer", visibility="declarer_private"),
        _context("decision_time", side="defenders"),
    )
    assert is_field_provenance_entry_available(
        _entry("/defenders", visibility="defender_private"),
        _context("decision_time", side="defenders"),
    )
    assert not is_field_provenance_entry_available(
        _entry("/defenders", visibility="defender_private"),
        _context("decision_time", side="declarer"),
    )


@pytest.mark.parametrize("stage", ("game_end", "offline_review", "engine_internal"))
def test_post_game_only_visibility_allows_only_post_game_stages(stage: str) -> None:
    entry = _entry(
        "/post-game", visibility="post_game_only", available_from="game_end"
    )
    assert is_field_provenance_entry_available(entry, _context(stage))


@pytest.mark.parametrize("stage", ("request_start", "decision_time", "after_actual_play"))
def test_post_game_only_visibility_rejects_earlier_stages(stage: str) -> None:
    entry = _entry(
        "/post-game", visibility="post_game_only", available_from="game_end"
    )
    assert not is_field_provenance_entry_available(entry, _context(stage))


def test_engine_private_visibility_is_internal_only() -> None:
    entry = _entry("/engine", visibility="engine_private")
    for stage in INFORMATION_USE_CONTEXT_STAGES:
        expected = stage == "engine_internal"
        assert is_field_provenance_entry_available(entry, _context(stage)) is expected


@pytest.mark.parametrize(
    ("entry", "context", "expected"),
    (
        (_entry("/request"), _context("request_start"), True),
        (
            _entry("/decision", available_from="current_decision", decision_index=2),
            _context("decision_time", decision_index=1),
            False,
        ),
        (
            _entry("/decision", available_from="current_decision", decision_index=2),
            _context("decision_time", decision_index=2),
            True,
        ),
        (
            _entry("/event", available_from="after_public_event", event_index=3),
            _context("decision_time", event_index=2),
            False,
        ),
        (
            _entry("/event", available_from="after_public_event", event_index=3),
            _context("decision_time", event_index=3),
            True,
        ),
        (
            _entry("/actual", available_from="after_actual_play", decision_index=4),
            _context("decision_time", decision_index=4),
            False,
        ),
        (
            _entry("/actual", available_from="after_actual_play", decision_index=4),
            _context("after_actual_play", decision_index=4),
            True,
        ),
        (_entry("/end", available_from="game_end"), _context("after_actual_play"), False),
        (_entry("/end", available_from="game_end"), _context("game_end"), True),
        (_entry("/review", available_from="offline_review"), _context("game_end"), False),
        (_entry("/review", available_from="offline_review"), _context("offline_review"), True),
        (_entry("/review", available_from="offline_review"), _context("engine_internal"), True),
    ),
)
def test_every_availability_boundary(
    entry: FieldProvenanceEntry, context: InformationUseContext, expected: bool
) -> None:
    assert is_field_provenance_entry_available(entry, context) is expected


def test_denied_use_raises_stable_non_disclosing_policy_error() -> None:
    entry = _entry(
        "/private/value",
        visibility="local_private",
        perspective_player_id="secret-player",
    )
    with pytest.raises(SkatAIInformationPolicyError) as exc_info:
        validate_field_provenance_entry_use(
            entry, _context("decision_time", player_id="different-player")
        )
    assert exc_info.value.code == "information_policy_error"
    assert exc_info.value.path == "/private/value"
    assert "secret-player" not in exc_info.value.message
    assert "different-player" not in exc_info.value.message


def test_redaction_removes_private_entries_references_and_dependencies_without_mutation() -> None:
    private_reference = FieldProvenanceSourceReference(
        reference_type="algorithm",
        reference_id="secret-reference-id",
        field_path="/secret/reference/path",
        visibility="engine_private",
    )
    public_reference = FieldProvenanceSourceReference(
        reference_type="request",
        reference_id="request-1",
        field_path="/input",
        visibility="public",
    )
    private = _entry("/secret/private-path", visibility="engine_private")
    public = _entry(
        "/public",
        source_references=(private_reference, public_reference),
        dependency_paths=("/secret/private-path",),
    )
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=(private, public),
        exemptions=(),
        limitations=(),
    )

    redacted = redact_field_provenance_ledger_for_public_output(ledger)

    assert tuple(entry.field_path for entry in redacted.entries) == ("/public",)
    assert tuple(
        reference.reference_id for reference in redacted.entries[0].source_references
    ) == ("request-1",)
    assert redacted.entries[0].dependency_paths == ()
    assert redacted.limitations == ("private_dependencies_redacted",)
    assert len(ledger.entries) == 2
    assert len(ledger.entries[0].source_references) == 2
    assert ledger.entries[0].dependency_paths == ("/secret/private-path",)

    serialized = build_public_serializable_field_provenance_ledger(redacted)
    serialized_text = repr(serialized)
    assert "secret-reference-id" not in serialized_text
    assert "/secret/reference/path" not in serialized_text
    assert "/secret/private-path" not in serialized_text
    assert "private_dependencies_redacted" in serialized_text


def test_redaction_leaves_an_already_public_ledger_equal_and_canonically_ordered() -> None:
    ledger = FieldProvenanceLedger(
        status="complete",
        entries=(_entry("/z"), _entry("/a")),
        exemptions=(),
        limitations=(),
    )
    redacted = redact_field_provenance_ledger_for_public_output(ledger)
    assert redacted == ledger
    assert tuple(entry.field_path for entry in redacted.entries) == ("/a", "/z")


def test_information_use_context_serialization_is_deterministic_and_explicit() -> None:
    context = _context(
        "decision_time",
        player_id="player-1",
        side="declarer",
        decision_index=2,
        event_index=None,
    )
    expected = {
        "workflow": "position_analysis",
        "stage": "decision_time",
        "perspective_player_id": "player-1",
        "perspective_side": "declarer",
        "decision_index": 2,
        "event_index": None,
    }
    assert build_serializable_information_use_context(context) == expected
    assert build_serializable_information_use_context(context) == expected
