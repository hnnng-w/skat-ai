# ruff: noqa: E501

from __future__ import annotations

import re
from html import escape

from skatmind.session_commands import (
    SESSION_COMMAND_ALLOWED_PHASES,
    SESSION_COMMAND_KINDS,
)

from .friendly_creation_rendering import render_friendly_managed_category_landing_v1
from .frontend_profile_contracts import LocalFrontendProfileV1
from .managed_item_contracts import ManagedCategoryViewV1
from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .session_frontend import GuidedSessionContextV1

_FORM_OPEN = re.compile(r"<form\b[^>]*>")


def _e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _bool_select(name: str, label: str, *, default: bool = False) -> str:
    return (
        f'<label>{_e(label)} <select name="{_e(name)}">'
        f'<option value="false"{" selected" if not default else ""}>No</option>'
        f'<option value="true"{" selected" if default else ""}>Yes</option>'
        "</select></label>"
    )


def render_managed_category_landing_v1(
    view: ManagedCategoryViewV1,
    *,
    profile: LocalFrontendProfileV1 | None = None,
    profile_generation: int = 0,
    locale: str = "en",
) -> str:
    return render_friendly_managed_category_landing_v1(
        view,
        profile=profile,
        profile_generation=profile_generation,
        locale=locale,
    )


def render_match_to_learning_transfer_v1(
    learning_state: dict[str, object] | None,
    *,
    report_id: str | None,
    target_managed_handle: str | None = None,
) -> str:
    if learning_state is None:
        return (
            '<section class="panel"><h2>Explicit Learning transfer</h2>'
            '<p><a href="/matches/downloads/workspace.json" download>'
            "Download current Match Workspace JSON</a></p>"
            "<p>Open a managed Learning Corpus to enable an explicit path-free transfer.</p>"
            '<p><a href="/learning">Manage Learning Corpora</a></p></section>'
        )
    if type(target_managed_handle) is not str or len(target_managed_handle) != 64:
        raise ValueError("target_managed_handle must be one opaque managed handle.")
    target_hidden = (
        f'<input type="hidden" name="target_managed_handle" value="{_e(target_managed_handle)}">'
    )
    corpus = learning_state["corpus"]
    if not isinstance(corpus, dict):
        raise ValueError("Active Learning state must contain Corpus summary data.")
    snapshots = learning_state["current_match_snapshots"]
    if not isinstance(snapshots, list):
        raise ValueError("Active Learning state must contain Current Match snapshots.")
    snapshot_options = "".join(
        f'<option value="{_e(item["match_snapshot_id"])}">'
        f"{_e(item['match_id'])} - {_e(item['match_snapshot_id'])}</option>"
        for item in snapshots
        if isinstance(item, dict)
    )
    report_form = ""
    if report_id is not None:
        report_form = (
            '<form method="post" action="/matches/transfer-report" class="form-grid">'
            f"{target_hidden}"
            f'<input type="hidden" name="report_id" value="{_e(report_id)}">'
            '<label>Current Match Snapshot <select name="match_snapshot_id" required>'
            f"{snapshot_options}</select></label>"
            '<button type="submit">Transfer this Decision Report source</button></form>'
            if snapshot_options
            else "<p>Import and select this Match Workspace before transferring a Report.</p>"
        )
    return (
        '<section class="panel"><h2>Explicit Learning transfer</h2>'
        f"<p>Target Corpus: <strong>{_e(corpus['corpus_id'])}</strong></p>"
        '<p><a href="/matches/downloads/workspace.json" download>'
        "Download current Match Workspace JSON</a></p>"
        '<form method="post" action="/matches/transfer-workspace" class="form-grid">'
        f"{target_hidden}"
        f'<input type="hidden" name="expected_catalog_revision" value="{_e(corpus["catalog_revision"])}">'
        '<label>Current-selection behavior <select name="selection_mode">'
        '<option value="select_imported">Select imported Snapshot</option>'
        '<option value="keep_current">Keep existing selection</option></select></label>'
        '<label>Same-revision behavior <select name="same_revision_resolution">'
        '<option value="reject">Require explicit resolution</option>'
        '<option value="retain">Retain both Snapshots</option></select></label>'
        '<button type="submit">Transfer current Match Workspace</button></form>'
        f"{report_form}</section>"
    )


