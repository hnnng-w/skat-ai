# ruff: noqa: E501

from __future__ import annotations

import json
from html import escape
from importlib.resources import files
from string import Template
from typing import Any

_TEMPLATE_PACKAGE = "skat_ai.capture_web"
_TEMPLATE_NAME = "templates/page.html"


def load_match_capture_web_template_v1() -> str:
    return files(_TEMPLATE_PACKAGE).joinpath(_TEMPLATE_NAME).read_text(encoding="utf-8")


def _e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _label(value: object) -> str:
    if value is None:
        return "None"
    if type(value) is bool:
        return "yes" if value else "no"
    return str(value).replace("_", " ")


def _facts(rows: tuple[tuple[str, object], ...]) -> str:
    return (
        '<dl class="report-facts">'
        + "".join(
            f"<div><dt>{_e(label)}</dt><dd>{_e(_label(value))}</dd></div>" for label, value in rows
        )
        + "</dl>"
    )


def _curated_json(value: object) -> str:
    return (
        '<pre class="curated-json">' + _e(json.dumps(value, ensure_ascii=True, indent=2)) + "</pre>"
    )


def _hidden(state: dict[str, Any], operation: str) -> str:
    return (
        f'<input type="hidden" name="operation" value="{_e(operation)}">'
        f'<input type="hidden" name="match_position" '
        f'value="{state["selected_position"]}">'
        f'<input type="hidden" name="expected_revision" '
        f'value="{state.get("workspace_revision", 0)}">'
    )


def _creation_form(state: dict[str, Any]) -> str:
    rows = "".join(
        f"""
        <fieldset>
          <legend>Player {index} - place_{index}</legend>
          <label>Player ID <input name="player_{index}_id" required></label>
          <label>Label <input name="player_{index}_label"></label>
          <label>Platform Player ID <input name="player_{index}_platform_id"></label>
        </fieldset>
        """
        for index in range(1, 4)
    )
    return f"""
    <main class="creation-shell">
      <section class="hero">
        <p class="eyebrow">Private local Match capture</p>
        <h1>Create {_e(state["workspace_filename"])}</h1>
        <p>One EuroSkat 36er Standard Match. No JSON authoring required.</p>
      </section>
      <form method="post" action="/api/v1/create" class="panel form-grid">
        <label>Match ID <input name="match_id" required autofocus></label>
        <label>Title <input name="title" required></label>
        <label>Game platform <input name="game_platform" value="EuroSkat" required></label>
        <label>External Match ID <input name="external_match_id"></label>
        <label>Played time (RFC 3339) <input name="played_at"></label>
        <label>Format <input value="euroskat_36_standard_v1" readonly></label>
        <label>Source kind
          <select name="source_kind">
            <option value="youtube_video">YouTube video</option>
            <option value="other_video">Other video</option>
            <option value="manual_observation">Manual observation</option>
          </select>
        </label>
        <label>Source URL <input type="url" name="source_url"></label>
        <label>Source title <input name="source_title" required></label>
        <label>Channel <input name="source_channel_name"></label>
        <label>Match start <input name="match_timecode_start" placeholder="01:12:34.500"></label>
        <label>Match end <input name="match_timecode_end" placeholder="01:45:00"></label>
        <div class="player-grid">{rows}</div>
        <label>Perspective Player ID <input name="perspective_player_id" required></label>
        <button type="submit" class="primary">Create and save Workspace</button>
      </form>
    </main>
    """


def _overview(state: dict[str, Any]) -> str:
    slots = state["slots"]
    rounds = []
    for round_number in range(1, 13):
        buttons = []
        for slot in slots[(round_number - 1) * 3 : round_number * 3]:
            classes = ["position-card", f"state-{slot['game_state']}"]
            if slot["selected"]:
                classes.append("selected")
            if slot["first_empty"]:
                classes.append("first-empty")
            buttons.append(
                f"""
                <a class="{" ".join(classes)}" href="/position/{slot["match_position"]}"
                   aria-current="{"page" if slot["selected"] else "false"}">
                  <strong>{slot["match_position"]}</strong>
                  <span>{_e(slot["game_state"].replace("_", " "))}</span>
                  <small>{slot["forehand_player_id"]} / {slot["middlehand_player_id"]} / {slot["rearhand_player_id"]}</small>
                  <small>{slot["play_count"]} Plays, {slot["commentary_count"]} Notes</small>
                </a>
                """
            )
        rounds.append(
            f'<section class="round"><h3>Round {round_number}</h3>'
            f'<div class="round-slots">{"".join(buttons)}</div></section>'
        )
    return "".join(rounds)


def _metadata_form(state: dict[str, Any]) -> str:
    match = state["match"]
    source = state["source"]
    participants = state["participants"]
    player_rows = "".join(
        f"""
        <label>{_e(player["player_id"])} label
          <input name="player_{index}_label" value="{_e(player["player_label"])}">
        </label>
        <label>{_e(player["player_id"])} platform ID
          <input name="player_{index}_platform_id" value="{_e(player["platform_player_id"])}">
        </label>
        """
        for index, player in enumerate(participants, start=1)
    )
    return f"""
      <details class="panel">
        <summary>Correct Match metadata</summary>
        <form method="post" action="/api/v1/operation" class="form-grid compact">
          {_hidden(state, "update_match_metadata")}
          <label>Title <input name="title" value="{_e(match["title"])}" required></label>
          <label>Game platform <input name="game_platform" value="{_e(match["game_platform"])}" required></label>
          <label>External Match ID <input name="external_match_id" value="{_e(match["external_match_id"])}"></label>
          <label>Played time <input name="played_at" value="{_e(match["played_at"])}"></label>
          <label>Source kind
            <select name="source_kind">
              {"".join(f'<option value="{kind}"{" selected" if kind == source["source_kind"] else ""}>{kind}</option>' for kind in ("youtube_video", "other_video", "manual_observation"))}
            </select>
          </label>
          <label>Source URL <input name="source_url" value="{_e(source["source_url"])}"></label>
          <label>Source title <input name="source_title" value="{_e(source["source_title"])}" required></label>
          <label>Channel <input name="source_channel_name" value="{_e(source["source_channel_name"])}"></label>
          <label>Match start <input name="match_timecode_start" value="{_e(source["match_timecode"]["start"])}"></label>
          <label>Match end <input name="match_timecode_end" value="{_e(source["match_timecode"]["end"])}"></label>
          {player_rows}
          <button type="submit">Save metadata</button>
        </form>
      </details>
    """


def _statistics_input(
    name: str,
    label: str,
    value: object,
    *,
    count: bool = False,
) -> str:
    constraints = ' min="0" step="1"' if count else ' min="0" max="100" step="any" required'
    return (
        f'<label>{_e(label)} <input type="number" name="{_e(name)}"'
        f'{constraints} value="{_e(value)}"></label>'
    )


