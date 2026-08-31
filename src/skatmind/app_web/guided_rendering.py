# ruff: noqa: E501
from __future__ import annotations

from html import escape

from .card_form import CANONICAL_CARD_CONTROLS_V1
from .guided_contracts import (
    ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH,
    ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH,
    ANALYZE_RESET_ACTION_ROUTE_PATH,
    ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH,
    ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH,
    REVIEW_BACK_ACTION_ROUTE_PATH,
    REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH,
    REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH,
    REVIEW_RESET_ACTION_ROUTE_PATH,
    REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH,
    REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
    REVIEW_START_ACTION_ROUTE_PATH,
    REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH,
    REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH,
)
from .historical_form import (
    HISTORICAL_FORM_STEPS,
    HISTORICAL_PLAYER_IDS,
    HistoricalFormDraftV1,
    build_historical_options_summary_v1,
    build_historical_play_view_v1,
)
from .historical_form_parsing import historical_player_label_v1
from .json_transfer import summarize_frontend_request_v1
from .position_form import (
    DEFAULT_POSITION_RANDOM_SEED_V1,
    DEFAULT_POSITION_SAMPLE_COUNT_V1,
    DEFAULT_POSITION_SEARCH_SEED_V1,
    POSITION_ANALYSIS_METHODS_V1,
    POSITION_COMPLETED_TRICK_ROW_COUNT_V1,
    POSITION_MULTI_STEP_POLICIES_V1,
    POSITION_OPPONENT_POLICIES_V1,
    POSITION_POLICY_PRESETS_V1,
    PositionFormDraftV1,
)
from .result_presentation import build_result_presentation_v1
from .result_rendering import render_result_presentation_v1
from .workflow_state import ProcessLocalFrontendWorkflowStateV1


def _e(value: object) -> str:
    return escape(str(value), quote=True)


def _selected(value: object, current: object) -> str:
    return " selected" if value == current else ""


def _checked(value: bool) -> str:
    return " checked" if value else ""


def _options(values: tuple[tuple[str, str], ...], current: object) -> str:
    return "".join(
        f'<option value="{_e(value)}"{_selected(value, current)}>{_e(label)}</option>'
        for value, label in values
    )


def _messages(state: ProcessLocalFrontendWorkflowStateV1) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for retained in state.validation_messages:
        field, separator, message = retained.partition("::")
        if not separator:
            field, message = "_form", retained
        grouped.setdefault(field, []).append(message)
    return {field: tuple(values) for field, values in grouped.items()}


def _field_errors(messages: dict[str, tuple[str, ...]], field: str) -> str:
    return "".join(
        f'<p class="field-error" id="error-{_e(field)}-{index}">{_e(message)}</p>'
        for index, message in enumerate(messages.get(field, ()), start=1)
    )


def _field_attributes(messages: dict[str, tuple[str, ...]], field: str) -> str:
    attributes = f'id="field-{_e(field)}"'
    errors = messages.get(field, ())
    if errors:
        described_by = " ".join(
            f"error-{field}-{index}" for index in range(1, len(errors) + 1)
        )
        attributes += f' aria-invalid="true" aria-describedby="{_e(described_by)}"'
    return attributes


def _field_group(
    messages: dict[str, tuple[str, ...]],
    field: str,
    content: str,
) -> str:
    return (
        f'<div class="form-field" role="group" {_field_attributes(messages, field)}>'
        f"{content}{_field_errors(messages, field)}</div>"
    )


def _error_summary(messages: dict[str, tuple[str, ...]]) -> str:
    if not messages:
        return ""
    items = []
    for field, values in messages.items():
        href = "#workflow-form" if field == "_form" else f"#field-{field}"
        for message in values:
            items.append(f'<li><a href="{_e(href)}">{_e(message)}</a></li>')
    return (
        '<section class="error-summary" aria-labelledby="error-summary-heading" tabindex="-1">'
        '<h2 id="error-summary-heading">Check the submitted information</h2><ul>'
        + "".join(items)
        + "</ul></section>"
    )


def _revision(state: ProcessLocalFrontendWorkflowStateV1) -> str:
    return f'<input type="hidden" name="revision" value="{state.revision}">'


