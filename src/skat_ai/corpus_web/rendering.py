# ruff: noqa: E501 - Server-rendered HTML stays legible as complete elements.

from __future__ import annotations

from html import escape
from importlib.resources import files
from typing import Any


def _e(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _facts(values: tuple[tuple[str, object], ...]) -> str:
    return "".join(
        f'<div class="fact"><dt>{_e(label)}</dt><dd>{_e(value)}</dd></div>'
        for label, value in values
    )


def _initialization() -> str:
    return """
      <section class="panel initialization">
        <p class="eyebrow">Uninitialized explicit root</p>
        <h2>Initialize the Learning Corpus</h2>
        <p>The server will use only the root supplied on the command line.</p>
        <form method="post" action="/api/v1/operations" class="form-grid">
          <input type="hidden" name="operation" value="initialize_corpus">
          <label>Corpus ID <input name="corpus_id" required autocomplete="off"></label>
          <button type="submit">Initialize Corpus</button>
        </form>
      </section>
    """


def _corpus_summary(state: dict[str, Any]) -> str:
    corpus = state["corpus"]
    return f"""
      <section class="panel corpus-summary">
        <div class="section-heading">
          <p class="eyebrow">Explicit current selections</p>
          <h2>{_e(corpus["corpus_id"])}</h2>
        </div>
        <dl class="facts">{
        _facts(
            (
                ("Catalog revision", corpus["catalog_revision"]),
                ("Logical Matches", corpus["logical_match_count"]),
                ("Retained Snapshots", corpus["retained_match_snapshot_count"]),
                ("Current Snapshots", corpus["current_match_snapshot_count"]),
                ("Orphans", corpus["orphan_match_snapshot_count"]),
            )
        )
    }</dl>
        <form method="post" action="/api/v1/operations" class="inline-form">
          <input type="hidden" name="operation" value="reload_corpus">
          <button type="submit">Reload Corpus</button>
        </form>
      </section>
    """


def _workspace_import(state: dict[str, Any]) -> str:
    revision = state["corpus"]["catalog_revision"]
    return f"""
      <section class="panel">
        <p class="eyebrow">Immutable source publication</p>
        <h2>Import Match Workspace</h2>
        <form method="post" action="/api/v1/operations" enctype="multipart/form-data" class="form-grid">
          <input type="hidden" name="operation" value="import_match_workspace">
          <input type="hidden" name="expected_catalog_revision" value="{revision}">
          <label>Workspace JSON <input type="file" name="workspace_file" accept="application/json,.json" required></label>
          <label>Selection
            <select name="selection_mode">
              <option value="select_imported">Select imported Snapshot</option>
              <option value="keep_current">Keep explicit Current Snapshot</option>
            </select>
          </label>
          <label>Same-revision conflict
            <select name="same_revision_resolution">
              <option value="reject">Require explicit resolution</option>
              <option value="retain">Retain both Snapshots</option>
            </select>
          </label>
          <button type="submit">Import Workspace</button>
        </form>
      </section>
    """


def _matches(state: dict[str, Any]) -> str:
    revision = state["corpus"]["catalog_revision"]
    rows = []
    for match in state["matches"]:
        snapshots = "".join(
            f"""
            <li class="snapshot{" current" if snapshot["current"] else ""}">
              <div><strong>Revision {snapshot["workspace_revision"]}</strong>
              <small>{_e(snapshot["match_snapshot_id"][:12])}</small></div>
              <span>{snapshot["observed_game_count"]} games, {
                snapshot["decision_count"]
            } decisions, {snapshot["commentary_count"]} commentaries, {
                snapshot["response_count"]
            } responses</span>
              {
                ""
                if snapshot["current"]
                else f'''<form method="post" action="/api/v1/operations" class="inline-form">
                <input type="hidden" name="operation" value="select_current_snapshot">
                <input type="hidden" name="expected_catalog_revision" value="{revision}">
                <input type="hidden" name="match_id" value="{_e(match["match_id"])}">
                <input type="hidden" name="match_snapshot_id" value="{_e(snapshot["match_snapshot_id"])}">
                <button type="submit">Select Current</button>
              </form>'''
            }
            </li>
            """
            for snapshot in match["snapshots"]
        )
        rows.append(
            f"""
            <article class="match-card">
              <h3>{_e(match["match_id"])}</h3>
              <p>Current revision: <strong>{_e(match["current_workspace_revision"])}</strong></p>
              <ul class="snapshot-list">{snapshots}</ul>
            </article>
            """
        )
    return f"""
      <section class="panel wide">
        <p class="eyebrow">Retained immutable revisions</p>
        <h2>Match Snapshots</h2>
        <div class="match-grid">{"".join(rows) or "<p>No Match Snapshots retained.</p>"}</div>
      </section>
    """


def _strategy_sources(state: dict[str, Any]) -> str:
    current_options = "".join(
        f'<option value="{_e(item["match_snapshot_id"])}">{_e(item["match_id"])} - {_e(item["match_snapshot_id"][:12])}</option>'
        for item in state["current_match_snapshots"]
    )
    rows = "".join(
        f"""
        <tr>
          <td>{_e(source["source_report_id"][:12])}</td>
          <td>{_e(source["match_id"])}</td>
          <td>{source["match_position"]} / {source["decision_index"]}</td>
          <td>{_e(source["recommendation_method"])}</td>
          <td><span class="status {source["binding_status"]}">{_e(source["binding_status"])}</span></td>
          <td><form method="post" action="/api/v1/operations" class="inline-form">
            <input type="hidden" name="operation" value="remove_strategy_teacher_report">
            <input type="hidden" name="source_binding_id" value="{_e(source["source_binding_id"])}">
            <button type="submit">Remove</button>
          </form></td>
        </tr>
        """
        for source in state["strategy_sources"]
    )
    return f"""
      <section class="panel wide">
        <p class="eyebrow">Session-local exact Reports</p>
        <h2>Strategy Teacher Sources</h2>
        <p>Non-current sources remain visible and block preparation until removed or replaced.</p>
        <form method="post" action="/api/v1/operations" enctype="multipart/form-data" class="form-grid">
          <input type="hidden" name="operation" value="import_strategy_teacher_report">
          <label>Report source JSON <input type="file" name="report_source_file" accept="application/json,.json" required></label>
          <label>Current Match Snapshot <select name="match_snapshot_id" required>{current_options}</select></label>
          <button type="submit"{" disabled" if not current_options else ""}>Add Report Source</button>
        </form>
        <div class="table-wrap"><table><thead><tr><th>Report</th><th>Match</th><th>Position / Decision</th><th>Method</th><th>Binding</th><th>Action</th></tr></thead>
        <tbody>{rows or '<tr><td colspan="6">No Strategy Teacher sources uploaded.</td></tr>'}</tbody></table></div>
        <form method="post" action="/api/v1/operations" class="inline-form">
          <input type="hidden" name="operation" value="clear_strategy_teacher_reports">
          <button type="submit"{" disabled" if not rows else ""}>Clear Sources</button>
        </form>
      </section>
    """


def _player_summary(prepared: dict[str, Any]) -> str:
    rows = "".join(
        f"<tr><td>{_e(player['player_id'])}</td><td>{_e(', '.join(player['observed_labels']) or 'None')}</td><td>{player['match_count']}</td><td>{player['alias_conflict_count']}</td><td>{player['statistics_observation_count']}</td></tr>"
        for player in prepared["players"]
    )
    return f"""
      <h3>Player Catalog Summary</h3>
      <p>{prepared["player_count"]} Players; {prepared["platform_alias_conflict_count"]} platform-alias conflicts.</p>
      <div class="table-wrap"><table><thead><tr><th>Player ID</th><th>Observed labels</th><th>Matches</th><th>Alias conflicts</th><th>Statistics</th></tr></thead>
      <tbody>{rows or '<tr><td colspan="5">No Current Match Players.</td></tr>'}</tbody></table></div>
    """


def _preparation(state: dict[str, Any]) -> str:
    corpus_id = state["corpus"]["corpus_id"]
    prepared = state["prepared"]
    summary = ""
    downloads = ""
    if prepared is not None:
        summary = f"""
          <dl class="facts">{
            _facts(
                (
                    ("Dataset status", prepared["dataset_status"]),
                    ("Observed Decisions", prepared["observed_decision_count"]),
                    ("Records", prepared["record_count"]),
                    ("Skipped", prepared["skipped_decision_count"]),
                    ("Teachers", prepared["strategy_teacher_evidence_count"]),
                    ("Commentaries", prepared["commentary_evidence_count"]),
                    ("Responses", prepared["response_evidence_count"]),
                    ("Known-player readiness", prepared["known_player"]["status"]),
                    ("Known-player reason", prepared["known_player"]["unavailable_reason"]),
                    ("Unseen-player readiness", prepared["unseen_player"]["status"]),
                    ("Unseen-player reason", prepared["unseen_player"]["unavailable_reason"]),
                    ("Cross-game Matches", prepared["cross_game_match_count"]),
                    ("Cross-game Players", prepared["cross_game_player_count"]),
                    ("Tactical status", prepared["tactical_collection_status"]),
                    ("Tactical Evidence", prepared["tactical_evidence_count"]),
                    ("Tactical skipped", prepared["tactical_skipped_decision_count"]),
                    ("Tactical motif occurrences", prepared["tactical_motif_occurrence_count"]),
                    ("Tactical Players", prepared["tactical_cross_game_player_count"]),
                    ("Tactical recurrences", prepared["tactical_cross_game_recurrence_count"]),
                )
            )
        }</dl>
          {_player_summary(prepared)}
        """
        download_routes = (
            ("Player Catalog", "player-catalog.json"),
            ("Human Evidence", "human-evidence.json"),
            ("Strategy Teacher Evidence", "strategy-teacher-evidence.json"),
            ("Learning Dataset v2", "learning-dataset-v2.json"),
            ("Known-player Partitions", "known-player-partitions.json"),
            ("Unseen-player Partitions", "unseen-player-partitions.json"),
            ("Cross-game Summary", "cross-game-summary.json"),
            ("Tactical Motif Evidence", "tactical-motif-evidence.json"),
            (
                "Tactical Motif Cross-game Summary",
                "tactical-motif-cross-game-summary.json",
            ),
        )
        downloads = (
            '<div class="download-grid">'
            + "".join(
                f'<a class="download-link" href="/downloads/{route}">{_e(label)}</a>'
                for label, route in download_routes
            )
            + "</div>"
        )
    return f"""
      <section class="panel wide preparation">
        <p class="eyebrow">Explicit process-local build</p>
        <h2>Learning Artifacts</h2>
        <form method="post" action="/api/v1/operations" class="form-grid six">
          <input type="hidden" name="operation" value="prepare_learning_artifacts">
          <label>Dataset ID <input name="dataset_id" value="{_e(corpus_id)}-learning-dataset-v2" required></label>
          <label>Known-player seed <input name="known_player_seed" type="number" value="0" required></label>
          <label>Unseen-player seed <input name="unseen_player_seed" type="number" value="0" required></label>
          <label>Train weight <input name="train_weight" type="number" min="1" value="70" required></label>
          <label>Validation weight <input name="validation_weight" type="number" min="1" value="15" required></label>
          <label>Test weight <input name="test_weight" type="number" min="1" value="15" required></label>
          <button type="submit">Prepare Artifacts</button>
        </form>
        {summary or "<p>No prepared artifacts in this process.</p>"}
        {downloads}
      </section>
    """


def render_learning_corpus_web_page_v1(
    state: dict[str, Any],
    *,
    notice: str | None = None,
    notice_kind: str = "info",
) -> str:
    if not isinstance(state, dict):
        raise ValueError("state must be one browser projection.")
    body = (
        _initialization()
        if not state["initialized"]
        else "".join(
            (
                _corpus_summary(state),
                _workspace_import(state),
                _matches(state),
                _strategy_sources(state),
                _preparation(state),
            )
        )
    )
    notice_html = (
        ""
        if notice is None
        else f'<div class="notice {_e(notice_kind)}" role="status">{_e(notice)}</div>'
    )
    template = (
        files("skat_ai.corpus_web").joinpath("templates/page.html").read_text(encoding="utf-8")
    )
    return template.replace("{{NOTICE}}", notice_html).replace("{{CONTENT}}", body)