def _statistics_form(state: dict[str, Any], player: dict[str, Any]) -> str:
    snapshot = player["statistics_snapshot"]
    record = None if snapshot is None else snapshot["statistics_record"]
    editable = record is not None and record["source"]["source_type"] in {
        "manual_entry",
        "online_platform",
    }
    form_record = record if editable else None
    source = {} if form_record is None else form_record["source"]
    percentages = {} if form_record is None else form_record["statistics"]
    counts = {} if form_record is None else form_record.get("exact_counts", {})
    source_type = source.get("source_type", "manual_entry")
    percentage_fields = (
        ("solo_games_played_percent", "Solo Games played %"),
        ("solo_games_won_percent", "Solo Games won %"),
        ("solo_hand_percent", "Solo Hand %"),
        ("suit_games_percent", "Suit Games %"),
        ("grand_games_percent", "Grand Games %"),
        ("null_games_percent", "Null Games %"),
        ("defender_games_played_percent", "Defender Games played %"),
        ("defender_games_won_percent", "Defender Games won %"),
    )
    count_fields = (
        ("solo_games_played", "Solo Games played"),
        ("solo_games_won", "Solo Games won"),
        ("solo_hand_games", "Solo Hand Games"),
        ("suit_games", "Suit Games"),
        ("grand_games", "Grand Games"),
        ("null_games", "Null Games"),
        ("defender_games_played", "Defender Games played"),
        ("defender_games_won", "Defender Games won"),
    )
    return f"""
      <details class="statistics-editor">
        <summary>{"Replace Snapshot" if snapshot is not None else "Add Snapshot"}</summary>
        <form method="post" action="/api/v1/operation" class="form-grid compact">
          {_hidden(state, "set_player_statistics_snapshot")}
          <input type="hidden" name="player_id" value="{_e(player["player_id"])}">
          <label>Snapshot ID (optional)
            <input name="snapshot_id" value="">
          </label>
          <label>Observed/captured time (RFC 3339)
            <input name="observed_at" value="{_e(source.get("captured_at"))}" required>
          </label>
          <label>Source type
            <select name="source_type">
              <option value="manual_entry"{" selected" if source_type == "manual_entry" else ""}>Manual entry</option>
              <option value="online_platform"{" selected" if source_type == "online_platform" else ""}>Online platform</option>
            </select>
          </label>
          <label>Source name
            <input name="source_name" value="{_e(source.get("source_name"))}" required>
          </label>
          <label>Source Player ID (optional)
            <input name="source_player_id" value="{_e(source.get("source_player_id"))}">
          </label>
          <label>Notes (optional)
            <input name="notes" value="{_e(source.get("notes"))}">
          </label>
          <label>Games played
            <input type="number" min="1" step="1" name="games_played" value="{_e(None if form_record is None else form_record["games_played"])}" required>
          </label>
          <fieldset class="statistics-fieldset">
            <legend>All eight percentages</legend>
            {"".join(_statistics_input(name, label, percentages.get(name)) for name, label in percentage_fields)}
          </fieldset>
          <fieldset class="statistics-fieldset">
            <legend>Optional exact Counts</legend>
            <p>Leave all eight blank, or provide the complete exact Count set.</p>
            {"".join(_statistics_input(name, label, counts.get(name), count=True) for name, label in count_fields)}
          </fieldset>
          <button type="submit">{"Replace Snapshot" if snapshot is not None else "Add Snapshot"}</button>
        </form>
      </details>
    """


def _statistics_card(state: dict[str, Any], player: dict[str, Any]) -> str:
    snapshot = player["statistics_snapshot"]
    if snapshot is None:
        retained = "<p>No Match-bound Snapshot retained.</p>"
        profile = "<p>No normalized Profile is available.</p>"
    else:
        record = snapshot["statistics_record"]
        source = record["source"]
        percentages = record["statistics"]
        counts = record.get("exact_counts")
        historical = source.get("historical_aggregation")
        retained = f"""
          <dl class="statistics-facts">
            <div><dt>Snapshot ID</dt><dd>{_e(snapshot["snapshot_id"])}</dd></div>
            <div><dt>Observed at</dt><dd>{_e(snapshot["observed_at"])}</dd></div>
            <div><dt>Source type</dt><dd>{_e(source["source_type"])}</dd></div>
            <div><dt>Source name</dt><dd>{_e(source["source_name"])}</dd></div>
            <div><dt>Source Player ID</dt><dd>{
            _e(source.get("source_player_id") or "None")
        }</dd></div>
            <div><dt>Games played</dt><dd>{record["games_played"]}</dd></div>
          </dl>
          {
            f'<p class="multiline"><strong>Notes:</strong> {_e(source.get("notes"))}</p>'
            if source.get("notes")
            else ""
        }
          <table class="statistics-table"><thead><tr><th>Statistic</th><th>Percentage</th><th>Exact Count</th></tr></thead>
            <tbody>
              {
            "".join(
                f"<tr><td>{_e(name.replace('_percent', '').replace('_', ' ').title())}</td><td>{_e(value)}</td><td>{_e('None' if counts is None else counts.get({'solo_games_played_percent': 'solo_games_played', 'solo_games_won_percent': 'solo_games_won', 'solo_hand_percent': 'solo_hand_games', 'suit_games_percent': 'suit_games', 'grand_games_percent': 'grand_games', 'null_games_percent': 'null_games', 'defender_games_played_percent': 'defender_games_played', 'defender_games_won_percent': 'defender_games_won'}[name]))}</td></tr>"
                for name, value in percentages.items()
            )
        }
            </tbody>
          </table>
          {
            f'''<div class="historical-provenance">
            <p><strong>Historical aggregation:</strong> retained read-only.</p>
            <dl class="statistics-facts">
              <div><dt>Dataset</dt><dd>{_e(historical["dataset_id"])} version {_e(historical["dataset_version"])}</dd></div>
              <div><dt>Partitions</dt><dd>{_e(", ".join(historical["included_partitions"]))}</dd></div>
              <div><dt>First played</dt><dd>{_e(historical["first_played_at"])}</dd></div>
              <div><dt>Last played</dt><dd>{_e(historical["last_played_at"])}</dd></div>
              <div><dt>Source record IDs</dt><dd>{_e(", ".join(historical["source_record_ids"]))}</dd></div>
              <div><dt>Source Game IDs</dt><dd>{_e(", ".join(historical["source_game_ids"]))}</dd></div>
            </dl>
          </div>'''
            if historical is not None
            else ""
        }
        """
        normalized = player["normalized_profile"]
        confidence = player["profile_confidence"]
        profile = f"""
          <dl class="statistics-facts">
            <div><dt>Classification</dt><dd>{_e(player["profile_classification"])}</dd></div>
            <div><dt>Derivation status</dt><dd>{_e(player["profile_derivation_status"])}</dd></div>
            <div><dt>Recommended preset</dt><dd>{_e(player["recommended_policy_preset"])}</dd></div>
            <div><dt>Actionable preset</dt><dd>{_e(player["actionable_policy_preset"] or "None")}</dd></div>
            <div><dt>Overall confidence</dt><dd>{_e(confidence["overall"]["level"])}</dd></div>
            <div><dt>Declarer confidence</dt><dd>{_e(confidence["declarer"]["level"])}</dd></div>
            <div><dt>Defender confidence</dt><dd>{_e(confidence["defender"]["level"])}</dd></div>
            <div><dt>Solo rate</dt><dd>{_e(normalized["solo_rate"])}</dd></div>
            <div><dt>Defender rate</dt><dd>{_e(normalized["defender_rate"])}</dd></div>
          </dl>
          <ul>{"".join(f"<li>{_e(item)}</li>" for item in player["profile_explanations"])}</ul>
        """
    temporal_messages = {
        "absent": "No Snapshot is available for temporal preparation.",
        "eligible": "Captured strictly before Match start; eligible for later retrospective Match analysis.",
        "match_time_unavailable": "Match played time is missing, so safe retrospective application is unavailable.",
        "captured_not_before_match": "Capture time is equal to or later than Match start; this Snapshot is descriptive only.",
    }
    clear_form = (
        ""
        if snapshot is None
        else f"""
        <form method="post" action="/api/v1/operation" class="inline-form" data-confirm="Clear this Match-bound Player Statistics Snapshot?">
          {_hidden(state, "clear_player_statistics_snapshot")}
          <input type="hidden" name="player_id" value="{_e(player["player_id"])}">
          <label><input type="checkbox" name="confirm_clear_snapshot" value="true" required> Confirm clear</label>
          <button type="submit">Clear Snapshot</button>
        </form>
        """
    )
    return f"""
      <article class="panel statistics-card">
        <p class="eyebrow">{_e(player["table_place"])}</p>
        <h3>{_e(player["player_label"] or player["player_id"])}</h3>
        {retained}
        <p class="temporal-status status-{_e(player["statistics_temporal_status"])}">{_e(temporal_messages[player["statistics_temporal_status"]])}</p>
        <h4>Prepared Profile</h4>
        {profile}
        {_statistics_form(state, player)}
        {clear_form}
      </article>
    """


