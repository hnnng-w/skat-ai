from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from skatmind.capture_web.contracts import (
    MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
    MATCH_CAPTURE_WEB_MUTATION_OPERATIONS,
)
from skatmind.corpus_web.contracts import LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES
from skatmind.session_commands import SESSION_COMMAND_KINDS

from .form_parsing import FormValuesV1, FormValueV1
from .frontend_profile_operations import FRONTEND_PROFILE_ACTION_ROUTES
from .guided_contracts import GUIDED_ACTION_ROUTE_PATHS
from .json_transfer import FRONTEND_JSON_MAX_FILE_BYTES
from .managed_item_contracts import MANAGED_ITEM_MAX_IMPORT_BYTES
from .position_form import (
    POSITION_ANALYSIS_METHODS_V1,
    POSITION_FORM_CARD_FIELDS_V1,
    POSITION_FORM_FIELDS_V1,
    POSITION_MULTI_STEP_POLICIES_V1,
    POSITION_OPPONENT_POLICIES_V1,
    POSITION_POLICY_PRESETS_V1,
)

_DEFAULT_BODY_LIMIT = FRONTEND_JSON_MAX_FILE_BYTES + 4_096
_MANAGED_IMPORT_BODY_LIMIT = MANAGED_ITEM_MAX_IMPORT_BYTES + 4_096
_CARD_FIELDS = {
    "actual_card_played",
    "card",
    "cards",
    "current_trick",
    "discarded_cards",
    "forehand_hand",
    "hand",
    "middlehand_hand",
    "public_declarer_cards",
    "rearhand_hand",
    "skat",
}
_CHECKBOX_FIELDS = {
    "compare_policies",
    "comparison_only",
    "decision_snapshots",
    "hand_game",
    "historical_tactical_motif_review",
    "immediate_review",
    "include_provenance",
    "information_set_replay_coaching",
    "information_set_search_review",
    "ouvert",
    "replay_coaching",
    "schneider_announced",
    "search_review",
    "strict_context",
    "schwarz_announced",
    "tactical",
    "tactical_motif_review",
    "use_profile_presets",
}
_DESTRUCTIVE_FIELDS = {
    "confirm_clear",
    "confirm_clear_snapshot",
    "confirm_replace",
    "confirm_reset",
}
_REPEATED_FIELDS = {
    *POSITION_FORM_CARD_FIELDS_V1,
    "cards",
    "discarded_cards",
    "forehand_hand",
    "middlehand_hand",
    "rearhand_hand",
}
_FILE_FIELDS = {
    "request_file",
    "session_file",
    "workspace_file",
    "report_source_file",
}
_SELECT_CHOICES = {
    "analysis_mode": ("live_decision", "post_game_review"),
    "capture_mode": ("live", "retrospective"),
    "card_evidence_mode": ("unknown", "known_empty", "exact"),
    "game_type": ("clubs", "spades", "hearts", "diamonds", "grand", "null", ""),
    "language": ("de", "en"),
    "selection_mode": ("select_imported", "keep_current"),
    "same_revision_resolution": ("reject", "retain"),
    "source_kind": ("youtube_video", "other_video", "manual_observation"),
}
_BOOLEAN_CHOICES = ("false", "true")
_LABEL_KEYS = {
    "capture_mode": "validation.field.capture_mode",
    "card": "validation.field.card",
    "cards": "validation.field.cards",
    "corpus_id": "validation.field.corpus_id",
    "game_type": "validation.field.game_type",
    "language": "validation.field.language",
    "match_id": "validation.field.match_id",
    "request_file": "validation.field.file",
    "session_id": "validation.field.session_id",
    "session_file": "validation.field.file",
    "source_title": "validation.field.source_title",
    "source_url": "validation.field.source_url",
    "workspace_file": "validation.field.file",
    "report_source_file": "validation.field.file",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class FrontendFormFieldV1:
    field_key: str
    cardinality: str
    control_type: str
    reflection_length: int
    field_label_key: str
    allowed_values: tuple[str, ...] = ()
    clear_after_rejection: bool = False

    def __post_init__(self) -> None:
        if type(self.field_key) is not str or not self.field_key:
            raise ValueError("field_key must be non-empty text.")
        if self.cardinality not in {"single", "repeated"}:
            raise ValueError("cardinality must be single or repeated.")
        if self.control_type not in {
            "text",
            "textarea",
            "select",
            "radio",
            "checkbox",
            "card",
            "file",
        }:
            raise ValueError("control_type must be canonical.")
        if type(self.reflection_length) is not int or not 0 <= self.reflection_length <= 4096:
            raise ValueError("reflection_length must be a bounded integer.")
        if not self.field_label_key.startswith("validation.field."):
            raise ValueError("field_label_key must identify a validation field label.")
        if self.control_type == "file" and self.reflection_length != 0:
            raise ValueError("File controls must never retain reflected values.")


@dataclass(frozen=True, slots=True, kw_only=True)
class FrontendFormDefinitionV1:
    form_key: str
    action_route: str
    media_type: str
    body_limit: int
    safe_fields: tuple[FrontendFormFieldV1, ...]
    originating_page: str
    active_context_requirement: str | None
    wizard_step: int | None
    known_error_mappings: tuple[str, ...]
    file_reselection_behavior: str
    success_redirect: str
    contextual_400_page: str
    contextual_409_page: str
    discriminator_field: str | None = None
    discriminator_value: str | None = None
    value_free: bool = False

    def __post_init__(self) -> None:
        fields = tuple(self.safe_fields)
        object.__setattr__(self, "safe_fields", fields)
        names = tuple(field.field_key for field in fields)
        if len(names) != len(set(names)):
            raise ValueError("safe_fields must not repeat field keys.")
        if self.media_type not in {
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        }:
            raise ValueError("media_type must be one registered browser form type.")
        if type(self.body_limit) is not int or self.body_limit < 1:
            raise ValueError("body_limit must be positive.")
        if self.file_reselection_behavior not in {"not_applicable", "required"}:
            raise ValueError("file_reselection_behavior must be canonical.")
        if (self.discriminator_field is None) != (self.discriminator_value is None):
            raise ValueError("Form discriminators must be supplied together.")
        if self.value_free and fields:
            raise ValueError("A value-free action cannot retain safe fields.")


def _field(
    name: str,
    *,
    control_override: str | None = None,
    cardinality_override: str | None = None,
    choices_override: tuple[str, ...] | None = None,
) -> FrontendFormFieldV1:
    if control_override is not None:
        control = control_override
    elif name in _FILE_FIELDS:
        control = "file"
    elif name in _CARD_FIELDS or (name.startswith("completed_trick_") and "_card_" in name):
        control = "card"
    elif name in _CHECKBOX_FIELDS or name in _DESTRUCTIVE_FIELDS:
        control = "checkbox"
    elif name in _SELECT_CHOICES or name.endswith("_mode") or name.endswith("_policy"):
        control = "select"
    elif name == "text":
        control = "textarea"
    else:
        control = "text"
    return FrontendFormFieldV1(
        field_key=name,
        cardinality=(
            cardinality_override or ("repeated" if name in _REPEATED_FIELDS else "single")
        ),
        control_type=control,
        reflection_length=0 if control == "file" else 4 if control == "card" else 2048,
        field_label_key=_LABEL_KEYS.get(name, "validation.field.submitted_value"),
        allowed_values=(
            choices_override if choices_override is not None else _SELECT_CHOICES.get(name, ())
        ),
        clear_after_rejection=name in _DESTRUCTIVE_FIELDS,
    )


def _definition(
    form_key: str,
    route: str,
    fields: tuple[str, ...] = (),
    *,
    page: str,
    active: str | None = None,
    wizard_step: int | None = None,
    media_type: str = "application/x-www-form-urlencoded",
    body_limit: int = _DEFAULT_BODY_LIMIT,
    file_reselection: bool = False,
    success: str,
    discriminator: tuple[str, str] | None = None,
    value_free: bool = False,
    control_overrides: Mapping[str, str] | None = None,
    cardinality_overrides: Mapping[str, str] | None = None,
    choice_overrides: Mapping[str, tuple[str, ...]] | None = None,
) -> FrontendFormDefinitionV1:
    controls = control_overrides or {}
    cardinalities = cardinality_overrides or {}
    choices = choice_overrides or {}
    return FrontendFormDefinitionV1(
        form_key=form_key,
        action_route=route,
        media_type=media_type,
        body_limit=body_limit,
        safe_fields=tuple(
            _field(
                name,
                control_override=controls.get(name),
                cardinality_override=cardinalities.get(name),
                choices_override=choices.get(name),
            )
            for name in fields
        ),
        originating_page=page,
        active_context_requirement=active,
        wizard_step=wizard_step,
        known_error_mappings=(
            "required",
            "choice",
            "integer",
            "bound",
            "duplicate",
            "card",
            "date_time",
            "source",
            "upload",
            "stale",
            "persistence",
            "unsupported",
        ),
        file_reselection_behavior="required" if file_reselection else "not_applicable",
        success_redirect=success,
        contextual_400_page=page,
        contextual_409_page=page,
        discriminator_field=None if discriminator is None else discriminator[0],
        discriminator_value=None if discriminator is None else discriminator[1],
        value_free=value_free,
    )


_REVIEW_OPTIONS = (
    "decision_snapshots",
    "immediate_review",
    "search_review",
    "information_set_search_review",
    "replay_coaching",
    "information_set_replay_coaching",
    "tactical",
    "include_provenance",
    "search_seed",
    "immediate_sample_count",
    "immediate_base_random_seed",
)
_SESSION_CREATE_FIELDS = (
    "session_id",
    "capture_mode",
    "local_player_id",
    "player_1_id",
    "player_1_label",
    "player_2_id",
    "player_2_label",
    "player_3_id",
    "player_3_label",
)
_SESSION_COMMAND_FIELDS = {
    "set_game_metadata": ("target_revision", "game_id", "played_at"),
    "record_dealt_card": ("target_revision", "destination", "player_id", "card"),
    "set_declarer": ("target_revision", "player_id"),
    "set_declaration": (
        "target_revision",
        "game_type",
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
        "matadors",
        "bid_value",
    ),
    "record_discard": ("target_revision", "card"),
    "record_play": ("target_revision", "player_id", "card"),
    "set_public_hand": ("target_revision", "player_id", "cards"),
    "set_game_event": (
        "target_revision",
        "event_kind",
        "after_play_count",
        "player_id",
        "cards",
        "exposure_form",
        "shown_to_defender_player_id",
        "claimed_play_level",
        "defender_1_player_id",
        "defender_1_response",
        "defender_1_form",
        "defender_2_player_id",
        "defender_2_response",
        "defender_2_form",
    ),
    "set_game_end": (
        "target_revision",
        "game_end_reason",
        "player_id",
        "cards",
        "remaining_card_count",
        "consent_status",
        "consenting_player_ids",
        "concession_form",
        "statement_classification",
        "exposure_form",
        "shown_to_defender_player_id",
        "claimed_play_level",
        "defender_1_player_id",
        "defender_1_response",
        "defender_1_form",
        "defender_2_player_id",
        "defender_2_response",
        "defender_2_form",
    ),
    "promote_to_retrospective": ("target_revision",),
}
_MATCH_CREATE_FIELDS = (
    "match_id",
    "title",
    "game_platform",
    "external_match_id",
    "played_at",
    "source_kind",
    "source_url",
    "source_title",
    "source_channel_name",
    "match_timecode_start",
    "match_timecode_end",
    "player_1_id",
    "player_1_label",
    "player_1_platform_id",
    "player_2_id",
    "player_2_label",
    "player_2_platform_id",
    "player_3_id",
    "player_3_label",
    "player_3_platform_id",
    "perspective_player_id",
)
_MATCH_METADATA_FIELDS = tuple(
    name
    for name in _MATCH_CREATE_FIELDS
    if name
    not in {"match_id", "perspective_player_id", "player_1_id", "player_2_id", "player_3_id"}
)
_STATISTIC_FIELDS = (
    "snapshot_id",
    "observed_at",
    "source_type",
    "source_name",
    "source_player_id",
    "notes",
    "games_played",
    "solo_games_played_percent",
    "solo_games_won_percent",
    "solo_hand_percent",
    "suit_games_percent",
    "grand_games_percent",
    "null_games_percent",
    "defender_games_played_percent",
    "defender_games_won_percent",
    "solo_games_played",
    "solo_games_won",
    "solo_hand_games",
    "suit_games",
    "grand_games",
    "null_games",
    "defender_games_played",
    "defender_games_won",
)
_MATCH_MUTATION_FIELDS = {
    "update_match_metadata": _MATCH_METADATA_FIELDS,
    "start_game": ("game_id", "game_timecode_start", "game_timecode_end"),
    "set_game_timecode": ("game_timecode_start", "game_timecode_end"),
    "set_perspective_hand": ("card_evidence_mode", "cards"),
    "set_declaration": (
        "declarer_player_id",
        "game_type",
        "hand_game",
        "ouvert",
        "schneider_announced",
        "schwarz_announced",
        "matadors",
        "bid_value",
    ),
    "set_original_skat": ("card_evidence_mode", "cards"),
    "set_discarded_cards": ("card_evidence_mode", "cards"),
    "append_plays": ("cards", "decision_timecode"),
    "truncate_plays": ("target_play_count",),
    "set_commentary": (
        "decision_index",
        "commentator_player_id",
        "commentator_name",
        "commentary_timecode",
        "text",
    ),
    "remove_commentary": (),
    "set_response_link": ("response_decision_index",),
    "remove_response_link": (),
    "mark_passed_deal": ("game_timecode_start", "game_timecode_end"),
    "clear_position": ("confirm_clear",),
    "set_player_statistics_snapshot": _STATISTIC_FIELDS,
    "clear_player_statistics_snapshot": ("confirm_clear_snapshot",),
}
_MATCH_ANALYSIS_FIELDS = {
    "prepare_materialization": (),
    "analyze_decision": (
        "decision_index",
        "recommendation_method",
        "immediate_sample_count",
        "immediate_random_seed",
        "search_random_seed",
        "search_budget_profile",
        "use_profile_presets",
    ),
    "analyze_historical_game": (
        "decision_snapshots",
        "tactical_motif_review",
        "immediate_review",
        "search_review",
        "information_set_search_review",
        "replay_coaching",
        "information_set_replay_coaching",
        "immediate_sample_count",
        "immediate_random_seed",
        "search_random_seed",
        "search_budget_profile",
        "use_profile_presets",
    ),
}

_ANALYZE_VISIBLE_FIELDS = tuple(
    field
    for field in POSITION_FORM_FIELDS_V1
    if field not in {"completed_tricks", "left_hand_size", "right_hand_size"}
)
_POSITION_CHOICE_OVERRIDES = {
    "analysis_mode": ("live_decision", "post_game_review"),
    "game_type": ("clubs", "spades", "hearts", "diamonds", "grand", "null"),
    "player_role": ("declarer", "defender"),
    "player_position": ("forehand", "middlehand", "rearhand"),
    "declarer_player": ("me", "left", "right"),
    "trick_leader": ("me", "left", "right"),
    "analysis_method": (*(method.form_value for method in POSITION_ANALYSIS_METHODS_V1),),
    "opponent_strategy": ("", "basic", "random"),
    "opponent_policy_preset": ("", *POSITION_POLICY_PRESETS_V1),
    "opponent_lead_policy": ("", *POSITION_OPPONENT_POLICIES_V1),
    "opponent_response_policy": ("", *POSITION_OPPONENT_POLICIES_V1),
    "left_opponent_lead_policy": ("", *POSITION_OPPONENT_POLICIES_V1),
    "left_opponent_response_policy": ("", *POSITION_OPPONENT_POLICIES_V1),
    "right_opponent_lead_policy": ("", *POSITION_OPPONENT_POLICIES_V1),
    "right_opponent_response_policy": ("", *POSITION_OPPONENT_POLICIES_V1),
    "card_selection_policy": ("", *POSITION_MULTI_STEP_POLICIES_V1),
}
for _trick_number in range(1, 10):
    _POSITION_CHOICE_OVERRIDES[f"completed_trick_{_trick_number}_leader"] = (
        "",
        "me",
        "left",
        "right",
    )


_FORMS: list[FrontendFormDefinitionV1] = [
    _definition(
        "analyze.run_guided",
        "/actions/analyze/run-guided",
        _ANALYZE_VISIBLE_FIELDS,
        page="/analyze",
        active="analyze",
        success="/analyze",
        control_overrides={
            "analysis_mode": "radio",
            **{f"completed_trick_{trick_number}_leader": "select" for trick_number in range(1, 10)},
            **{
                name: "select"
                for name in (
                    "game_type",
                    "player_role",
                    "player_position",
                    "declarer_player",
                    "trick_leader",
                    "analysis_method",
                    "opponent_strategy",
                    "opponent_policy_preset",
                    "opponent_lead_policy",
                    "opponent_response_policy",
                    "left_opponent_lead_policy",
                    "left_opponent_response_policy",
                    "right_opponent_lead_policy",
                    "right_opponent_response_policy",
                    "card_selection_policy",
                )
            },
        },
        choice_overrides=_POSITION_CHOICE_OVERRIDES,
    ),
    _definition(
        "analyze.import_json",
        "/actions/analyze/import-json",
        ("request_file",),
        page="/analyze",
        active="analyze",
        media_type="multipart/form-data",
        file_reselection=True,
        success="/analyze",
    ),
    _definition(
        "analyze.run_imported",
        "/actions/analyze/run-imported",
        page="/analyze",
        active="analyze",
        success="/analyze",
        value_free=True,
    ),
    _definition(
        "analyze.reset",
        "/actions/analyze/reset",
        ("confirm_reset",),
        page="/analyze",
        active="analyze",
        success="/analyze",
    ),
    _definition(
        "review.start",
        "/actions/review/start",
        page="/review",
        active="review",
        wizard_step=1,
        success="/review",
        value_free=True,
    ),
    _definition(
        "review.players",
        "/actions/review/update-players",
        ("forehand_label", "middlehand_label", "rearhand_label"),
        page="/review",
        active="review",
        wizard_step=1,
        success="/review",
    ),
    _definition(
        "review.deal",
        "/actions/review/update-deal",
        ("forehand_hand", "middlehand_hand", "rearhand_hand", "skat"),
        page="/review",
        active="review",
        wizard_step=2,
        success="/review",
    ),
    _definition(
        "review.declaration",
        "/actions/review/update-declaration",
        (
            "declarer_player_id",
            "game_type",
            "bid_value",
            "hand_game",
            "ouvert",
            "schneider_announced",
            "schwarz_announced",
        ),
        page="/review",
        active="review",
        wizard_step=3,
        success="/review",
        control_overrides={
            "declarer_player_id": "select",
            "game_type": "select",
        },
        choice_overrides={"game_type": ("clubs", "spades", "hearts", "diamonds", "grand", "null")},
    ),
    _definition(
        "review.discards",
        "/actions/review/update-discards",
        ("discarded_cards",),
        page="/review",
        active="review",
        wizard_step=4,
        success="/review",
    ),
    _definition(
        "review.play",
        "/actions/review/append-play",
        ("card",),
        page="/review",
        active="review",
        wizard_step=5,
        success="/review",
    ),
    _definition(
        "review.undo_play",
        "/actions/review/undo-play",
        page="/review",
        active="review",
        wizard_step=5,
        success="/review",
        value_free=True,
    ),
    _definition(
        "review.options",
        "/actions/review/update-options",
        _REVIEW_OPTIONS,
        page="/review",
        active="review",
        wizard_step=6,
        success="/review",
    ),
    _definition(
        "review.back",
        "/actions/review/back",
        page="/review",
        active="review",
        success="/review",
        value_free=True,
    ),
    _definition(
        "review.run_guided",
        "/actions/review/run-guided",
        page="/review",
        active="review",
        wizard_step=7,
        success="/review",
        value_free=True,
    ),
    _definition(
        "review.import_json",
        "/actions/review/import-json",
        ("request_file",),
        page="/review",
        active="review",
        media_type="multipart/form-data",
        file_reselection=True,
        success="/review",
    ),
    _definition(
        "review.run_imported",
        "/actions/review/run-imported",
        page="/review",
        active="review",
        success="/review",
        value_free=True,
    ),
    _definition(
        "review.reset",
        "/actions/review/reset",
        ("confirm_reset",),
        page="/review",
        active="review",
        success="/review",
    ),
    _definition(
        "profile.language",
        "/actions/profile/language",
        ("language",),
        page="/",
        active="profile",
        success="contextual",
    ),
    _definition(
        "profile.reset",
        "/actions/profile/reset",
        ("confirm_reset",),
        page="/about",
        active="profile",
        success="contextual",
    ),
    _definition(
        "session.create",
        "/sessions/create",
        _SESSION_CREATE_FIELDS,
        page="/sessions",
        active="sessions",
        success="/sessions/current",
    ),
    _definition(
        "session.import",
        "/sessions/import",
        ("session_file",),
        page="/sessions",
        active="sessions",
        media_type="multipart/form-data",
        body_limit=_MANAGED_IMPORT_BODY_LIMIT,
        file_reselection=True,
        success="/sessions/current",
    ),
    _definition(
        "session.open",
        "/sessions/open",
        page="/sessions",
        active="sessions",
        success="/sessions/current",
        value_free=True,
    ),
    _definition(
        "session.reload",
        "/sessions/reload",
        page="/sessions/current",
        active="sessions",
        success="/sessions/current",
        value_free=True,
    ),
    _definition(
        "session.undo",
        "/sessions/undo",
        ("target_revision",),
        page="/sessions/current",
        active="sessions",
        success="/sessions/current",
    ),
    _definition(
        "session.analyze",
        "/sessions/analyze",
        (
            "sample_count",
            "random_seed",
            "opponent_strategy",
            "recommendation_method",
            "search_budget_profile",
        ),
        page="/sessions/current",
        active="sessions",
        success="/sessions/current",
        control_overrides={
            "opponent_strategy": "select",
            "recommendation_method": "select",
            "search_budget_profile": "select",
        },
        choice_overrides={
            "opponent_strategy": ("basic", "random"),
            "recommendation_method": (
                "",
                "immediate_expected_value",
                "bounded_search",
                "auto",
            ),
            "search_budget_profile": ("interactive_v1", "historical_review_v1"),
        },
    ),
    _definition(
        "session.review",
        "/sessions/review",
        (
            "decision_snapshots",
            "immediate_review",
            "search_review",
            "information_set_search_review",
            "replay_coaching",
            "information_set_replay_coaching",
            "historical_tactical_motif_review",
            "sample_count",
            "random_seed",
            "search_seed",
            "search_budget_profile",
        ),
        page="/sessions/current",
        active="sessions",
        success="/sessions/current",
        choice_overrides={
            **{
                name: _BOOLEAN_CHOICES
                for name in (
                    "decision_snapshots",
                    "immediate_review",
                    "search_review",
                    "information_set_search_review",
                    "replay_coaching",
                    "information_set_replay_coaching",
                    "historical_tactical_motif_review",
                )
            },
            "search_budget_profile": ("historical_review_v1", "interactive_v1"),
        },
        control_overrides={
            **{
                name: "select"
                for name in (
                    "decision_snapshots",
                    "immediate_review",
                    "search_review",
                    "information_set_search_review",
                    "replay_coaching",
                    "information_set_replay_coaching",
                    "historical_tactical_motif_review",
                )
            },
            "search_budget_profile": "select",
        },
    ),
    _definition(
        "match.import",
        "/matches/import",
        ("workspace_file",),
        page="/matches",
        active="matches",
        media_type="multipart/form-data",
        body_limit=_MANAGED_IMPORT_BODY_LIMIT,
        file_reselection=True,
        success="/matches/current",
    ),
    _definition(
        "match.open",
        "/matches/open",
        page="/matches",
        active="matches",
        success="/matches/current",
        value_free=True,
    ),
    _definition(
        "match.create",
        "/matches/api/v1/create",
        _MATCH_CREATE_FIELDS,
        page="/matches/new",
        active="matches",
        body_limit=MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
        success="/matches/position/1",
    ),
    _definition(
        "match.reload",
        "/matches/api/v1/reload",
        page="/matches/current",
        active="matches",
        body_limit=MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
        success="contextual",
        value_free=True,
    ),
    _definition(
        "match.transfer_workspace",
        "/matches/transfer-workspace",
        ("selection_mode", "same_revision_resolution"),
        page="/matches/current",
        active="matches",
        success="contextual",
    ),
    _definition(
        "match.transfer_report",
        "/matches/transfer-report",
        ("match_snapshot_id",),
        page="/matches/current",
        active="matches",
        success="contextual",
        control_overrides={"match_snapshot_id": "select"},
    ),
    _definition(
        "learning.create",
        "/learning/create",
        ("corpus_id",),
        page="/learning",
        active="learning",
        success="/learning/current",
    ),
    _definition(
        "learning.open",
        "/learning/open",
        page="/learning",
        active="learning",
        success="/learning/current",
        value_free=True,
    ),
]

for kind in SESSION_COMMAND_KINDS:
    session_controls: dict[str, str] = {}
    session_choices: dict[str, tuple[str, ...]] = {}
    if kind == "set_declaration":
        for field_name in (
            "hand_game",
            "ouvert",
            "schneider_announced",
            "schwarz_announced",
        ):
            session_controls[field_name] = "select"
            session_choices[field_name] = _BOOLEAN_CHOICES
        session_choices["game_type"] = (
            "clubs",
            "spades",
            "hearts",
            "diamonds",
            "grand",
            "null",
        )
    if kind in {"record_dealt_card", "record_discard", "record_play"}:
        session_controls["card"] = "text"
    if kind == "record_dealt_card":
        session_controls["destination"] = "select"
        session_choices["destination"] = ("player_hand", "skat")
    if kind in {
        "record_dealt_card",
        "set_declarer",
        "record_play",
        "set_public_hand",
        "set_game_event",
        "set_game_end",
    }:
        session_controls["player_id"] = "select"
    if kind in {"set_public_hand", "set_game_event", "set_game_end"}:
        session_controls["cards"] = "text"
    if kind == "set_game_event":
        session_controls["event_kind"] = "select"
        session_choices["event_kind"] = (
            "defender_open_play_continuation",
            "declarer_card_exposure_continuation",
        )
    if kind == "set_game_end":
        session_controls["game_end_reason"] = "select"
        session_choices["game_end_reason"] = (
            "normal_completion",
            "declarer_concession",
            "defender_concession",
            "declarer_card_exposure",
            "defender_open_play",
            "open_card_throw",
        )
    if kind in {"set_game_event", "set_game_end"}:
        session_choices.update(
            {
                "exposure_form": ("laid_open", "shown_to_defender"),
                "claimed_play_level": ("simple", "schneider", "schwarz"),
                "defender_1_response": ("accept", "continue"),
                "defender_2_response": ("accept", "continue"),
            }
        )
        session_controls.update(
            {
                field_name: "select"
                for field_name in session_choices
                if field_name != "game_end_reason"
            }
        )
        session_controls.update(
            {
                "shown_to_defender_player_id": "select",
                "defender_1_player_id": "select",
                "defender_2_player_id": "select",
            }
        )
    _FORMS.append(
        _definition(
            f"session.command.{kind}",
            "/sessions/command",
            _SESSION_COMMAND_FIELDS[kind],
            page="/sessions/current",
            active="sessions",
            success="/sessions/current",
            discriminator=("kind", kind),
            control_overrides=session_controls,
            cardinality_overrides=({"cards": "single"} if "cards" in session_controls else None),
            choice_overrides=session_choices,
        )
    )
for operation in MATCH_CAPTURE_WEB_MUTATION_OPERATIONS:
    mutation_controls = (
        {"card_evidence_mode": "radio"}
        if operation in {"set_perspective_hand", "set_original_skat", "set_discarded_cards"}
        else {}
    )
    if operation == "append_plays":
        mutation_controls["cards"] = "text"
    if operation == "set_declaration":
        mutation_controls["declarer_player_id"] = "select"
    if operation == "truncate_plays":
        mutation_controls["target_play_count"] = "select"
    if operation == "set_commentary":
        mutation_controls.update(
            {
                "decision_index": "select",
                "commentator_player_id": "select",
            }
        )
    if operation == "set_response_link":
        mutation_controls["response_decision_index"] = "select"
    evidence_choices = (
        {"card_evidence_mode": ("unknown", "known_empty", "exact")}
        if operation == "set_discarded_cards"
        else {"card_evidence_mode": ("unknown", "exact")}
        if operation in {"set_perspective_hand", "set_original_skat"}
        else {}
    )
    if operation == "set_player_statistics_snapshot":
        mutation_controls["source_type"] = "select"
        evidence_choices["source_type"] = ("manual_entry", "online_platform")
    _FORMS.append(
        _definition(
            f"match.operation.{operation}",
            "/matches/api/v1/operation",
            _MATCH_MUTATION_FIELDS[operation],
            page="/matches/current",
            active="matches",
            body_limit=MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
            success="contextual",
            discriminator=("operation", operation),
            value_free=not _MATCH_MUTATION_FIELDS[operation],
            control_overrides=mutation_controls,
            cardinality_overrides=({"cards": "single"} if operation == "append_plays" else None),
            choice_overrides=evidence_choices,
        )
    )
for operation, fields in _MATCH_ANALYSIS_FIELDS.items():
    analysis_controls: dict[str, str] = {}
    analysis_choices: dict[str, tuple[str, ...]] = {}
    if operation in {"analyze_decision", "analyze_historical_game"}:
        analysis_controls["search_budget_profile"] = "select"
        analysis_choices["search_budget_profile"] = (
            "historical_review_v1",
            "interactive_v1",
        )
    if operation == "analyze_decision":
        analysis_controls["decision_index"] = "select"
        analysis_controls["recommendation_method"] = "select"
        analysis_choices["recommendation_method"] = (
            "immediate_expected_value",
            "bounded_search",
            "auto",
            "information_set_search",
        )
    _FORMS.append(
        _definition(
            f"match.analysis.{operation}",
            "/matches/api/v1/analysis",
            fields,
            page="/matches/current",
            active="matches",
            body_limit=MATCH_CAPTURE_WEB_MAX_REQUEST_BYTES,
            success="contextual",
            discriminator=("operation", operation),
            value_free=not fields,
            control_overrides=analysis_controls,
            choice_overrides=analysis_choices,
        )
    )
for operation, fields, media, file_reselection in (
    ("reload_corpus", (), "application/x-www-form-urlencoded", False),
    (
        "select_current_snapshot",
        (),
        "application/x-www-form-urlencoded",
        False,
    ),
    ("remove_strategy_teacher_report", (), "application/x-www-form-urlencoded", False),
    ("clear_strategy_teacher_reports", (), "application/x-www-form-urlencoded", False),
    (
        "prepare_learning_artifacts",
        (
            "dataset_id",
            "known_player_seed",
            "unseen_player_seed",
            "train_weight",
            "validation_weight",
            "test_weight",
        ),
        "application/x-www-form-urlencoded",
        False,
    ),
    (
        "import_match_workspace",
        ("workspace_file", "selection_mode", "same_revision_resolution"),
        "multipart/form-data",
        True,
    ),
    (
        "import_strategy_teacher_report",
        ("report_source_file", "match_snapshot_id"),
        "multipart/form-data",
        True,
    ),
):
    learning_controls = (
        {"match_snapshot_id": "select"} if operation == "import_strategy_teacher_report" else {}
    )
    _FORMS.append(
        _definition(
            f"learning.operation.{operation}",
            "/learning/api/v1/operations",
            fields,
            page="/learning/current",
            active="learning",
            media_type=media,
            body_limit=LEARNING_CORPUS_WEB_MAX_REQUEST_BYTES,
            file_reselection=file_reselection,
            success="/learning/current",
            discriminator=("operation", operation),
            value_free=not fields,
            control_overrides=learning_controls,
        )
    )

FRONTEND_FORM_REGISTRY = tuple(_FORMS)
UNIFIED_FRONTEND_POST_ROUTES = tuple(
    dict.fromkeys(
        (
            *GUIDED_ACTION_ROUTE_PATHS,
            *FRONTEND_PROFILE_ACTION_ROUTES,
            "/sessions/create",
            "/sessions/import",
            "/sessions/open",
            "/sessions/reload",
            "/sessions/command",
            "/sessions/undo",
            "/sessions/analyze",
            "/sessions/review",
            "/matches/import",
            "/matches/open",
            "/matches/api/v1/create",
            "/matches/api/v1/reload",
            "/matches/api/v1/operation",
            "/matches/api/v1/analysis",
            "/matches/transfer-workspace",
            "/matches/transfer-report",
            "/learning/create",
            "/learning/open",
            "/learning/api/v1/operations",
        )
    )
)


def validate_frontend_form_registry_v1() -> None:
    keys = tuple(form.form_key for form in FRONTEND_FORM_REGISTRY)
    identities = tuple(
        (form.action_route, form.discriminator_field, form.discriminator_value)
        for form in FRONTEND_FORM_REGISTRY
    )
    routes = {form.action_route for form in FRONTEND_FORM_REGISTRY}
    if len(keys) != len(set(keys)) or len(identities) != len(set(identities)):
        raise ValueError("Frontend form registry contains duplicate entries.")
    if routes != set(UNIFIED_FRONTEND_POST_ROUTES):
        raise ValueError("Frontend form registry has missing or orphaned POST Routes.")
    command_values = {
        form.discriminator_value
        for form in FRONTEND_FORM_REGISTRY
        if form.action_route == "/sessions/command"
    }
    if command_values != set(SESSION_COMMAND_KINDS):
        raise ValueError("Session Command form registry coverage is incomplete.")
    mutation_values = {
        form.discriminator_value
        for form in FRONTEND_FORM_REGISTRY
        if form.action_route == "/matches/api/v1/operation"
    }
    if mutation_values != set(MATCH_CAPTURE_WEB_MUTATION_OPERATIONS):
        raise ValueError("Match mutation form registry coverage is incomplete.")


def resolve_frontend_form_v1(
    route: str,
    values: Mapping[str, object] | None = None,
    *,
    media_type: str | None = None,
) -> FrontendFormDefinitionV1:
    route_candidates = tuple(form for form in FRONTEND_FORM_REGISTRY if form.action_route == route)
    if not route_candidates:
        raise KeyError(route)
    supplied = values or {}
    if media_type is not None and any(
        supplied.get(form.discriminator_field or "") == form.discriminator_value
        and form.media_type != media_type
        for form in route_candidates
    ):
        raise ValueError("The shared form media type is unsupported.")
    candidates = tuple(
        form for form in route_candidates if media_type is None or form.media_type == media_type
    )
    if not candidates:
        raise ValueError("The shared form media type is unsupported.")
    if len(candidates) == 1:
        return candidates[0]
    matches = tuple(
        form
        for form in candidates
        if supplied.get(form.discriminator_field or "") == form.discriminator_value
    )
    if len(matches) == 1:
        return matches[0]
    raise ValueError("The shared form discriminator is missing or unsupported.")


def get_frontend_form_by_key_v1(form_key: str) -> FrontendFormDefinitionV1:
    for definition in FRONTEND_FORM_REGISTRY:
        if definition.form_key == form_key:
            return definition
    raise KeyError(form_key)


def capture_safe_submitted_values_v1(
    definition: FrontendFormDefinitionV1,
    values: Mapping[str, object],
) -> FormValuesV1:
    if type(definition) is not FrontendFormDefinitionV1 or not isinstance(values, Mapping):
        raise ValueError("Safe form capture requires a registered form and value mapping.")
    entries: list[FormValueV1] = []
    for field in definition.safe_fields:
        if field.control_type == "file" or field.clear_after_rejection:
            continue
        raw = values.get(field.field_key)
        if raw is None:
            if field.control_type == "checkbox" or field.cardinality == "repeated":
                entries.append(FormValueV1(field=field.field_key, values=("",)))
            continue
        if isinstance(raw, str):
            retained = (raw,)
        elif isinstance(raw, (list, tuple)) and all(type(item) is str for item in raw):
            retained = tuple(raw)
        else:
            continue
        if field.cardinality == "single" and len(retained) != 1:
            continue
        if not retained or len(retained) > 64:
            continue
        if any(len(value) > field.reflection_length for value in retained):
            continue
        if field.allowed_values and any(value not in field.allowed_values for value in retained):
            continue
        if field.control_type == "card" and any(
            value
            and (
                len(value) not in {2, 3}
                or value[0] not in "CSHD"
                or value[1:] not in {"A", "10", "K", "Q", "J", "9", "8", "7"}
            )
            for value in retained
        ):
            continue
        entries.append(FormValueV1(field=field.field_key, values=retained))
    return FormValuesV1(tuple(entries))