def _card_palette(
    name: str,
    selected_cards: tuple[str, ...],
    *,
    legend: str,
    allowed_cards: tuple[str, ...] | None = None,
    messages: dict[str, tuple[str, ...]] | None = None,
) -> str:
    messages = messages or {}
    selected = set(selected_cards)
    allowed = set(allowed_cards) if allowed_cards is not None else None
    controls = []
    for card in CANONICAL_CARD_CONTROLS_V1:
        if allowed is not None and card.code not in allowed:
            continue
        controls.append(
            '<label class="card-choice">'
            f'<input type="checkbox" name="{_e(name)}" value="{_e(card.code)}"'
            f'{_checked(card.code in selected)}>'
            f'<span>{_e(card.name)} <code>{_e(card.code)}</code></span></label>'
        )
    return (
        f'<fieldset class="card-palette" {_field_attributes(messages, name)}>'
        f'<legend>{_e(legend)}</legend><p>{len(selected)} Cards selected.</p>'
        '<div class="card-grid">'
        + "".join(controls)
        + f"</div>{_field_errors(messages, name)}</fieldset>"
    )


def _card_select(
    name: str,
    current: str | None,
    *,
    label: str,
    include_empty: bool = True,
    allowed_cards: tuple[str, ...] | None = None,
    field_id: str | None = None,
) -> str:
    allowed = set(allowed_cards) if allowed_cards is not None else None
    values = ['<option value="">No Card</option>'] if include_empty else []
    values.extend(
        f'<option value="{_e(card.code)}"{_selected(card.code, current)}>'
        f'{_e(card.name)} ({_e(card.code)})</option>'
        for card in CANONICAL_CARD_CONTROLS_V1
        if allowed is None or card.code in allowed
    )
    identifier = field_id or f"field-{name}"
    return (
        f'<label for="{_e(identifier)}">{_e(label)}</label>'
        f'<select id="{_e(identifier)}" name="{_e(name)}">'
        f'{"".join(values)}</select>'
    )


def _process_local_notice() -> str:
    return (
        '<aside class="local-notice"><strong>Process-local only.</strong> Closing SkatMind '
        "discards unsaved drafts and Results. Explicit JSON download is the only export.</aside>"
    )


def _import_form(
    *,
    action: str,
    revision: int,
    heading: str = "Import SkatMind JSON",
) -> str:
    return (
        '<details class="secondary-action"><summary>'
        + _e(heading)
        + "</summary><p>Import one strict SkatMind JSON object. Import validates but does not run it.</p>"
        f'<form method="post" action="{_e(action)}" enctype="multipart/form-data">'
        f'<input type="hidden" name="revision" value="{revision}">'
        '<label for="request-file">SkatMind JSON file</label>'
        '<input id="request-file" name="request_file" type="file" accept="application/json,.json" required>'
        '<button type="submit">Import JSON</button></form></details>'
    )


def _imported_request(
    state: ProcessLocalFrontendWorkflowStateV1,
    *,
    run_action: str,
    page: str,
) -> str:
    if state.imported_request is None:
        return ""
    summary = summarize_frontend_request_v1(state.imported_request)
    rows = [
        ("Workflow", summary.workflow.value),
        ("Analysis mode", summary.analysis_mode or "Not applicable"),
        ("Game end", summary.game_end_reason or "Not applicable"),
    ]
    executed = state.latest_successful_request == state.imported_request
    if state.execution_source_revision is not None:
        status = "Analysis is running."
        run_label = "Run imported Request"
    elif executed:
        status = "This imported Request produced the Result shown above."
        run_label = "Run imported Request again"
    else:
        status = "It has not been executed."
        run_label = "Run imported Request"
    run_control = (
        '<p class="execution-status" role="status">Analysis is running.</p>'
        if state.execution_source_revision is not None
        else f'<button type="submit">{run_label}</button>'
    )
    request_download = (
        ANALYZE_REQUEST_DOWNLOAD_ROUTE_PATH
        if page == "analyze"
        else REVIEW_REQUEST_DOWNLOAD_ROUTE_PATH
    )
    return (
        '<section class="import-summary" aria-labelledby="import-summary-heading">'
        '<h2 id="import-summary-heading">Imported document</h2>'
        f'<p>The document is validated and retained in memory. {_e(status)}</p>'
        '<dl class="result-details">'
        + "".join(f"<dt>{_e(label)}</dt><dd>{_e(value)}</dd>" for label, value in rows)
        + "</dl>"
        f'<p><a href="{request_download}" download>Download validated Request JSON</a></p>'
        f'<form method="post" action="{_e(run_action)}">{_revision(state)}'
        f"{run_control}</form></section>"
    )


def _result(state: ProcessLocalFrontendWorkflowStateV1, *, page: str) -> str:
    if state.execution_source_revision is not None:
        return '<p class="execution-status" role="status">Analysis is running.</p>'
    if state.latest_successful_result is None:
        return ""
    presentation = build_result_presentation_v1(state.latest_successful_result)
    return render_result_presentation_v1(
        presentation,
        request_download_available=state.request_json_bytes is not None,
        result_download_available=state.result_json_bytes is not None,
        page=page,
    )