def _command_fields(kind: str, player_options: str) -> str:
    if kind == "set_game_metadata":
        return (
            '<label>Game ID <input name="game_id"></label>'
            '<label>Played at (RFC 3339) <input name="played_at"></label>'
        )
    if kind == "record_dealt_card":
        return (
            '<label>Destination <select name="destination"><option value="player_hand">'
            'Player hand</option><option value="skat">Skat</option></select></label>'
            f'<label>Player <select name="player_id"><option value="">None</option>{player_options}</select></label>'
            '<label>Card code <input name="card" required></label>'
        )
    if kind == "set_declarer":
        return f'<label>Declarer <select name="player_id">{player_options}</select></label>'
    if kind == "set_declaration":
        return (
            '<label>Game type <select name="game_type">'
            + "".join(
                f'<option value="{value}">{label}</option>'
                for value, label in (
                    ("clubs", "Clubs"),
                    ("spades", "Spades"),
                    ("hearts", "Hearts"),
                    ("diamonds", "Diamonds"),
                    ("grand", "Grand"),
                    ("null", "Null"),
                )
            )
            + "</select></label>"
            + _bool_select("hand_game", "Hand game")
            + _bool_select("ouvert", "Ouvert")
            + _bool_select("schneider_announced", "Schneider announced")
            + _bool_select("schwarz_announced", "Schwarz announced")
            + '<label>Matadors <input type="number" name="matadors" min="1"></label>'
            + '<label>Bid value <input type="number" name="bid_value" min="1"></label>'
        )
    if kind == "record_discard":
        return '<label>Discard Card code <input name="card" required></label>'
    if kind == "record_play":
        return (
            f'<label>Player <select name="player_id">{player_options}</select></label>'
            '<label>Played Card code <input name="card" required></label>'
        )
    if kind == "set_public_hand":
        return (
            f'<label>Player <select name="player_id">{player_options}</select></label>'
            '<label>Current public hand Card codes <input name="cards" required></label>'
        )
    if kind == "set_game_event":
        return (
            '<label>Continuation <select name="event_kind">'
            '<option value="defender_open_play_continuation">Defender open play</option>'
            '<option value="declarer_card_exposure_continuation">Declarer card exposure</option>'
            "</select></label>"
            '<label>After play count <input type="number" name="after_play_count" min="0" max="29" required></label>'
            f'<label>Exposing Player <select name="player_id"><option value="">None</option>{player_options}</select></label>'
            '<label>Exposed Card codes <input name="cards" required></label>'
            + _exposure_response_fields(player_options)
        )
    if kind == "set_game_end":
        return (
            '<label>End reason <select name="game_end_reason">'
            '<option value="normal_completion">Normal completion</option>'
            '<option value="declarer_concession">Declarer concession</option>'
            '<option value="defender_concession">Defender concession</option>'
            '<option value="declarer_card_exposure">Declarer card exposure</option>'
            '<option value="defender_open_play">Defender open play</option>'
            '<option value="open_card_throw">Open Card throw</option>'
            "</select></label>"
            f'<label>Relevant Player <select name="player_id"><option value="">None</option>{player_options}</select></label>'
            '<label>Relevant Card codes <input name="cards"></label>'
            '<label>Remaining Card count <input type="number" name="remaining_card_count"></label>'
            '<label>Consent status <input name="consent_status"></label>'
            '<label>Consenting Player IDs <input name="consenting_player_ids"></label>'
            '<label>Concession form <input name="concession_form"></label>'
            '<label>Statement classification <input name="statement_classification"></label>'
            + _exposure_response_fields(player_options)
        )
    return "<p>Promote this Live Session without adding private facts.</p>"