def _player_statistics(state: dict[str, Any]) -> str:
    preparation = state["player_statistics_preparation"]
    return f"""
      <section class="player-statistics">
        <div class="section-heading">
          <p class="eyebrow">Private Match metadata</p>
          <h2>Player Statistics</h2>
          <p>Each participant may retain one immutable Match-bound Snapshot. A later Match may retain another Snapshot for the same stable Player.</p>
          <p>Only captures strictly before Match start enter the canonical eligible input. Missing Match time and equal or later captures remain descriptive. Eligible prepared Profiles can now be explicitly applied by Decision or Historical analysis forms.</p>
          <p><strong>Preparation:</strong> {_e(preparation["status"])}; eligible Players: {_e(", ".join(preparation["eligible_player_ids"]) or "None")}; actionable Profiles: {_e(", ".join(preparation["actionable_player_ids"]) or "None")}.</p>
        </div>
        <div class="statistics-grid">{"".join(_statistics_card(state, player) for player in state["participants"])}</div>
      </section>
    """


def _setup_forms(state: dict[str, Any]) -> str:
    game = state["game"]
    if game is None:
        return f"""
        <div class="action-row">
          <form method="post" action="/api/v1/operation">
            {_hidden(state, "start_game")}
            <label>Game ID (optional) <input name="game_id"></label>
            <label>Start <input name="game_timecode_start"></label>
            <label>End <input name="game_timecode_end"></label>
            <button type="submit" class="primary">Start Game</button>
          </form>
          <form method="post" action="/api/v1/operation">
            {_hidden(state, "mark_passed_deal")}
            <label>Start <input name="game_timecode_start"></label>
            <label>End <input name="game_timecode_end"></label>
            <button type="submit">Mark Passed Deal</button>
          </form>
        </div>
        """
    declaration = game["declaration"] or {}
    player_options = "".join(
        f'<option value="{_e(player["player_id"])}"'
        f"{' selected' if player['player_id'] == game['declarer_player_id'] else ''}>"
        f"{_e(player['player_label'] or player['player_id'])}</option>"
        for player in state["participants"]
    )
    game_type_options = "".join(
        f'<option value="{game_type}"'
        f"{' selected' if game_type == declaration.get('game_type') else ''}>"
        f"{game_type.title()}</option>"
        for game_type in state["declaration_options"]
    )
    return f"""
      <div class="setup-grid">
        <form method="post" action="/api/v1/operation" class="panel">
          <h3>Game time bounds</h3>{_hidden(state, "set_game_timecode")}
          <label>Start <input name="game_timecode_start" value="{_e(game["game_timecode"]["start"])}"></label>
          <label>End <input name="game_timecode_end" value="{_e(game["game_timecode"]["end"])}"></label>
          <button type="submit">Save time bounds</button>
        </form>
        <form method="post" action="/api/v1/operation" class="panel">
          <h3>Perspective hand</h3>{_hidden(state, "set_perspective_hand")}
          <label><input type="radio" name="card_evidence_mode" value="unknown"{" checked" if game["perspective_initial_hand"] is None else ""}> Unknown</label>
          <label><input type="radio" name="card_evidence_mode" value="exact"{" checked" if game["perspective_initial_hand"] is not None else ""}> Exact ten Cards</label>
          {_setup_card_selector(game["perspective_initial_hand"])}
          <button type="submit">Save hand evidence</button>
        </form>
        <form method="post" action="/api/v1/operation" class="panel declaration-form">
          <h3>Declaration</h3>{_hidden(state, "set_declaration")}
          <label>Declarer <select name="declarer_player_id"><option value="">Unknown</option>{player_options}</select></label>
          <label>Game type <select name="game_type"><option value="">Unknown</option>{game_type_options}</select></label>
          <label><input type="checkbox" name="hand_game"{" checked" if declaration.get("hand_game") else ""}> Hand</label>
          <label><input type="checkbox" name="ouvert"{" checked" if declaration.get("ouvert") else ""}> Ouvert</label>
          <label><input type="checkbox" name="schneider_announced"{" checked" if declaration.get("schneider_announced") else ""}> Schneider announced</label>
          <label><input type="checkbox" name="schwarz_announced"{" checked" if declaration.get("schwarz_announced") else ""}> Schwarz announced</label>
          <label>Matadors <input type="number" min="1" name="matadors" value="{_e(declaration.get("matadors"))}"></label>
          <label>Bid value <input type="number" min="1" name="bid_value" value="{_e(declaration.get("bid_value"))}"></label>
          <button type="submit">Save declaration</button>
        </form>
        {_card_evidence_form(state, "set_original_skat", "Original Skat", game["original_skat"], False)}
        {_card_evidence_form(state, "set_discarded_cards", "Discards", game["discarded_cards"], True)}
      </div>
    """


def _card_evidence_form(
    state: dict[str, Any],
    operation: str,
    heading: str,
    cards: list[str] | None,
    allow_empty: bool,
) -> str:
    known_empty = cards == []
    exact = cards is not None and not known_empty
    empty_option = (
        f'<label><input type="radio" name="card_evidence_mode" value="known_empty"'
        f"{' checked' if known_empty else ''}> Known empty (Hand)</label>"
        if allow_empty
        else ""
    )
    return f"""
      <form method="post" action="/api/v1/operation" class="panel">
        <h3>{heading}</h3>{_hidden(state, operation)}
        <label><input type="radio" name="card_evidence_mode" value="unknown"{" checked" if cards is None else ""}> Unknown</label>
        {empty_option}
        <label><input type="radio" name="card_evidence_mode" value="exact"{" checked" if exact else ""}> Exact two Cards</label>
        {_setup_card_selector(cards)}
        <button type="submit">Save {heading.lower()}</button>
      </form>
    """


def _setup_card_selector(selected_cards: list[str] | None) -> str:
    selected = set(selected_cards or ())
    cards = []
    for suit, suit_name in (("C", "Clubs"), ("S", "Spades"), ("H", "Hearts"), ("D", "Diamonds")):
        for rank, rank_name in (
            ("A", "Ace"),
            ("10", "Ten"),
            ("K", "King"),
            ("Q", "Queen"),
            ("J", "Jack"),
            ("9", "Nine"),
            ("8", "Eight"),
            ("7", "Seven"),
        ):
            code = f"{suit}{rank}"
            cards.append(
                f'<label class="setup-card suit-{suit.lower()}">'
                f'<input type="checkbox" name="cards" value="{code}"'
                f"{' checked' if code in selected else ''}>"
                f"<strong>{code}</strong><span>{suit_name} {rank_name}</span></label>"
            )
    return f'<div class="setup-card-selector">{"".join(cards)}</div>'


def _palette(state: dict[str, Any]) -> str:
    view = state["position_view"]
    if view["card_selection_scope"] == "exact_legal_cards":
        scope_label = "Exact legal cards"
    elif view["card_selection_scope"] == "bounded_observation_candidates":
        scope_label = "Observed-card candidates; ownership may be unknown"
    else:
        scope_label = "Card entry unavailable"
    cards = "".join(
        f"""
        <form method="post" action="/api/v1/operation" class="card-button-form">
          {_hidden(state, "append_plays")}
          <button type="submit" name="cards" value="{card["code"]}"
            class="card suit-{card["code"][0].lower()}"{" disabled" if not card["selectable"] else ""}
            title="{_e(card["label"])}">
            <strong>{_e(card["code"])}</strong><span>{_e(card["label"])}</span>
          </button>
        </form>
        """
        for card in state["card_palette"]
    )
    return f"""
      <section class="panel play-entry" data-play-entry>
        <p class="scope-label">{scope_label}</p>
        <h3>Next Player: {_e(view["next_player_id"] or "None")}</h3>
        <form method="post" action="/api/v1/operation" class="card-code-form">
          {_hidden(state, "append_plays")}
          <label>Card code or atomic batch
            <input name="cards" data-card-input autocomplete="off" placeholder="CA or CA, S7, C7">
          </label>
          <label>Decision timecode <input name="decision_timecode" placeholder="12:34.500"></label>
          <button type="submit">Append Card code</button>
        </form>
        <div class="card-palette">{cards}</div>
      </section>
    """