def _completed_trick_controls(
    draft: PositionFormDraftV1 | None,
    messages: dict[str, tuple[str, ...]],
) -> str:
    rows = []
    completed = draft.completed_tricks if draft else ()
    leader_options = (
        ("", "No completed Trick"),
        ("me", "You led"),
        ("left", "Left opponent led"),
        ("right", "Right opponent led"),
    )
    for trick_number in range(1, POSITION_COMPLETED_TRICK_ROW_COUNT_V1 + 1):
        trick = completed[trick_number - 1] if trick_number <= len(completed) else None
        leader = trick.leader if trick else ""
        cards = trick.cards if trick else ()
        rows.append(
            f'<fieldset class="completed-trick-row"><legend>Completed Trick {trick_number}</legend>'
            f'<label>Leader<select name="completed_trick_{trick_number}_leader">'
            f'{_options(leader_options, leader)}</select></label>'
            + "".join(
                _card_select(
                    f"completed_trick_{trick_number}_card_{card_number}",
                    cards[card_number - 1] if len(cards) >= card_number else None,
                    label=f"Card {card_number}",
                    field_id=f"completed-trick-{trick_number}-card-{card_number}",
                )
                for card_number in range(1, 4)
            )
            + "</fieldset>"
        )
    return (
        f'<div class="completed-tricks" role="group" '
        f'{_field_attributes(messages, "completed_tricks")}>'
        '<p>Select completed Tricks in chronological order. Leave unused rows empty.</p>'
        + "".join(rows)
        + _field_errors(messages, "completed_tricks")
        + "</div>"
    )


def _advanced_position(
    draft: PositionFormDraftV1 | None,
    messages: dict[str, tuple[str, ...]],
) -> str:
    method = draft.analysis_method if draft else "immediate"
    sample_count = draft.sample_count if draft else DEFAULT_POSITION_SAMPLE_COUNT_V1
    random_seed = draft.random_seed if draft else DEFAULT_POSITION_RANDOM_SEED_V1
    search_seed = draft.search_seed if draft else DEFAULT_POSITION_SEARCH_SEED_V1
    opponent_strategy = draft.opponent_strategy if draft else None
    preset = draft.opponent_policy_preset if draft else None

    method_options = tuple(
        (item.form_value, item.label) for item in POSITION_ANALYSIS_METHODS_V1
    )
    policy_options = (("", "Use existing default"),) + tuple(
        (value, value.replace("_", " ").title()) for value in POSITION_OPPONENT_POLICIES_V1
    )
    preset_options = (("", "No preset override"),) + tuple(
        (value, value.replace("_", " ").title()) for value in POSITION_POLICY_PRESETS_V1
    )
    multi_options = (("", "Use existing default"),) + tuple(
        (value, value.replace("_", " ").title()) for value in POSITION_MULTI_STEP_POLICIES_V1
    )

    def policy_select(field: str, label: str) -> str:
        current = getattr(draft, field) if draft else None
        return _field_group(
            messages,
            field,
            f'<label>{_e(label)}<select name="{field}">'
            f'{_options(policy_options, current or "")}</select></label>',
        )

    return f'''
      <section class="advanced-settings" aria-labelledby="advanced-heading">
        <h2 id="advanced-heading">Advanced Settings</h2>
        <p>These controls change runtime, reproducibility, or evidence scope; they do not change Skat rules.</p>
        <details><summary>Analysis method</summary>
          {_field_group(messages, "analysis_method", f'<label>Method<select name="analysis_method">{_options(method_options, method)}</select></label>')}
          <p>Standard immediate analysis is the default. Bounded Search is strict and has no fallback. Auto tries Search first and may use the existing Immediate fallback. Information-set Search is selected-world, fixed-policy, and bounded, not perfect play.</p>
        </details>
        <details><summary>Runtime and reproducibility</summary>
          {_field_group(messages, "sample_count", f'<label>Immediate samples<input name="sample_count" type="number" min="1" max="100000" value="{sample_count}"></label>')}
          {_field_group(messages, "random_seed", f'<label>Immediate random seed<input name="random_seed" type="number" value="{random_seed}"></label>')}
          {_field_group(messages, "search_seed", f'<label>Search seed<input name="search_seed" type="number" value="{search_seed}"></label>')}
          <p>More samples can increase runtime and simulation precision. Seeds make repeated runs reproducible. Samples are not calibrated probabilities. Search uses the existing interactive budget and timing is not a quality guarantee.</p>
        </details>
        <details><summary>Opponent behavior</summary>
          {_field_group(messages, "opponent_strategy", f'<label>Legacy opponent strategy<select name="opponent_strategy">{_options((("", "Use normal basic strategy"), ("basic", "Basic rule-based strategy"), ("random", "Random legal Cards")), opponent_strategy or "")}</select></label>')}
          {_field_group(messages, "opponent_policy_preset", f'<label>Policy preset<select name="opponent_policy_preset">{_options(preset_options, preset or "")}</select></label>')}
          {policy_select("opponent_lead_policy", "General lead Policy")}
          {policy_select("opponent_response_policy", "General response Policy")}
          {policy_select("left_opponent_lead_policy", "Left opponent lead Policy")}
          {policy_select("left_opponent_response_policy", "Left opponent response Policy")}
          {policy_select("right_opponent_lead_policy", "Right opponent lead Policy")}
          {policy_select("right_opponent_response_policy", "Right opponent response Policy")}
          {_field_group(messages, "use_profile_presets", f'<label><input type="checkbox" name="use_profile_presets"{_checked(draft.use_profile_presets if draft else False)}> Use existing Profile presets when eligible</label>')}
          <p>Policies are fixed rule-based behavior assumptions, not AI predictions. Side-specific values keep existing precedence and may change evidence, runtime, and recommendations.</p>
        </details>
        <details><summary>Simulation and comparison</summary>
          {_field_group(messages, "multi_step_count", f'<label>Multi-Step local Decision count<input name="multi_step_count" type="number" min="1" value="{_e(draft.multi_step_count or "" if draft else "")}"></label>')}
          {_field_group(messages, "card_selection_policy", f'<label>Local Card Policy<select name="card_selection_policy">{_options(multi_options, draft.card_selection_policy or "" if draft else "")}</select></label>')}
          {_field_group(messages, "expected_value_sample_count", f'<label>Expected-value samples<input name="expected_value_sample_count" type="number" min="1" max="100000" value="{draft.expected_value_sample_count if draft else 100}"></label>')}
          {_field_group(messages, "strict_context", f'<label><input type="checkbox" name="strict_context"{_checked(draft.strict_context if draft else False)}> Require strict simulation context</label>')}
          {_field_group(messages, "compare_policies", f'<label><input type="checkbox" name="compare_policies"{_checked(draft.compare_policies if draft else False)}> Compare Policies</label>')}
          {_field_group(messages, "comparison_only", f'<label><input type="checkbox" name="comparison_only"{_checked(draft.comparison_only if draft else False)}> Show comparison only</label>')}
          <p>Steps count new local Decisions. Simulated opponent Cards are not hidden truth. Simulation runs only when selected and preserves the existing nine phases, fallback, ordering, and information boundaries.</p>
        </details>
        <details><summary>Technical evidence</summary>
          {_field_group(messages, "include_provenance", f'<label><input type="checkbox" name="include_provenance"{_checked(draft.include_provenance if draft else False)}> Include field provenance</label>')}
          <p>Provenance reports public-safe field origin and information timing. It is not Confidence, probability, correctness, or authorship, and it can enlarge technical output.</p>
        </details>
        <details><summary>Dataset and evaluation</summary>
          <p>Dataset and evaluation operations are advanced automation workflows and are not configured from this page.</p>
        </details>
      </section>'''


