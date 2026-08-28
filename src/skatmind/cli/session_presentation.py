from __future__ import annotations

import copy
import sys
from typing import Any

import skatmind.api.v1.session as session_api
from skatmind.cli.presentation.historical import (
    print_historical_game_result,  # noqa: F401
    print_historical_replay_coaching_result,  # noqa: F401
    print_historical_search_review_result,  # noqa: F401
)
from skatmind.cli.presentation.position import print_analysis_result  # noqa: F401
from skatmind.cli.presentation.provenance import (
    print_field_provenance_summary,  # noqa: F401
)
from skatmind.output_writer import write_analysis_result_to_json


def write_output(output_path: str, document: dict[str, Any]) -> None:
    write_analysis_result_to_json(output_path=output_path, result=document)


def print_diagnostics(diagnostics: tuple[object, ...]) -> None:
    for diagnostic in diagnostics:
        print(f"Diagnostic {diagnostic.code}: {diagnostic.message}")


def print_session_summary(
    state: session_api.SessionStateV1,
    checkpoints: tuple[session_api.SessionDecisionCheckpointV1, ...],
) -> None:
    print("Session summary")
    print("Session ID:", state.session_id)
    print("Revision:", state.revision)
    print("Capture mode:", state.capture_mode)
    print("Phase:", state.phase)
    print("Position readiness:", state.validation.position_export.status)
    print("Historical readiness:", state.validation.historical_export.status)
    print(
        "Players:",
        ", ".join(f"{player.player_id} ({player.seat})" for player in state.players),
    )
    print("Checkpoint count:", len(checkpoints))
    for index, checkpoint in enumerate(checkpoints):
        observation = session_api.observe_session_decision_checkpoint(
            state=state,
            checkpoint=checkpoint,
        ).value
        line = (
            f"Checkpoint {index}: revision {checkpoint.source_revision}, "
            f"decision {checkpoint.decision_index}, "
            f"lineage {observation.lineage.relationship}, "
            f"observation {observation.status}"
        )
        if observation.actual_card is not None:
            line += f", actual card {observation.actual_card}"
        print(line)


def print_save_conflict() -> None:
    print(
        "Error: Session file changed since it was loaded; no changes were saved.",
        file=sys.stderr,
    )


def print_output_confirmation(output_path: str) -> None:
    print("Output file written:", output_path)


def privacy_safe_position_result(result: dict[str, Any]) -> dict[str, Any]:
    safe = copy.deepcopy(result)
    position = safe.get("position")
    if isinstance(position, dict):
        hand = position.get("hand")
        if isinstance(hand, list):
            position["hand"] = f"[{len(hand)} private cards]"
        skat = position.get("skat")
        if isinstance(skat, list):
            position["skat"] = f"[{len(skat)} private cards]"
    legal_cards = safe.get("legal_cards")
    if isinstance(legal_cards, list):
        safe["legal_cards"] = f"[{len(legal_cards)} private legal cards]"
    if isinstance(safe.get("analysis_report"), list):
        safe["analysis_report"] = []
    return safe


_write_output = write_output
_print_diagnostics = print_diagnostics
_print_session_summary = print_session_summary
_print_save_conflict = print_save_conflict
_print_output_confirmation = print_output_confirmation
_privacy_safe_position_result = privacy_safe_position_result