def _exposure_response_fields(player_options: str) -> str:
    responses = "".join(
        (
            f'<label>Defender {index} <select name="defender_{index}_player_id">'
            f'<option value="">None</option>{player_options}</select></label>'
            f'<label>Defender {index} response <select name="defender_{index}_response">'
            '<option value="accept">Accept</option><option value="continue">Continue</option>'
            "</select></label>"
            f'<label>Defender {index} form <input name="defender_{index}_form" value="explicit"></label>'
        )
        for index in (1, 2)
    )
    return (
        '<label>Exposure form <select name="exposure_form">'
        '<option value="laid_open">Laid open</option>'
        '<option value="shown_to_defender">Shown to defender</option></select></label>'
        f'<label>Shown to defender <select name="shown_to_defender_player_id">'
        f'<option value="">None</option>{player_options}</select></label>'
        '<label>Claimed play level <select name="claimed_play_level">'
        '<option value="simple">Simple</option><option value="schneider">Schneider</option>'
        '<option value="schwarz">Schwarz</option></select></label>' + responses
    )


def _session_command_forms(context: GuidedSessionContextV1) -> str:
    state = context.state
    player_options = "".join(
        f'<option value="{_e(player.player_id)}">{_e(player.player_label or player.player_id)}</option>'
        for player in state.players
    )
    forms = []
    for kind in SESSION_COMMAND_KINDS:
        allowed = state.phase in SESSION_COMMAND_ALLOWED_PHASES[kind]
        forms.append(
            f'<details class="command-form"><summary>{_e(kind.replace("_", " ").title())}'
            f" - {'available now' if allowed else 'correction only in this phase'}</summary>"
            '<form method="post" action="/sessions/command" class="form-grid">'
            f'<input type="hidden" name="expected_revision" value="{state.revision}">'
            f'<input type="hidden" name="kind" value="{_e(kind)}">'
            "<label>Correction target revision (leave empty for a new Command) "
            '<input type="number" name="target_revision" min="1"></label>'
            f"{_command_fields(kind, player_options)}"
            f'<button type="submit">{"Apply Command" if allowed else "Correct target Command"}</button>'
            "</form></details>"
        )
    return "".join(forms)


def _session_analysis(context: GuidedSessionContextV1) -> str:
    execution = context.execution
    result = ""
    if execution is not None:
        presentation = build_result_presentation_v1(execution.result)
        result = render_result_presentation_v1(
            presentation,
            request_download_available=True,
            result_download_available=True,
            request_download_route="/sessions/downloads/request.json",
            result_download_route="/sessions/downloads/result.json",
        )
    position = (
        '<form method="post" action="/sessions/analyze" class="form-grid">'
        f'<input type="hidden" name="expected_revision" value="{context.state.revision}">'
        '<label>Samples <input type="number" name="sample_count" value="100" min="1" max="100000"></label>'
        '<label>Random seed <input type="number" name="random_seed" value="0"></label>'
        '<label>Opponent strategy <select name="opponent_strategy"><option value="basic">Basic</option>'
        '<option value="random">Random</option></select></label>'
        '<label>Recommendation method <select name="recommendation_method"><option value="">Automatic</option>'
        '<option value="immediate_expected_value">Immediate</option><option value="bounded_search">Search</option>'
        '<option value="auto">Search-first automatic</option></select></label>'
        '<label>Search budget <select name="search_budget_profile"><option value="interactive_v1">Interactive</option>'
        '<option value="historical_review_v1">Historical review</option></select></label>'
        '<button type="submit">Analyze current Position</button></form>'
    )
    historical_bools = "".join(
        _bool_select(name, name.replace("_", " ").title(), default=name == "immediate_review")
        for name in (
            "decision_snapshots",
            "immediate_review",
            "search_review",
            "information_set_search_review",
            "replay_coaching",
            "information_set_replay_coaching",
            "historical_tactical_motif_review",
        )
    )
    historical = (
        '<form method="post" action="/sessions/review" class="form-grid">'
        f'<input type="hidden" name="expected_revision" value="{context.state.revision}">'
        f"{historical_bools}"
        '<label>Immediate samples <input type="number" name="sample_count" value="100" min="1"></label>'
        '<label>Immediate seed <input type="number" name="random_seed" value="0"></label>'
        '<label>Search seed <input type="number" name="search_seed" value="0"></label>'
        '<label>Search budget <select name="search_budget_profile"><option value="historical_review_v1">'
        'Historical review</option><option value="interactive_v1">Interactive</option></select></label>'
        '<button type="submit">Review completed game</button></form>'
    )
    return (
        '<section class="panel"><h2>Explicit analysis</h2><div class="analysis-grid">'
        f"{position}{historical}</div>{result}</section>"
    )