def render_analyze_workflow_v1(state: ProcessLocalFrontendWorkflowStateV1) -> str:
    if type(state) is not ProcessLocalFrontendWorkflowStateV1:
        raise ValueError("state must be exact process-local workflow state.")
    messages = _messages(state)
    draft = state.draft if type(state.draft) is PositionFormDraftV1 else None
    mode = draft.analysis_mode if draft else "live_decision"
    game_type = draft.game_type if draft else "grand"
    role = draft.player_role if draft else "declarer"
    seat = draft.player_position if draft else "forehand"
    declarer = draft.declarer_player if draft else "me"
    leader = draft.trick_leader if draft else "me"
    current = draft.current_trick if draft else ()
    run_control = (
        '<p class="execution-status" role="status">Analysis is running.</p>'
        if state.execution_source_revision is not None
        else '<button type="submit">Run analysis</button>'
    )
    content = [
        _process_local_notice(),
        _error_summary(messages),
        _result(state, page="analyze"),
        '<form id="workflow-form" class="workflow-form" method="post" action="'
        + ANALYZE_RUN_GUIDED_ACTION_ROUTE_PATH
        + '">',
        _revision(state),
        f'<fieldset {_field_attributes(messages, "analysis_mode")}><legend>What would you like to do?</legend>',
        f'<label><input type="radio" name="analysis_mode" value="live_decision"{_checked(mode == "live_decision")}> Analyze a current decision</label>',
        f'<label><input type="radio" name="analysis_mode" value="post_game_review"{_checked(mode == "post_game_review")}> Review one card that was actually played</label>{_field_errors(messages, "analysis_mode")}</fieldset>',
        '<section aria-labelledby="contract-heading"><h2 id="contract-heading">Your role and the contract</h2>',
        _field_group(messages, "game_type", f'<label>Game type<select name="game_type">{_options(tuple((value, value.title()) for value in ("clubs", "spades", "hearts", "diamonds", "grand", "null")), game_type)}</select></label>'),
        _field_group(messages, "player_role", f'<label>Local role<select name="player_role">{_options((("declarer", "Declarer"), ("defender", "Defender")), role)}</select></label>'),
        _field_group(messages, "player_position", f'<label>Local seat<select name="player_position">{_options((("forehand", "Forehand"), ("middlehand", "Middlehand"), ("rearhand", "Rearhand")), seat)}</select></label>'),
        _field_group(messages, "declarer_player", f'<label>Declarer relative to you<select name="declarer_player">{_options((("me", "You are Declarer"), ("left", "Left opponent"), ("right", "Right opponent")), declarer)}</select></label>'),
        _field_group(messages, "hand_game", f'<label><input type="checkbox" name="hand_game"{_checked(draft.hand_game if draft else False)}> Hand</label>'),
        _field_group(messages, "schneider_announced", f'<label><input type="checkbox" name="schneider_announced"{_checked(draft.schneider_announced if draft else False)}> Schneider announced</label>'),
        _field_group(messages, "schwarz_announced", f'<label><input type="checkbox" name="schwarz_announced"{_checked(draft.schwarz_announced if draft else False)}> Schwarz announced</label>'),
        _field_group(messages, "ouvert", f'<label><input type="checkbox" name="ouvert"{_checked(draft.ouvert if draft else False)}> Ouvert</label>'),
        _field_group(messages, "bid_value", f'<label>Bid value<input name="bid_value" type="number" min="1" value="{_e(draft.bid_value or "" if draft else "")}"></label>'),
        _field_group(messages, "matadors", f'<label>Matadors, if known<input name="matadors" type="number" min="1" max="11" value="{_e(draft.matadors or "" if draft else "")}"></label>'),
        '<p>Leave Matadors empty where existing inference or an unavailable value is permitted. SkatMind calculates Game value.</p></section>',
        '<section aria-labelledby="visible-heading"><h2 id="visible-heading">Cards you can currently see</h2>',
        _card_palette("hand", draft.hand if draft else (), legend="Your remaining hand", messages=messages),
        _card_palette("skat", draft.skat if draft else (), legend="Visible Skat, when legitimately known", messages=messages),
        _card_palette("public_declarer_cards", draft.public_declarer_cards if draft else (), legend="Rule-authorized public Declarer hand", messages=messages),
        '<p>Do not enter hidden opponent hands. The server checks every known Card for duplicates.</p></section>',
        '<section aria-labelledby="tricks-heading"><h2 id="tricks-heading">Completed tricks and current trick</h2>',
        _completed_trick_controls(draft, messages),
        _field_group(messages, "current_trick", _card_select("current_trick", current[0] if current else None, label="Current Trick first Card", field_id="current-trick-first") + _card_select("current_trick", current[1] if len(current) > 1 else None, label="Current Trick second Card", field_id="current-trick-second")),
        _field_group(messages, "trick_leader", f'<label>Current Trick leader<select name="trick_leader">{_options((("me", "You"), ("left", "Left opponent"), ("right", "Right opponent")), leader)}</select></label>'),
        '<p>SkatMind derives each completed-Trick winner and the next Player through existing rules.</p></section>',
        '<section aria-labelledby="score-heading"><h2 id="score-heading">Current score and turn</h2>',
        _field_group(messages, "declarer_points", f'<label>Known Declarer points<input name="declarer_points" type="number" min="0" max="120" value="{draft.declarer_points if draft else 0}"></label>'),
        _field_group(messages, "defender_points", f'<label>Known Defender points<input name="defender_points" type="number" min="0" max="120" value="{draft.defender_points if draft else 0}"></label>'),
        _field_group(messages, "actual_card_played", _card_select("actual_card_played", draft.actual_card_played if draft else None, label="Actual Card for retrospective review", field_id="actual-card-played")),
        '<p>Opponent sizes mean Cards remaining. They are derived from attributed public play when possible.</p></section>',
        _advanced_position(draft, messages),
        '<section aria-labelledby="run-heading"><h2 id="run-heading">Run analysis</h2>',
        f'<p>Run validates this exact visible-information Position and executes it once.</p>{run_control}</section></form>',
        _import_form(action=ANALYZE_IMPORT_JSON_ACTION_ROUTE_PATH, revision=state.revision),
        _imported_request(
            state,
            run_action=ANALYZE_RUN_IMPORTED_ACTION_ROUTE_PATH,
            page="analyze",
        ),
        f'<form class="reset-form" method="post" action="{ANALYZE_RESET_ACTION_ROUTE_PATH}">{_revision(state)}<label><input type="checkbox" name="confirm_reset" required> Confirm discard of this process-local Analyze draft and Result</label><button type="submit">Reset Analyze</button></form>',
    ]
    return "".join(content)