def _play_history(state: dict[str, Any]) -> str:
    game = state["game"]
    if game is None:
        return ""
    plays = "".join(
        f"<tr><td>{play['decision_index']}</td><td>{play['trick_number']}</td>"
        f"<td>{_e(play['player_id'])}</td><td>{_e(play['card'])}</td>"
        f"<td>{_e(play['decision_timecode_text'])}</td></tr>"
        for play in game["plays"]
    )
    options = "".join(
        f'<option value="{count}">{count} retained Plays</option>'
        for count in range(len(game["plays"]) + 1)
    )
    return f"""
      <section class="panel">
        <h3>Play history</h3>
        <table><thead><tr><th>Decision</th><th>Trick</th><th>Player</th><th>Card</th><th>Time</th></tr></thead>
        <tbody>{plays or '<tr><td colspan="5">No Plays retained.</td></tr>'}</tbody></table>
        <div class="action-row">
          <form method="post" action="/api/v1/operation" data-undo-form>
            {_hidden(state, "truncate_plays")}
            <input type="hidden" name="target_play_count" value="{max(0, len(game["plays"]) - 1)}">
            <button type="submit"{" disabled" if not game["plays"] else ""}>Undo last Play</button>
          </form>
          <form method="post" action="/api/v1/operation">
            {_hidden(state, "truncate_plays")}
            <label>Explicit truncation <select name="target_play_count">{options}</select></label>
            <button type="submit">Truncate</button>
          </form>
        </div>
      </section>
    """


def _annotations(state: dict[str, Any]) -> str:
    game = state["game"]
    if game is None:
        return ""
    if not game["plays"]:
        return """
        <section class="panel annotations">
          <h3>Commentary and Response Links</h3>
          <p>Commentary becomes available after the first retained Decision.</p>
        </section>
        """
    decision_options = _decision_options(game)
    commentator_options = _commentator_options(state)
    commentary_rows = []
    for commentary in game["commentaries"]:
        selected_decisions = _decision_options(
            game,
            selected=commentary["decision_index"],
        )
        selected_commentator_options = _commentator_options(
            state,
            selected=commentary["commentator_player_id"],
        )
        later = _later_decision_options(
            game,
            after=commentary["decision_index"],
        )
        links = [
            link
            for link in game["response_links"]
            if link["commentary_id"] == commentary["commentary_id"]
        ]
        link_rows = "".join(
            f"""
            <li>
              <form method="post" action="/api/v1/operation" class="inline-form">
                {_hidden(state, "set_response_link")}
                <input type="hidden" name="commentary_id" value="{_e(commentary["commentary_id"])}">
                <input type="hidden" name="link_id" value="{_e(link["link_id"])}">
                <label>Response Decision
                  <select name="response_decision_index">{_later_decision_options(game, after=commentary["decision_index"], selected=link["response_decision_index"])}</select>
                </label>
                <button type="submit">Replace link</button>
              </form>
              <form method="post" action="/api/v1/operation" class="inline-form">
                {_hidden(state, "remove_response_link")}
                <input type="hidden" name="link_id" value="{_e(link["link_id"])}">
                <button type="submit">Remove link</button>
              </form>
            </li>
            """
            for link in links
        )
        commentary_rows.append(
            f"""
            <article class="commentary-card">
              <h4>Decision #{commentary["decision_index"]} - {_e(commentary["subject_player_id"])}</h4>
              <p class="multiline">{_e(commentary["text"])}</p>
              <p>Commentator: {_e(commentary["commentator_player_id"] or commentary["commentator_name"])}</p>
              {f'<p class="warning">Removing this Commentary also removes {len(links)} Response Link(s).</p>' if links else ""}
              <form method="post" action="/api/v1/operation" class="form-grid compact">
                {_hidden(state, "set_commentary")}
                <input type="hidden" name="commentary_id" value="{_e(commentary["commentary_id"])}">
                <label>Decision <select name="decision_index">{selected_decisions}</select></label>
                <label>Match Player <select name="commentator_player_id"><option value="">None</option>{selected_commentator_options}</select></label>
                <label>External name <input name="commentator_name" value="{_e(commentary["commentator_name"])}"></label>
                <label>Timecode <input name="commentary_timecode" value="{_e(commentary["commentary_timecode_text"])}"></label>
                <label>Text <textarea name="text" rows="3" required>{_e(commentary["text"])}</textarea></label>
                <button type="submit">Update Commentary</button>
              </form>
              <form method="post" action="/api/v1/operation" class="inline-form" data-confirm="Removing Commentary also removes its Response Links. Continue?">
                {_hidden(state, "remove_commentary")}
                <input type="hidden" name="commentary_id" value="{_e(commentary["commentary_id"])}">
                <button type="submit">Remove Commentary</button>
              </form>
              <form method="post" action="/api/v1/operation" class="inline-form">
                {_hidden(state, "set_response_link")}
                <input type="hidden" name="commentary_id" value="{_e(commentary["commentary_id"])}">
                <label>Later response <select name="response_decision_index">{later}</select></label>
                <button type="submit"{" disabled" if not later else ""}>Add Response Link</button>
              </form>
              <ul>{link_rows}</ul>
            </article>
            """
        )
    return f"""
      <section class="panel annotations">
        <h3>Commentary and Response Links</h3>
        <p>Free-text observations only. No causality, quality, signal, or optimality is inferred.</p>
        <form method="post" action="/api/v1/operation" class="form-grid compact">
          {_hidden(state, "set_commentary")}
          <label>Decision <select name="decision_index">{decision_options}</select></label>
          <label>Match Player commentator <select name="commentator_player_id"><option value="">None</option>{commentator_options}</select></label>
          <label>External commentator <input name="commentator_name"></label>
          <label>Timecode <input name="commentary_timecode"></label>
          <label>Commentary <textarea name="text" rows="4" required></textarea></label>
          <button type="submit">Add Commentary</button>
        </form>
        {"".join(commentary_rows)}
      </section>
    """


def _decision_options(game: dict[str, Any], selected: int | None = None) -> str:
    return "".join(
        f'<option value="{play["decision_index"]}"'
        f"{' selected' if play['decision_index'] == selected else ''}>"
        f"#{play['decision_index']} {_e(play['player_id'])} - "
        f"{_e(play['card'])}</option>"
        for play in game["plays"]
    )


def _commentator_options(state: dict[str, Any], selected: str | None = None) -> str:
    return "".join(
        f'<option value="{_e(player["player_id"])}"'
        f"{' selected' if player['player_id'] == selected else ''}>"
        f"{_e(player['player_label'] or player['player_id'])}</option>"
        for player in state["participants"]
    )


def _later_decision_options(
    game: dict[str, Any],
    *,
    after: int,
    selected: int | None = None,
) -> str:
    return "".join(
        f'<option value="{play["decision_index"]}"'
        f"{' selected' if play['decision_index'] == selected else ''}>"
        f"#{play['decision_index']} {_e(play['player_id'])} - "
        f"{_e(play['card'])}</option>"
        for play in game["plays"]
        if play["decision_index"] > after
    )


def _report_navigation(state: dict[str, Any]) -> str:
    reports = state["reports"]
    links = "".join(
        f'<a class="report-link{" selected" if report["selected"] else ""}" '
        f'href="/reports/{report["report_id"]}" data-report-link>'
        f"<strong>{_e(report['report_kind'].replace('_', ' ').title())}</strong>"
        f"<span>{_e(report['status'].replace('_', ' '))}</span>"
        f"<small>{_e(report['report_id'][:12])}</small></a>"
        for report in reports
    )
    return f"""
      <section class="panel reports-navigation">
        <div class="section-heading">
          <p class="eyebrow">Ephemeral current-revision reports</p>
          <h2>Analysis reports</h2>
          <p>Reports stay in memory only and disappear after an applied change, Reload, or server stop.</p>
        </div>
        <div class="report-links">{links or "<p>No reports prepared for this revision.</p>"}</div>
      </section>
    """


def _download_warning() -> str:
    return (
        '<p class="private-warning"><strong>Private local download:</strong> '
        "downloaded analysis may contain exact hands, historical results, and "
        "Player Profile application details. Store it accordingly.</p>"
    )