def render_guided_session_v1(
    context: GuidedSessionContextV1,
    *,
    show_operation_notice: bool = True,
) -> str:
    with context.lock:
        state = context.state
        operation = context.last_operation if show_operation_notice else None
        notice = (
            ""
            if operation is None
            else (
                f'<div class="notice {"warning" if operation.status in {"conflict", "rejected", "stale"} else "info"}">'
                f"<p>{_e(operation.message)}</p>"
                + "".join(f"<p>{_e(item)}</p>" for item in operation.diagnostics)
                + "</div>"
            )
        )
        players = "".join(
            f"<li>{_e(player.seat)}: {_e(player.player_label or player.player_id)} "
            f"(<code>{_e(player.player_id)}</code>)</li>"
            for player in state.players
        )
        diagnostics = "".join(
            f"<li><strong>{_e(item.code)}</strong>: {_e(item.message)}</li>"
            for item in state.validation.diagnostics
        )
        history = "".join(
            f"<tr><td>{record.revision}</td><td>{_e(record.command.kind)}</td>"
            f"<td>{_e(record.command.to_dict())}</td></tr>"
            for record in state.command_log
        )
        rendered = (
            f'<div id="session-app">{notice}<section class="panel"><p class="eyebrow">'
            f"{_e(state.capture_mode)} Session</p><h2>{_e(state.session_id)}</h2>"
            f"<dl><dt>Revision</dt><dd>{state.revision}</dd><dt>Phase</dt><dd>{_e(state.phase)}</dd>"
            f"<dt>Decision Checkpoints</dt><dd>{len(context.decision_checkpoints)}</dd></dl>"
            f'<ul>{players}</ul><p><a href="/sessions">Manage Sessions</a></p>'
            '<form method="post" action="/sessions/reload"><button type="submit">Reload from disk</button></form>'
            '<p><a href="/sessions/downloads/session.json" download>Download current Session JSON</a></p>'
            f'</section><section class="panel"><h2>Validation</h2><ul>{diagnostics or "<li>No current diagnostics.</li>"}</ul></section>'
            f'<section class="panel"><h2>Phase-aware Command entry</h2>{_session_command_forms(context)}</section>'
            '<section class="panel"><h2>History</h2><form method="post" action="/sessions/undo">'
            f'<input type="hidden" name="expected_revision" value="{state.revision}">'
            '<label>Target revision <input type="number" name="target_revision" min="0" required></label>'
            '<button type="submit">Undo to strict prefix</button></form>'
            f'<div class="table-wrap"><table><thead><tr><th>Revision</th><th>Kind</th><th>Command</th></tr></thead>'
            f"<tbody>{history or '<tr><td colspan="3">No accepted Commands.</td></tr>'}</tbody></table></div></section>"
            f"{_session_analysis(context)}</div>"
        )
        hidden = f'<input type="hidden" name="managed_handle" value="{_e(context.handle)}">'
        return _FORM_OPEN.sub(lambda match: match.group(0) + hidden, rendered)