def _review_back_and_reset(state: ProcessLocalFrontendWorkflowStateV1, draft: HistoricalFormDraftV1) -> str:
    back = ""
    if draft.step > 1:
        back = (
            f'<form method="post" action="{REVIEW_BACK_ACTION_ROUTE_PATH}">{_revision(state)}'
            '<button type="submit">Back</button></form>'
        )
    reset = (
        f'<form class="reset-form" method="post" action="{REVIEW_RESET_ACTION_ROUTE_PATH}">{_revision(state)}'
        '<label><input type="checkbox" name="confirm_reset" required> Confirm discard of this process-local Review draft and Result</label>'
        '<button type="submit">Reset Review</button></form>'
    )
    return f'<div class="wizard-actions">{back}{reset}</div>'


def _review_step(
    state: ProcessLocalFrontendWorkflowStateV1,
    draft: HistoricalFormDraftV1,
    messages: dict[str, tuple[str, ...]],
) -> str:
    progress = (
        f'<p class="wizard-progress" role="status">Step {draft.step} of 7: '
        f'{_e(HISTORICAL_FORM_STEPS[draft.step - 1].replace("_", " ").title())}</p>'
    )
    if draft.step == 1:
        body = f'''<form id="workflow-form" method="post" action="{REVIEW_UPDATE_PLAYERS_ACTION_ROUTE_PATH}">{_revision(state)}
          <h2>1. Players and seats</h2><p>Seats are fixed. Display labels are optional and remain process-local.</p>
          {_field_group(messages, "forehand_label", f'<label>Forehand display label<input name="forehand_label" value="{_e(draft.players[0].player_label or "")}"></label>')}
          {_field_group(messages, "middlehand_label", f'<label>Middlehand display label<input name="middlehand_label" value="{_e(draft.players[1].player_label or "")}"></label>')}
          {_field_group(messages, "rearhand_label", f'<label>Rearhand display label<input name="rearhand_label" value="{_e(draft.players[2].player_label or "")}"></label>')}
          <button type="submit">Continue to Deal</button></form>'''
    elif draft.step == 2:
        body = (
            f'<form id="workflow-form" method="post" action="{REVIEW_UPDATE_DEAL_ACTION_ROUTE_PATH}">{_revision(state)}'
            '<h2>2. Deal</h2><p>Assign all 32 Cards exactly: ten per Player and two to the Skat. No Cards are generated or corrected.</p>'
            + _card_palette("forehand_hand", draft.players[0].initial_hand, legend="Forehand hand: 10 Cards", messages=messages)
            + _card_palette("middlehand_hand", draft.players[1].initial_hand, legend="Middlehand hand: 10 Cards", messages=messages)
            + _card_palette("rearhand_hand", draft.players[2].initial_hand, legend="Rearhand hand: 10 Cards", messages=messages)
            + _card_palette("skat", draft.skat, legend="Skat: 2 Cards", messages=messages)
            + '<button type="submit">Validate Deal</button></form>'
        )
    elif draft.step == 3:
        declaration = draft.declaration
        body = f'''<form id="workflow-form" method="post" action="{REVIEW_UPDATE_DECLARATION_ACTION_ROUTE_PATH}">{_revision(state)}
          <h2>3. Declarer and declaration</h2>
          {_field_group(messages, "declarer_player_id", f'<label>Declarer<select name="declarer_player_id">{_options(tuple((player.player_id, player.player_label or player.seat.title()) for player in draft.players), declaration.declarer_player_id if declaration else HISTORICAL_PLAYER_IDS[0])}</select></label>')}
          {_field_group(messages, "game_type", f'<label>Game type<select name="game_type">{_options(tuple((value, value.title()) for value in ("clubs", "spades", "hearts", "diamonds", "grand", "null")), declaration.game_type if declaration else "grand")}</select></label>')}
          {_field_group(messages, "bid_value", f'<label>Bid value<input name="bid_value" type="number" min="1" value="{declaration.bid_value if declaration else 18}"></label>')}
          {_field_group(messages, "hand_game", f'<label><input type="checkbox" name="hand_game"{_checked(declaration.hand_game if declaration else False)}> Hand</label>')}
          {_field_group(messages, "schneider_announced", f'<label><input type="checkbox" name="schneider_announced"{_checked(declaration.schneider_announced if declaration else False)}> Schneider announced</label>')}
          {_field_group(messages, "schwarz_announced", f'<label><input type="checkbox" name="schwarz_announced"{_checked(declaration.schwarz_announced if declaration else False)}> Schwarz announced</label>')}
          {_field_group(messages, "ouvert", f'<label><input type="checkbox" name="ouvert"{_checked(declaration.ouvert if declaration else False)}> Ouvert</label>')}
          <p>All four Null variants use the existing Hand and Ouvert dependencies. Product validation remains authoritative.</p>
          <button type="submit">Continue to Skat and Discards</button></form>'''
    elif draft.step == 4:
        hand_game = bool(draft.declaration and draft.declaration.hand_game)
        declarer = (
            next(
                player
                for player in draft.players
                if player.player_id == draft.declaration.declarer_player_id
            )
            if draft.declaration is not None
            else None
        )
        discard_controls = (
            ""
            if hand_game or declarer is None
            else _card_palette(
                "discarded_cards",
                draft.discarded_cards,
                legend="Discards",
                allowed_cards=(*declarer.initial_hand, *draft.skat),
                messages=messages,
            )
        )
        body = (
            f'<form id="workflow-form" method="post" action="{REVIEW_UPDATE_DISCARDS_ACTION_ROUTE_PATH}">{_revision(state)}'
            '<h2>4. Skat pickup and Discards</h2>'
            f'<p>{"Hand games require no Discards." if hand_game else "Select exactly two Cards discarded after pickup."}</p>'
            + discard_controls
            + '<button type="submit">Validate Discards</button></form>'
        )
    elif draft.step == 5:
        view = build_historical_play_view_v1(draft)
        actor = historical_player_label_v1(draft, view.acting_player_id) if view.acting_player_id else "Complete"
        current_cards = ", ".join(play.card for play in view.current_trick_plays) or "No Cards"
        play_control = (
            f'<form method="post" action="{REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH}">{_revision(state)}'
            '<button type="submit">Continue to Review options</button></form>'
            if view.is_complete
            else f'''<form method="post" action="{REVIEW_APPEND_PLAY_ACTION_ROUTE_PATH}">{_revision(state)}
             {_field_group(messages, "card", _card_select("card", None, label="Legal Card", include_empty=False, allowed_cards=view.legal_cards, field_id="legal-card"))}
            <button type="submit">Append Card</button></form>'''
        )
        body = f'''<section id="workflow-form"><h2>5. Card play</h2>
          <p>Play {view.played_card_count} of 30. Completed Tricks: {len(view.completed_tricks)}. Current Trick: {_e(current_cards)}.</p>
          <p><strong>Acting Player:</strong> {_e(actor)}</p>
          {play_control}
          {f'<form method="post" action="{REVIEW_UNDO_PLAY_ACTION_ROUTE_PATH}">{_revision(state)}<button type="submit">Undo final play</button></form>' if draft.plays else ""}
          <p>SkatMind derives the actor, legal Cards, Trick winner, and next leader with existing Product helpers.</p></section>'''
    elif draft.step == 6:
        options = draft.options
        body = f'''<form id="workflow-form" method="post" action="{REVIEW_UPDATE_OPTIONS_ACTION_ROUTE_PATH}">{_revision(state)}
          <h2>6. Review options</h2><p>Game validation, Result, and Settlement are always included. No optional family runs unless selected.</p>
          <section class="advanced-settings" aria-labelledby="advanced-heading"><h3 id="advanced-heading">Advanced Settings</h3>
          <details><summary>Analysis method</summary>
            {_field_group(messages, "decision_snapshots", f'<label><input type="checkbox" name="decision_snapshots"{_checked(options.decision_snapshots)}> Decision Snapshots</label>')}
            {_field_group(messages, "immediate_review", f'<label><input type="checkbox" name="immediate_review"{_checked(options.immediate_review)}> Immediate Historical Review</label>')}
            {_field_group(messages, "search_review", f'<label><input type="checkbox" name="search_review"{_checked(options.search_review)}> Bounded Search Review</label>')}
            {_field_group(messages, "information_set_search_review", f'<label><input type="checkbox" name="information_set_search_review"{_checked(options.information_set_search_review)}> Information-set Search Review</label>')}
            <p>Optional reviews assess chronological Decisions using existing Immediate or bounded Search methods. Search can increase runtime and has no perfect-play claim.</p>
          </details>
          <details><summary>Runtime and reproducibility</summary>
            {_field_group(messages, "search_seed", f'<label>Search seed<input name="search_seed" type="number" value="{options.search_seed}"></label>')}
            {_field_group(messages, "immediate_sample_count", f'<label>Immediate samples<input name="immediate_sample_count" type="number" min="1" value="{options.immediate_sample_count}"></label>')}
            {_field_group(messages, "immediate_base_random_seed", f'<label>Immediate base random seed<input name="immediate_base_random_seed" type="number" value="{options.immediate_base_random_seed}"></label>')}
            <p>Search-dependent reviews use the existing Historical Review budget profile. Samples can increase runtime; seeds preserve reproducibility. Timing is not a quality guarantee.</p>
          </details>
          <details><summary>Opponent behavior</summary><p>Historical reviews retain existing fixed public Policy behavior. This editor adds no learned prediction or separate opponent-data source.</p></details>
          <details><summary>Simulation and comparison</summary>
            {_field_group(messages, "replay_coaching", f'<label><input type="checkbox" name="replay_coaching"{_checked(options.replay_coaching)}> Replay Coaching</label>')}
            {_field_group(messages, "information_set_replay_coaching", f'<label><input type="checkbox" name="information_set_replay_coaching"{_checked(options.information_set_replay_coaching)}> Information-set Replay Coaching</label>')}
            {_field_group(messages, "tactical", f'<label><input type="checkbox" name="tactical"{_checked(options.tactical)}> Tactical Motif Review</label>')}
            <p>Coaching and Tactical outputs use their existing prerequisites and evidence limits. They do not establish ground truth, intent, causation, or global optimality.</p>
          </details>
          <details><summary>Technical evidence</summary>
            {_field_group(messages, "include_provenance", f'<label><input type="checkbox" name="include_provenance"{_checked(options.include_provenance)}> Include field provenance</label>')}
            <p>Provenance reports public-safe field origin and information timing. It changes evidence scope, not game rules, Confidence, probability, correctness, or authorship.</p>
          </details>
          <details><summary>Dataset and evaluation</summary><p>Dataset and evaluation operations are advanced automation workflows and are not configured from this page.</p></details>
          </section><button type="submit">Review selections</button></form>'''
    else:
        summary = build_historical_options_summary_v1(draft)
        selected = ", ".join(summary.selected_outputs) or "No optional review families"
        prerequisites = ", ".join(summary.implied_prerequisites) or "None"
        run_control = (
            '<p class="execution-status" role="status">Analysis is running.</p>'
            if state.execution_source_revision is not None
            else f'<form method="post" action="{REVIEW_RUN_GUIDED_ACTION_ROUTE_PATH}">{_revision(state)}<button type="submit">Validate and run Review</button></form>'
        )
        body = f'''<section id="workflow-form"><h2>7. Validate and run</h2>
          <dl class="result-details"><dt>Game</dt><dd>Normal completion, 30 legal plays</dd>
          <dt>Always included</dt><dd>{_e(", ".join(summary.always_included))}</dd>
          <dt>Selected</dt><dd>{_e(selected)}</dd><dt>Implied prerequisites</dt><dd>{_e(prerequisites)}</dd></dl>
          {run_control}</section>'''
    return '<section class="wizard">' + progress + body + _review_back_and_reset(state, draft) + "</section>"