def _decision_report(state: dict[str, Any], report: dict[str, Any]) -> str:
    details = report["details"]
    if details["status"] == "unavailable":
        content = f"""
          <p class="normal-unavailable">Decision analysis is normally unavailable: {_e(_label(details["unavailable_reason"]))}.</p>
          {f"<p>Preparation reason: {_e(_label(details['skipped_reason']))}.</p>" if details["skipped_reason"] else ""}
        """
    else:
        method = details["recommendation_method"]
        recommendation = details["recommendation"] or {}
        review = details["post_game_review"] or {}
        search_review = details["search_post_game_review"]
        immediate_rows = "".join(
            f"<tr><td>{_e(item.get('card'))}</td><td>{_e(item.get('expected_point_swing'))}</td>"
            f"<td>{_e(item.get('win_rate'))}</td><td>{_e(_label(item.get('is_recommended')))}</td></tr>"
            for item in details["immediate_candidate_values"]
        )
        search = details["bounded_search"]
        search_html = "<p>No bounded Search was requested.</p>"
        if search is not None:
            candidate_rows = "".join(
                f"<tr><td>{_e(item.get('rank'))}</td><td>{_e(item.get('card'))}</td>"
                f"<td>{_e(item.get('local_contract_success_rate'))}</td>"
                f"<td>{_e(item.get('mean_local_side_game_score'))}</td>"
                f"<td>{_e(item.get('mean_local_side_card_point_margin'))}</td></tr>"
                for item in search["candidate_results"]
            )
            search_html = f"""
              {
                _facts(
                    (
                        ("Status", search["status"]),
                        ("Stop reason", search["stop_reason"]),
                        ("World coverage", search["world_coverage"]),
                        ("Solution claim", search["solution_claim"]),
                        ("Selected worlds", search["selected_world_count"]),
                        ("Completed worlds", search["completed_world_count"]),
                        ("Fallback used", search["fallback_used"]),
                        ("Fallback method", search["fallback_method"]),
                    )
                )
            }
              <table><thead><tr><th>Rank</th><th>Card</th><th>Contract success</th><th>Mean settlement</th><th>Mean point margin</th></tr></thead>
              <tbody>{
                candidate_rows or '<tr><td colspan="5">No completed candidate aggregates.</td></tr>'
            }</tbody></table>
              <p class="bounded-note">Bounded compatible-world determinization aggregates do not claim a perfect or optimal imperfect-information policy.</p>
            """
        information_set = details["information_set_search"]
        information_set_html = "<p>No Information-set Search was requested.</p>"
        if information_set is not None:
            information_set_html = f"""
              {
                _facts(
                    (
                        ("Status", information_set["status"]),
                        ("Stop reason", information_set["stop_reason"]),
                        ("World coverage", information_set["world_coverage"]),
                        ("Policy claim", information_set["policy_claim"]),
                        ("Policy consistency", information_set["policy_consistency"]),
                        ("Compatible worlds", information_set["compatible_world_count"]),
                        ("Selected worlds", information_set["selected_world_count"]),
                        ("Completed worlds", information_set["completed_world_count"]),
                        (
                            "Information sets evaluated",
                            information_set["information_sets_evaluated"],
                        ),
                        (
                            "Controlled Policy Decisions",
                            information_set["controlled_policy_decision_count"],
                        ),
                        ("Fixed Policy Decisions", information_set["fixed_policy_decision_count"]),
                        (
                            "Information-set Card",
                            information_set["information_set_recommended_card"],
                        ),
                        ("Same-selection PIMC Card", information_set["pimc_recommended_card"]),
                        (
                            "Independent Immediate Card",
                            information_set["immediate_recommended_card"],
                        ),
                        ("Actual Card", information_set["actual_card"]),
                        (
                            "Information-set / PIMC agreement",
                            information_set["information_set_pimc_same_card"],
                        ),
                        (
                            "Information-set / Immediate agreement",
                            information_set["information_set_immediate_same_card"],
                        ),
                        (
                            "Information-set / actual agreement",
                            information_set["information_set_actual_same_card"],
                        ),
                    )
                )
            }
              <p class="bounded-note">This is a bounded controlled-player Policy over selected compatible Worlds. Fixed opponents use the effective deterministic Match Policies; the result is not calibrated probability, ground truth, or a complete optimal imperfect-information policy.</p>
            """
        profile_cards = "".join(
            f"""
            <article class="profile-application-card">
              <h4>{side.title()} opponent: {_e(profile["opponent_player_id"])}</h4>
              {
                _facts(
                    (
                        ("Temporal status", profile["temporal_status"]),
                        ("Profile available", profile["profile_available"]),
                        ("Actionable preset", profile["actionable_policy_preset"]),
                        ("Application status", profile["application_status"]),
                        ("Not applied reason", profile["not_applied_reason"]),
                        ("Applied preset", profile["applied_policy_preset"]),
                        ("Effective lead policy", profile["effective_lead_policy"]),
                        ("Effective response policy", profile["effective_response_policy"]),
                    )
                )
            }
            </article>
            """
            for side, profile in details["profiles"].items()
        )
        content = f"""
          {
            _facts(
                (
                    ("Acting Player", details["acting_player_id"]),
                    ("Actual Card", details["actual_card"]),
                    ("Requested method", method.get("requested_method")),
                    ("Effective method", method.get("effective_method")),
                    ("Fallback used", method.get("fallback_used")),
                    ("Recommended Card", recommendation.get("card")),
                    ("Review available", review.get("is_available")),
                    ("Decision quality", review.get("decision_quality")),
                    ("Review status", review.get("reason")),
                )
            )
        }
          <h3>Recommendation</h3>
          <p><strong>Reason:</strong> {_e(recommendation.get("reason"))}</p>
          <p><strong>Legal Cards:</strong> {_e(", ".join(details["legal_cards"]) or "None")}</p>
          <p><strong>Strategic summary:</strong> {_e(details["strategic_summary"])}</p>
          <p><strong>Retrospective actual-Card review:</strong> {
            _e(review.get("decision_explanation"))
        }</p>
          {
            (
                "<p>No bounded Search actual-Card comparison.</p>"
                if search_review is None
                else "<h4>Bounded Search actual-Card comparison</h4>" + _curated_json(search_review)
            )
        }
          <h3>Immediate candidate values</h3>
          <table><thead><tr><th>Card</th><th>Expected point swing</th><th>Win rate</th><th>Recommended</th></tr></thead>
          <tbody>{
            immediate_rows
            or '<tr><td colspan="4">No Immediate candidate values in this result.</td></tr>'
        }</tbody></table>
          <h3>Bounded Search</h3>{search_html}
          <h3>Information-set Search</h3>{information_set_html}
          <h3>Eligible Profile binding and application</h3>
          <div class="profile-application-grid">{profile_cards}</div>
        """
    download = (
        f'<a class="download-link" href="/api/v1/reports/{report["report_id"]}.json">Download exact cached Root Result JSON</a>'
        if state["download_availability"]["report_result"]
        else "<p>This unavailable report has no Root Result download.</p>"
    )
    strategy_source_download = (
        f'<a class="download-link" href="/api/v1/reports/{report["report_id"]}/strategy-source.json">Download for Learning Corpus</a>'
        if details["status"] == "executed"
        else ""
    )
    return f"""
      <section class="panel selected-report decision-report">
        <p class="eyebrow">Decision Analysis report</p>
        <h2>Position {details["match_position"]}, Decision {details["decision_index"]}</h2>
        {_facts((("Match", report["match_id"]), ("Game", details["game_id"]), ("Report ID", report["report_id"])))}
        {content}
        {_download_warning()}{download}{strategy_source_download}
      </section>
    """


