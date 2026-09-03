from __future__ import annotations

from pathlib import Path

import skatmind.api.v1.session as session_api
from skatmind.api.v1.session import files as session_files
from skatmind.app_web.friendly_creation_rendering import (
    render_friendly_managed_category_landing_v1,
    render_profile_driven_match_creation_v1,
)
from skatmind.app_web.frontend_profile_codec import build_local_frontend_profile_v1
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.managed_item_discovery import (
    apply_managed_item_display_labels_v1,
    discover_managed_items_v1,
)
from skatmind.app_web.managed_item_storage import build_managed_item_storage_path_v1
from skatmind.app_web.profile_player_contracts import (
    KnownPlayerV1,
    ManagedItemDisplayLabelV1,
)


def _profile():
    player = KnownPlayerV1("frontend-player-" + "a" * 64, "Henning", (), ())
    return build_local_frontend_profile_v1(
        known_players=(player,),
        own_player_id=player.player_id,
        preferred_perspective_player_id=player.player_id,
        preferred_game_platform="EuroSkat",
    )


def test_session_and_learning_creation_are_bilingual_name_first_and_id_free(
    tmp_path: Path,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    for family, locale, required, forbidden in (
        ("sessions", "en", "Name of this game", "Session ID"),
        ("sessions", "de", "Name dieses Spiels", "Session-ID"),
        ("corpora", "en", "Name of this learning collection", "Corpus ID"),
        ("corpora", "de", "Name dieser Lernsammlung", "Korpus-ID"),
    ):
        view = discover_managed_items_v1(
            home.category(family).path,
            family=family,
            generation=1,
        ).view
        html = render_friendly_managed_category_landing_v1(
            view,
            profile=_profile(),
            profile_generation=3,
            locale=locale,
        )
        assert required in html
        assert forbidden not in html
        assert "frontend-player-" not in html
        assert 'name="profile_generation" value="3"' in html
        technical_fields = (
            ("session_id", "local_player_id", "player_1_id")
            if family == "sessions"
            else ("corpus_id",)
        )
        assert all(f'name="{field}"' not in html for field in technical_fields)


def test_match_creation_is_bilingual_friendly_and_keeps_technical_fields_advanced() -> None:
    english = render_profile_driven_match_creation_v1(
        profile=_profile(),
        profile_generation=4,
        locale="en",
    )
    german = render_profile_driven_match_creation_v1(
        profile=_profile(),
        profile_generation=4,
        locale="de",
    )
    for html, values in (
        (
            english,
            (
                "Match title",
                "Date played",
                "EuroSkat 36-game standard",
                "Advanced Match details",
                "Source URL",
            ),
        ),
        (
            german,
            (
                "Match-Titel",
                "Spieldatum",
                "EuroSkat-36er-Standard",
                "Erweiterte Match-Angaben",
                "Quellen-URL",
            ),
        ),
    ):
        assert all(value in html for value in values)
        assert "frontend-player-" not in html
        assert "euroskat_36_standard_v1" not in html
        assert 'name="match_id"' not in html
        assert 'name="perspective_player_id"' not in html
        assert 'name="player_1_id"' not in html
        assert html.count("<fieldset>") >= 3
        assert '<select name="perspective_seat"' in html
        assert html.index(
            "Advanced Match details" if html is english else "Erweiterte Match-Angaben"
        ) > html.index("Source URL" if html is english else "Quellen-URL")


def test_managed_label_overlay_and_page_order_do_not_expose_product_identity(
    tmp_path: Path,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    session_id = "private-session-product-id"
    state = session_api.create_session(
        session_id=session_id,
        players=(
            session_api.SessionPlayerV1(player_id="a", player_label="Anna", seat="forehand"),
            session_api.SessionPlayerV1(player_id="b", player_label="Peter", seat="middlehand"),
            session_api.SessionPlayerV1(player_id="c", player_label="Mira", seat="rearhand"),
        ),
        capture_mode="retrospective",
    ).value
    path = build_managed_item_storage_path_v1(
        home.category("sessions").path,
        family="sessions",
        product_id=session_id,
    )
    document = session_api.build_session_persistence_document(state).value
    assert (
        session_files.save_session_file(
            path,
            document,
            expected_content_fingerprint=None,
        ).value.status
        == "saved"
    )
    unlabeled_discovery = discover_managed_items_v1(
        home.category("sessions").path,
        family="sessions",
        generation=1,
    )
    discovery = apply_managed_item_display_labels_v1(
        unlabeled_discovery,
        (ManagedItemDisplayLabelV1("sessions", session_id, "Thursday game"),),
    )
    html = render_friendly_managed_category_landing_v1(
        discovery.view,
        profile=None,
        profile_generation=0,
        locale="en",
    )
    assert "Thursday game" in html
    assert session_id not in html
    assert html.index("Create a game") < html.index("Your saved games")
    assert html.index("Your saved games") < html.index("Import existing data")
    assert '<details class="secondary-action">' in html

    german = render_friendly_managed_category_landing_v1(
        unlabeled_discovery.view,
        profile=None,
        profile_generation=0,
        locale="de",
    )
    assert "Spiel mit Anna, Peter, Mira" in german
    assert "Session:" not in german