def render_review_workflow_v1(state: ProcessLocalFrontendWorkflowStateV1) -> str:
    if type(state) is not ProcessLocalFrontendWorkflowStateV1:
        raise ValueError("state must be exact process-local workflow state.")
    messages = _messages(state)
    draft = state.draft if type(state.draft) is HistoricalFormDraftV1 else None
    content = [
        _process_local_notice(),
        _error_summary(messages),
        _result(state, page="review"),
        '<section class="workflow-choice"><h2>Choose how to review</h2><p>Enter a completed game</p><p>Import an existing SkatMind JSON document</p></section>',
    ]
    if draft is None and state.imported_request is None:
        content.append(
            f'<form id="workflow-form" method="post" action="{REVIEW_START_ACTION_ROUTE_PATH}">{_revision(state)}'
            '<button type="submit">Start normal-completion editor</button></form>'
        )
    if draft is not None:
        content.append(_review_step(state, draft, messages))
    content.extend(
        (
            '<aside class="scope-note"><h2>Manual editor scope</h2><p>The guided editor emits normal completion only. Existing supported shortened endings, continuations, party-wide Claims, and Position post-game variants remain available through strict JSON import.</p></aside>',
            _import_form(action=REVIEW_IMPORT_JSON_ACTION_ROUTE_PATH, revision=state.revision, heading="Import an existing SkatMind JSON document"),
            _imported_request(
                state,
                run_action=REVIEW_RUN_IMPORTED_ACTION_ROUTE_PATH,
                page="review",
            ),
        )
    )
    return "".join(content)