def _historical_report(state: dict[str, Any], report: dict[str, Any]) -> str:
    details = report["details"]
    if details["status"] == "unavailable":
        content = (
            '<p class="normal-unavailable">Strict Historical analysis is normally '
            f"unavailable: {_e(_label(details['unavailable_reason']))}.</p>"
        )
    else:
        declaration = details["declaration"] or {}
        settlement = details["settlement"] or {}
        game_result = details["game_result"] or {}
        game_value = details["game_value"] or {}
        overbid = details["overbid"] or {}
        snapshots = details["decision_snapshots"]
        review = details["immediate_review"]
        search = details["search_review"]
        coaching = details["replay_coaching"]
        profile = details["profile_application"]
        review_html = "<p>Not requested.</p>"
        if review is not None:
            quality = review.get("quality_counts") or {}
            review_html = _facts(
                (
                    ("Decision count", review.get("decision_count")),
                    ("Reviewed", review.get("reviewed_decision_count")),
                    ("Unavailable", review.get("unavailable_decision_count")),
                    ("Optimal", quality.get("optimal")),
                    ("Acceptable", quality.get("acceptable")),
                    ("Suboptimal", quality.get("suboptimal")),
                    ("Mistake", quality.get("mistake")),
                )
            )
        search_html = "<p>Not requested.</p>"
        if search is not None:
            counts = search.get("decision_counts") or {}
            statuses = search.get("status_counts") or {}
            coverage = search.get("coverage") or {}
            agreement = search.get("search_vs_immediate_agreement") or {}
            quality = search.get("quality_gate") or {}
            actual = search.get("actual_card_agreement") or {}
            performance = search.get("performance") or {}
            search_html = _facts(
                (
                    ("Decisions attempted", counts.get("search_attempted_count")),
                    ("Search recommendations", counts.get("search_recommendation_count")),
                    ("Complete", statuses.get("complete")),
                    ("Partial", statuses.get("partial")),
                    ("Timeout", statuses.get("timeout")),
                    ("Unavailable", statuses.get("unavailable")),
                    ("Exact coverage", coverage.get("exact_coverage_decision_count")),
                    ("Sampled coverage", coverage.get("sampled_coverage_decision_count")),
                    ("No coverage", coverage.get("no_coverage_decision_count")),
                    ("Same recommendation rate", agreement.get("same_recommended_card_rate")),
                    ("Quality gate passed", quality.get("quality_gate_passed")),
                    ("Quality violations", quality.get("quality_violation_count")),
                    ("Actual Card top-1 rate", actual.get("actual_top_1_rate")),
                    (
                        "Nodes expanded total",
                        (performance.get("nodes_expanded") or {}).get("total"),
                    ),
                    (
                        "Completed worlds total",
                        (performance.get("completed_world_count") or {}).get("total"),
                    ),
                    ("Fallback count", performance.get("fallback_count")),
                )
            )
        coaching_html = "<p>Not requested.</p>"
        if coaching is not None:
            coverage = coaching.get("coverage_summary") or {}
            prioritization = coaching.get("prioritization") or {}
            guidance = coaching.get("guidance") or {}
            outcome = coaching.get("outcome_context") or {}
            key_decisions = prioritization.get("key_decisions", [])
            turning_points = prioritization.get("turning_points", [])
            decision_recommendations = guidance.get("decision_recommendations", [])
            pattern_recommendations = guidance.get("pattern_recommendations", [])
            coaching_html = f"""
              {
                _facts(
                    (
                        ("Method", coaching.get("report_method")),
                        ("Assessable Decisions", coverage.get("assessable_decision_count")),
                        ("Not assessable", coverage.get("not_assessable_count")),
                        ("High-impact Decisions", coverage.get("high_impact_decision_count")),
                        (
                            "Recorded winner",
                            (outcome.get("game_result_summary") or {}).get("winner"),
                        ),
                        (
                            "Recorded settlement",
                            (outcome.get("final_settlement_summary") or {}).get("settlement_score"),
                        ),
                    )
                )
            }
              <h4>Key Decisions</h4>{_curated_json(key_decisions)}
              <h4>Turning Points</h4>{_curated_json(turning_points)}
              <h4>Decision Recommendations</h4>{_curated_json(decision_recommendations)}
              <h4>Pattern Recommendations</h4>{_curated_json(pattern_recommendations)}
              <p><strong>Limitations:</strong> {
                _e(", ".join(coaching.get("limitations") or []) or "None")
            }</p>
            """
        profile_html = "<p>No eligible Match Profile input was applied.</p>"
        if profile is not None:
            participant_rows = "".join(
                f"<tr><td>{_e(item.get('player_id'))}</td>"
                f"<td>{_e(_label(item.get('match_status')))}</td>"
                f"<td>{_e(_label(item.get('temporal_status')))}</td>"
                f"<td>{_e(_label(item.get('derivation_status')))}</td>"
                f"<td>{_e(_label(item.get('actionable_policy_preset')))}</td></tr>"
                for item in profile.get("participant_matches", [])
            )
            profile_html = f"""
              {
                _facts(
                    (
                        ("Temporal rule", profile.get("temporal_rule")),
                        ("Matched Players", profile.get("matched_player_count")),
                        (
                            "Unmatched Players",
                            ", ".join(profile.get("unmatched_player_ids") or []) or "None",
                        ),
                    )
                )
            }
              <table><thead><tr><th>Player</th><th>Match status</th><th>Temporal status</th><th>Derivation</th><th>Actionable preset</th></tr></thead>
              <tbody>{participant_rows}</tbody></table>
            """
        content = f"""
          {
            _facts(
                (
                    ("Declarer", details["declarer_player_id"]),
                    ("Game type", declaration.get("game_type")),
                    ("Hand", declaration.get("hand_game")),
                    ("Ouvert", declaration.get("ouvert")),
                    ("Bid", declaration.get("bid_value")),
                    ("Historical status", details["status"]),
                    ("Winner", details["winner"]),
                    ("Declarer points", details["declarer_points"]),
                    ("Defender points", details["defender_points"]),
                    ("Result winner", game_result.get("winner")),
                    ("Game value", game_value.get("game_value")),
                    ("Overbid status", overbid.get("status")),
                    ("Settlement score", settlement.get("settlement_score")),
                    ("Settlement complete", settlement.get("is_complete")),
                )
            )
        }
          <h3>Decision Snapshot coverage</h3>
          {
            (
                "<p>Not requested.</p>"
                if snapshots is None
                else _facts(
                    (
                        ("Snapshot count", snapshots["snapshot_count"]),
                        ("Game-end reason", snapshots["game_end_reason"]),
                    )
                )
            )
        }
          <h3>Immediate Review coverage and agreement</h3>
          {review_html}
          <h3>Historical bounded Search Review</h3>
          {search_html}
          <p class="bounded-note">Search coverage may be complete, partial, timeout, or unavailable. It remains bounded determinization evidence, not a perfect-play claim.</p>
          <h3>Replay Coaching</h3>
          {coaching_html}
          <p class="bounded-note">Coaching is retrospective and non-causal. It does not infer that Commentary caused a later Decision.</p>
          <h3>Historical Profile application</h3>
          {profile_html}
        """
    download = (
        f'<a class="download-link" href="/api/v1/reports/{report["report_id"]}.json">Download exact cached Historical Root Result JSON</a>'
        if state["download_availability"]["report_result"]
        else "<p>This unavailable report has no Root Result download.</p>"
    )
    return f"""
      <section class="panel selected-report historical-report">
        <p class="eyebrow">Historical Analysis report</p>
        <h2>Position {details["match_position"]}: {_e(details["game_id"] or "Unavailable Game")}</h2>
        {_facts((("Match", report["match_id"]), ("Report ID", report["report_id"])))}
        {content}
        {_download_warning()}{download}
      </section>
    """


def _materialization_report(state: dict[str, Any], report: dict[str, Any]) -> str:
    details = report["details"]
    historical_rows = "".join(
        f"<tr><td>{item['match_position']}</td><td>{_e(_label(item['reason']))}</td></tr>"
        for item in details["historical_unavailable"]
    )
    list_value = details["historical_list"]
    standings = "".join(
        f"<tr><td>{standing['rank']}</td><td>{_e(standing['player_totals']['player_id'])}</td>"
        f"<td>{standing['player_totals']['total_performance_points']}</td>"
        f"<td>{standing['player_totals']['player_game_points']}</td>"
        f"<td>{standing['player_totals']['own_games_won']}</td>"
        f"<td>{standing['player_totals']['own_games_lost']}</td></tr>"
        for standing in list_value["final_standings"]
    )
    progression_rows = []
    for item in list_value["round_end_progression"]:
        standings_text = ", ".join(
            f"rank {standing['rank']} "
            f"{standing['player_totals']['player_id']} "
            f"{standing['player_totals']['total_performance_points']}"
            for standing in item["provisional_standings"]
        )
        progression_rows.append(
            f"<tr><td>{item['entry_fact']['round_number']}</td>"
            f"<td>{item['entry_fact']['entry_number']}</td>"
            f"<td>{_e(standings_text)}</td></tr>"
        )
    progression = "".join(progression_rows)
    downloads = [
        ("materialization", "materialization.json", "Materialization summary"),
        ("historical_games", "historical-games.json", "Historical Games"),
        ("training_sources", "training-sources.json", "Training sources"),
        ("historical_list_input", "historical-list-input.json", "Historical list input"),
        (
            "historical_list_aggregation",
            "historical-list-aggregation.json",
            "Historical list aggregation",
        ),
    ]
    links = "".join(
        f'<a class="download-link" href="/api/v1/exports/{path}">Download {_e(label)} JSON</a>'
        for key, path, label in downloads
        if state["download_availability"][key]
    )
    return f"""
      <section class="panel selected-report materialization-report">
        <p class="eyebrow">Prepared Match summary</p>
        <h2>{_e(report["match_id"])}, revision {report["workspace_revision"]}</h2>
        {
        _facts(
            (
                ("Status", details["status"]),
                ("Occupied Slots", details["occupied_slot_count"]),
                ("Empty Slots", details["empty_slot_count"]),
                ("Observed Games", details["observed_game_count"]),
                ("Passed Deals", details["passed_deal_count"]),
                ("Prepared Decisions", details["prepared_decision_count"]),
                ("Skipped Decisions", details["skipped_decision_count"]),
                ("Strict Historical Games", details["historical_game_count"]),
                ("Training source Records", details["training_record_count"]),
                ("Commentary count", details["commentary_count"]),
                ("Response Link count", details["response_link_count"]),
            )
        )
    }
        <h3>Strict Historical unavailability</h3>
        <table><thead><tr><th>Position</th><th>Reason</th></tr></thead><tbody>{
        historical_rows or '<tr><td colspan="2">None.</td></tr>'
    }</tbody></table>
        <h3>Fixed 36-position list</h3>
        {
        _facts(
            (
                ("Availability", list_value["status"]),
                ("Unavailable reason", list_value["unavailable_reason"]),
                ("Ranking status", list_value["ranking_status"]),
                (
                    "Lot required Players",
                    ", ".join(list_value["lot_required_player_ids"]) or "None",
                ),
                (
                    "Applied lot order",
                    None
                    if list_value["applied_lot_order"] is None
                    else ", ".join(list_value["applied_lot_order"]),
                ),
            )
        )
    }
        <h3>Final standings</h3>
        <table><thead><tr><th>Rank</th><th>Player</th><th>Performance points</th><th>Game points</th><th>Own wins</th><th>Own losses</th></tr></thead>
        <tbody>{
        standings
        or '<tr><td colspan="6">Unavailable until the complete list materializes.</td></tr>'
    }</tbody></table>
        <h3>Round-end Progression</h3>
        <table><thead><tr><th>Round</th><th>Entry</th><th>Provisional standings</th></tr></thead>
        <tbody>{
        progression
        or '<tr><td colspan="3">Unavailable until the complete list materializes.</td></tr>'
    }</tbody></table>
        {_download_warning()}<div class="download-links">{links}</div>
      </section>
    """


def _selected_report(state: dict[str, Any]) -> str:
    report = state["selected_report"]
    if report is None:
        return ""
    if report["report_kind"] == "decision_analysis":
        content = _decision_report(state, report)
    elif report["report_kind"] == "historical_analysis":
        content = _historical_report(state, report)
    else:
        content = _materialization_report(state, report)
    position = report["match_position"] or state["selected_position"]
    return f"""
      <nav class="report-back"><a href="/position/{position}">Back to current position</a></nav>
      {content}
    """


def _materialization_controls(state: dict[str, Any]) -> str:
    return f"""
      <section class="panel analysis-control materialization-control">
        <p class="eyebrow">Explicit preparation, no workflow execution</p>
        <h2>Match materialization</h2>
        <p>Prepare one revision-scoped summary of Decision coverage, strict Historical Games, Training sources, and fixed-list availability.</p>
        <form method="post" action="/api/v1/analysis" data-native-submit>
          {_hidden(state, "prepare_materialization")}
          <button type="submit" class="primary">Prepare Match summary</button>
        </form>
      </section>
    """


def _decision_analysis_controls(state: dict[str, Any]) -> str:
    preparation = state["decision_preparation"]
    if state["game"] is None:
        return ""
    rows = "".join(
        f"<tr><td>{item['decision_index']}</td><td>{_e(item['acting_player_id'])}</td>"
        f"<td>{_e(item['actual_card'])}</td><td>{_e(item['state'])}</td>"
        f"<td>{_e(_label(item['reason']))}</td></tr>"
        for item in preparation["decisions"]
    )
    options = "".join(
        f'<option value="{item["decision_index"]}">#{item["decision_index"]} '
        f"{_e(item['acting_player_id'])} - {_e(item['actual_card'])}</option>"
        for item in preparation["decisions"]
        if item["state"] == "prepared"
    )
    return f"""
      <section class="panel analysis-control decision-analysis-control">
        <p class="eyebrow">Explicit post-game Decision analysis</p>
        <h2>Observed Game Decisions</h2>
        {
        _facts(
            (
                ("Preparation status", preparation["status"]),
                ("Source Plays", preparation["source_play_count"]),
                ("Prepared Decisions", preparation["prepared_decision_count"]),
                ("Skipped Decisions", preparation["skipped_decision_count"]),
            )
        )
    }
        <table><thead><tr><th>Decision</th><th>Actor</th><th>Actual Card</th><th>State</th><th>Reason</th></tr></thead>
        <tbody>{rows or '<tr><td colspan="5">No retained Plays.</td></tr>'}</tbody></table>
        <form method="post" action="/api/v1/analysis" class="form-grid analysis-form" data-analysis-method-form data-native-submit>
          {_hidden(state, "analyze_decision")}
          <label>Prepared Decision <select name="decision_index" required>{options}</select></label>
          <label>Recommendation method
            <select name="recommendation_method" data-analysis-method>
              <option value="immediate_expected_value">Immediate expected value</option>
              <option value="bounded_search">Bounded Search</option>
              <option value="auto">Auto Search with Immediate fallback</option>
              <option value="information_set_search">Information-set Search</option>
            </select>
          </label>
          <label>Immediate sample count <input type="number" min="1" max="100000" name="immediate_sample_count" value="100" required></label>
          <label>Immediate random seed <input type="number" name="immediate_random_seed" value="0" required></label>
          <div class="search-settings" data-search-settings>
            <label>Search random seed <input type="number" name="search_random_seed" value="0"></label>
            <label>Search budget profile
              <select name="search_budget_profile">
                <option value="historical_review_v1">Historical review</option>
                <option value="interactive_v1">Interactive</option>
              </select>
            </label>
          </div>
          <label class="checkbox-label"><input type="checkbox" name="use_profile_presets" value="true" checked> Use eligible Player Profile Presets</label>
          <p class="analysis-warning">The actual Card is retrospective evidence, not an optimal-label assertion. Bounded Search is determinization-based. Information-set Search is strict without fallback, controls only the acting Player over selected compatible Worlds, and uses fixed effective opponent Policies. Either Search may be unavailable, partial, or time out normally; neither is calibrated probability or a complete optimal imperfect-information policy.</p>
          <button type="submit" class="primary"{
        " disabled" if not options else ""
    }>Analyze selected Decision</button>
        </form>
      </section>
    """


def _historical_analysis_controls(state: dict[str, Any]) -> str:
    materialization = state["historical_materialization"]
    if not materialization["available"]:
        return f"""
          <section class="panel analysis-control historical-analysis-control">
            <p class="eyebrow">Strict Historical evidence</p>
            <h2>Historical Game Analysis unavailable</h2>
            <p class="normal-unavailable">Canonical reason: {_e(_label(materialization["unavailable_reason"]))}.</p>
          </section>
        """
    return f"""
      <section class="panel analysis-control historical-analysis-control">
        <p class="eyebrow">Explicit strict Historical analysis</p>
        <h2>Historical Game Analysis</h2>
        <p>Strict Historical materialization is available for {_e(materialization["game_id"])}.</p>
        <form method="post" action="/api/v1/analysis" class="form-grid analysis-form" data-historical-analysis-form data-native-submit>
          {_hidden(state, "analyze_historical_game")}
          <fieldset class="analysis-modes">
            <legend>Analysis modes, select at least one</legend>
            <label><input type="checkbox" name="decision_snapshots" value="true"> Decision Snapshots</label>
            <label><input type="checkbox" name="immediate_review" value="true" checked> Immediate Review</label>
            <label><input type="checkbox" name="search_review" value="true"> Search Review</label>
            <label><input type="checkbox" name="replay_coaching" value="true"> Replay Coaching</label>
          </fieldset>
          <label>Immediate sample count <input type="number" min="1" max="100000" name="immediate_sample_count" value="100" required></label>
          <label>Immediate random seed <input type="number" name="immediate_random_seed" value="0" required></label>
          <div class="search-settings">
            <label>Search random seed <input type="number" name="search_random_seed" value="0"></label>
            <label>Search budget profile
              <select name="search_budget_profile">
                <option value="historical_review_v1">Historical review</option>
                <option value="interactive_v1">Interactive</option>
              </select>
            </label>
          </div>
          <label class="checkbox-label"><input type="checkbox" name="use_profile_presets" value="true" checked> Use eligible Player Profile Presets</label>
          <p class="analysis-warning">Historical Search Review and Replay Coaching may take substantially longer. Their conclusions are bounded and retrospective, not perfect-play or causal claims.</p>
          <button type="submit" class="primary">Analyze strict Historical Game</button>
        </form>
      </section>
    """


def _workspace(state: dict[str, Any]) -> str:
    match = state["match"]
    source = state["source"]
    view = state["position_view"]
    progress = state["progress"]
    source_link = (
        f'<a href="{_e(source["source_url"])}" target="_blank" '
        f'rel="noopener noreferrer">Open source</a>'
        if source["source_url"]
        else "Manual observation"
    )
    current_trick = " / ".join(view["current_trick_cards"]) or "No current Trick"
    blockers = ", ".join(view["record_play_blockers"]) or "None"
    play_counts = " | ".join(
        f"{item['player_id']}: {item['play_count']}" for item in view["player_play_counts"]
    )
    evidence = view["evidence_summary"]
    evidence_summary = (
        "No observed Game evidence."
        if evidence is None
        else (
            f"Perspective samples: {evidence['perspective_decision_samples_reconstructable']}; "
            f"all-Player samples: {evidence['all_player_decision_samples_reconstructable']}; "
            f"discard review: {evidence['discard_review_reconstructable']}; "
            f"complete initial Deal: {evidence['complete_initial_deal_reconstructable']}."
        )
    )
    participant_line = " | ".join(
        f"{_e(player['table_place'])}: {_e(player['player_label'] or player['player_id'])}"
        for player in state["participants"]
    )
    snapshots = [
        (player["player_id"], player["statistics_snapshot"])
        for player in state["participants"]
        if player["statistics_snapshot"] is not None
    ]
    snapshot_line = (
        "No attached Player Statistics Snapshots."
        if not snapshots
        else "Attached snapshots: "
        + " | ".join(
            f"{player_id}: {snapshot['snapshot_id']} at {snapshot['observed_at']}"
            for player_id, snapshot in snapshots
        )
    )
    selected_position = state["selected_position"]
    previous_link = (
        ""
        if selected_position == 1
        else f'<a href="/position/{selected_position - 1}" data-position-previous>Previous position</a>'
    )
    next_link = (
        ""
        if selected_position == 36
        else f'<a href="/position/{selected_position + 1}" data-position-next>Next position</a>'
    )
    return f"""
    <header class="app-header">
      <div><p class="eyebrow">EuroSkat 36er Standard</p><h1>{_e(match["title"])}</h1></div>
      <div class="header-stats"><span>Revision {state["workspace_revision"]}</span><span>{progress["occupied_slot_count"]}/36 classified</span></div>
    </header>
    <main class="workspace-shell">
      <section class="panel match-summary">
        <p>{_e(match["game_platform"])} | {_e(source["source_title"])} | {source_link}</p>
        <p>{participant_line}</p>
        <p>Perspective: <strong>{_e(state["perspective_player_id"])}</strong></p>
        <p>{_e(snapshot_line)}</p>
        <form method="post" action="/api/v1/reload" class="inline-form">
          <input type="hidden" name="match_position" value="{state["selected_position"]}">
          <button type="submit">Reload Workspace from disk</button>
        </form>
      </section>
      {_metadata_form(state)}
      {_player_statistics(state)}
      {_report_navigation(state)}
      {_selected_report(state)}
      {_materialization_controls(state)}
      <section class="overview"><h2>Match overview</h2>{_overview(state)}</section>
      <section class="position-head panel">
        <p class="eyebrow">Round {view["round_number"]} | Position {view["match_position"]}</p>
        <h2>{_e(view["game_state"].replace("_", " ").title())}</h2>
        <nav class="position-navigation" aria-label="Position navigation">{previous_link} {next_link}</nav>
        <dl>
          <div><dt>Dealer</dt><dd>{_e(view["dealer_player_id"])}</dd></div>
          <div><dt>Forehand</dt><dd>{_e(view["forehand_player_id"])}</dd></div>
          <div><dt>Middlehand</dt><dd>{_e(view["middlehand_player_id"])}</dd></div>
          <div><dt>Rearhand</dt><dd>{_e(view["rearhand_player_id"])}</dd></div>
          <div><dt>Current Trick</dt><dd>{_e(current_trick)}</dd></div>
          <div><dt>Completed Tricks</dt><dd>{view["completed_trick_count"]}</dd></div>
          <div><dt>Total Plays</dt><dd>{view["play_count"]}</dd></div>
          <div><dt>Next Player</dt><dd>{_e(view["next_player_id"] or "None")}</dd></div>
          <div><dt>Slot kind</dt><dd>{_e(view["slot_kind"])}</dd></div>
          <div><dt>Game ID</dt><dd>{_e(view["game_id"] or "None")}</dd></div>
          <div><dt>Declarer</dt><dd>{_e(view["declarer_player_id"] or "Unknown")}</dd></div>
          <div><dt>Record blockers</dt><dd>{_e(blockers)}</dd></div>
        </dl>
        <p><strong>Player Play counts:</strong> {_e(play_counts)}</p>
        <p><strong>Evidence Summary:</strong> {_e(evidence_summary)}</p>
        <p><strong>Workspace Progress:</strong> {_e(progress["status"])}; {progress["empty_slot_count"]} empty, {progress["observed_game_count"]} observed, {progress["passed_deal_count"]} passed.</p>
      </section>
      {_setup_forms(state)}
      {_palette(state) if state["game"] is not None else ""}
      {_play_history(state)}
      {_annotations(state)}
      {_decision_analysis_controls(state)}
      {_historical_analysis_controls(state)}
      <section class="panel danger-zone">
        <h3>Position correction</h3>
        <form method="post" action="/api/v1/operation" data-confirm="Replace all retained Game evidence with a Passed Deal?">
          {_hidden(state, "mark_passed_deal")}
          <input type="hidden" name="confirm_replace" value="true">
          <input type="hidden" name="game_timecode_start" value="">
          <input type="hidden" name="game_timecode_end" value="">
          <button type="submit">Replace with Passed Deal</button>
        </form>
        <form method="post" action="/api/v1/operation" data-confirm="Clear all retained evidence for this position?">
          {_hidden(state, "clear_position")}
          <label><input type="checkbox" name="confirm_clear" value="true" required> Confirm clear</label>
          <button type="submit">Clear position</button>
        </form>
      </section>
    </main>
    """


def render_match_capture_web_page_v1(
    state: dict[str, Any],
    *,
    notice: str | None = None,
    notice_kind: str = "info",
) -> str:
    body = _workspace(state) if state["workspace_exists"] else _creation_form(state)
    notice_html = (
        ""
        if notice is None
        else f'<div class="notice notice-{_e(notice_kind)}" role="status">{_e(notice)}</div>'
    )
    return Template(load_match_capture_web_template_v1()).substitute(
        PAGE_TITLE=_e(state["workspace_filename"]),
        NOTICE=notice_html,
        BODY=body,
    )
