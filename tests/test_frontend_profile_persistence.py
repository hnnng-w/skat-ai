from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from skatmind.app_web.context import AppWebContextV1
from skatmind.app_web.frontend_profile_codec import (
    build_frontend_profile_bytes_v1,
    build_frontend_profile_fingerprint_v1,
    build_local_frontend_profile_v1,
    resume_local_frontend_profile_v1,
)
from skatmind.app_web.frontend_profile_contracts import (
    FRONTEND_PROFILE_FILENAME,
    FRONTEND_PROFILE_FINGERPRINT_DOMAIN,
    FRONTEND_PROFILE_MAX_FILE_BYTES,
    LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND,
    LOCAL_FRONTEND_PROFILE_VERSION,
    FrontendProfileLoadResultV1,
)
from skatmind.app_web.frontend_profile_operations import (
    InvalidFrontendProfileResetRequiredError,
    reset_frontend_profile_v1,
    set_frontend_language_v1,
)
from skatmind.app_web.frontend_profile_persistence import (
    load_frontend_profile_file_v1,
    save_frontend_profile_file_v1,
)
from skatmind.app_web.managed_data import prepare_managed_home_v1
from skatmind.app_web.profile_player_contracts import (
    KnownPlayerPlatformIdV1,
    KnownPlayerV1,
)


def _expected_document(*, revision: int, language: str | None, fingerprint: str) -> dict:
    return {
        "local_frontend_profile_version": 1,
        "document_kind": "skatmind_frontend_profile",
        "revision": revision,
        "language": language,
        "interface_preferences": {"advanced_settings_expanded": False},
        "own_player_id": None,
        "known_players": [],
        "preferred_perspective_player_id": None,
        "preferred_game_platform": None,
        "workflow_preferences": {
            "position_analysis": None,
            "historical_review": None,
        },
        "managed_item_display_labels": [],
        "content_fingerprint": fingerprint,
    }


def test_profile_contract_shape_fingerprint_domain_and_canonical_bytes_are_exact() -> None:
    assert LOCAL_FRONTEND_PROFILE_VERSION == 1
    assert LOCAL_FRONTEND_PROFILE_DOCUMENT_KIND == "skatmind_frontend_profile"
    assert FRONTEND_PROFILE_FILENAME == "frontend-profile.json"
    assert FRONTEND_PROFILE_MAX_FILE_BYTES == 1_048_576
    assert FRONTEND_PROFILE_FINGERPRINT_DOMAIN == b"skatmind\0frontend_profile_v1\0"
    profile = build_local_frontend_profile_v1(revision=0, language="de")
    assert profile.to_dict() == _expected_document(
        revision=0,
        language="de",
        fingerprint=profile.content_fingerprint,
    )
    content = build_frontend_profile_bytes_v1(profile)
    assert content.startswith(b'{\n  "local_frontend_profile_version": 1,\n')
    assert content.endswith(b"\n") and not content.endswith(b"\n\n")
    assert b"\r" not in content and not content.startswith(b"\xef\xbb\xbf")
    assert json.loads(content) == profile.to_dict()

    payload = dict(profile.to_dict())
    del payload["content_fingerprint"]
    payload_bytes = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    assert profile.content_fingerprint == hashlib.sha256(
        FRONTEND_PROFILE_FINGERPRINT_DOMAIN + payload_bytes
    ).hexdigest()
    assert profile.content_fingerprint == build_frontend_profile_fingerprint_v1(
        revision=0,
        language="de",
    )


def test_profile_resume_rejects_unknown_future_and_forged_values() -> None:
    profile = build_local_frontend_profile_v1()
    valid = profile.to_dict()
    assert resume_local_frontend_profile_v1(valid) == profile
    for mutation in (
        {**valid, "unknown": None},
        {**valid, "language": "fr"},
        {**valid, "revision": True},
        {**valid, "known_players": [{"player_id": "future"}]},
        {**valid, "preferred_game_platform": "future"},
        {**valid, "content_fingerprint": "0" * 64},
    ):
        with pytest.raises(ValueError):
            resume_local_frontend_profile_v1(mutation)
    with pytest.raises(ValueError):
        build_frontend_profile_fingerprint_v1(revision=True, language=None)
    with pytest.raises(ValueError):
        build_frontend_profile_fingerprint_v1(revision=0, language="fr")


def test_startup_load_is_absent_and_writes_nothing(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    context = AppWebContextV1.create(home)
    assert context.frontend_profile.load_status == "absent"
    assert context.frontend_profile.profile_path == home.root / FRONTEND_PROFILE_FILENAME
    assert not context.frontend_profile.profile_path.exists()
    assert sorted(path.name for path in home.root.iterdir()) == [
        "corpora",
        "matches",
        "sessions",
    ]


def test_profile_save_unchanged_conflict_and_revision_progression(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    german = build_local_frontend_profile_v1(language="de")
    first = save_frontend_profile_file_v1(
        home.root,
        german,
        expected_fingerprint=None,
    )
    assert first.status == "saved"
    profile_path = home.root / FRONTEND_PROFILE_FILENAME
    initial_bytes = profile_path.read_bytes()
    initial_mtime = profile_path.stat().st_mtime_ns
    unchanged = save_frontend_profile_file_v1(
        home.root,
        german,
        expected_fingerprint=german.content_fingerprint,
    )
    assert unchanged.status == "unchanged"
    assert profile_path.read_bytes() == initial_bytes
    assert profile_path.stat().st_mtime_ns == initial_mtime

    english = build_local_frontend_profile_v1(revision=1, language="en")
    conflict = save_frontend_profile_file_v1(
        home.root,
        english,
        expected_fingerprint=None,
    )
    assert conflict.status == "conflict"
    saved = save_frontend_profile_file_v1(
        home.root,
        english,
        expected_fingerprint=german.content_fingerprint,
    )
    assert saved.status == "saved"
    loaded = load_frontend_profile_file_v1(home.root)
    assert loaded.status == "available" and loaded.document == english
    assert not tuple(home.root.glob(f".{FRONTEND_PROFILE_FILENAME}.*.tmp"))


def test_profile_save_validates_expected_state_and_exact_revision_transition(
    tmp_path: Path,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    for expected_fingerprint, expected_invalid_raw_digest in (
        ("not-a-digest", None),
        (None, "A" * 64),
        ("0" * 64, "1" * 64),
    ):
        with pytest.raises(ValueError):
            save_frontend_profile_file_v1(
                home.root,
                build_local_frontend_profile_v1(),
                expected_fingerprint=expected_fingerprint,
                expected_invalid_raw_digest=expected_invalid_raw_digest,
            )
    with pytest.raises(ValueError):
        save_frontend_profile_file_v1(
            home.root,
            build_local_frontend_profile_v1(revision=9),
            expected_fingerprint=None,
        )

    initial = build_local_frontend_profile_v1(language="de")
    assert (
        save_frontend_profile_file_v1(
            home.root,
            initial,
            expected_fingerprint=None,
        ).status
        == "saved"
    )
    with pytest.raises(ValueError):
        save_frontend_profile_file_v1(
            home.root,
            build_local_frontend_profile_v1(revision=2, language="en"),
            expected_fingerprint=initial.content_fingerprint,
        )


def test_profile_save_rejects_unreloadable_canonical_bytes_before_writing(
    tmp_path: Path,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    platform_ids = tuple(
        KnownPlayerPlatformIdV1(
            "EuroSkat",
            f"{index:02d}-" + "x" * 252,
        )
        for index in range(16)
    )
    players = tuple(
        KnownPlayerV1(
            f"frontend-player-{index:064x}",
            f"Player {index}",
            (),
            platform_ids,
        )
        for index in range(512)
    )
    oversized = build_local_frontend_profile_v1(known_players=players)
    assert len(build_frontend_profile_bytes_v1(oversized)) > FRONTEND_PROFILE_MAX_FILE_BYTES

    with pytest.raises(ValueError, match="bounded persistence limit"):
        save_frontend_profile_file_v1(
            home.root,
            oversized,
            expected_fingerprint=None,
        )
    assert not (home.root / FRONTEND_PROFILE_FILENAME).exists()
    assert not tuple(home.root.glob(f".{FRONTEND_PROFILE_FILENAME}.*.tmp"))


def test_profile_save_rechecks_target_immediately_before_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    requested = build_local_frontend_profile_v1(language="de")
    external = build_local_frontend_profile_v1(language="en")
    calls = 0

    def changing_observation(_managed_root: Path) -> FrontendProfileLoadResultV1:
        nonlocal calls
        calls += 1
        if calls == 1:
            return FrontendProfileLoadResultV1(status="absent")
        return FrontendProfileLoadResultV1(status="available", document=external)

    monkeypatch.setattr(
        "skatmind.app_web.frontend_profile_persistence.load_frontend_profile_file_v1",
        changing_observation,
    )
    result = save_frontend_profile_file_v1(
        home.root,
        requested,
        expected_fingerprint=None,
    )
    assert result.status == "conflict"
    assert calls == 2
    assert not (home.root / FRONTEND_PROFILE_FILENAME).exists()
    assert not tuple(home.root.glob(f".{FRONTEND_PROFILE_FILENAME}.*.tmp"))


@pytest.mark.parametrize(
    "raw",
    (
        b"\xef\xbb\xbf{}\n",
        b'{"revision":NaN}\n',
        b'{"revision":0,"revision":1}\n',
        b"[]\n",
        b"{not-json}\n",
        b"\xff",
    ),
)
def test_invalid_profiles_are_retained_with_only_a_raw_digest(
    tmp_path: Path,
    raw: bytes,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / FRONTEND_PROFILE_FILENAME
    path.write_bytes(raw)
    loaded = load_frontend_profile_file_v1(home.root)
    assert loaded.status == "invalid"
    assert loaded.document is None
    assert loaded.invalid_raw_digest == hashlib.sha256(raw).hexdigest()
    assert path.read_bytes() == raw


def test_noncanonical_profile_bytes_are_invalid_and_not_repaired(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    profile = build_local_frontend_profile_v1(language="de")
    raw = json.dumps(profile.to_dict(), separators=(",", ":")).encode()
    path = home.root / FRONTEND_PROFILE_FILENAME
    path.write_bytes(raw)
    assert load_frontend_profile_file_v1(home.root).status == "invalid"
    AppWebContextV1.create(home)
    assert path.read_bytes() == raw


def test_invalid_profile_requires_explicit_reset_before_language_save(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / FRONTEND_PROFILE_FILENAME
    invalid = b"invalid profile bytes\n"
    path.write_bytes(invalid)
    context = AppWebContextV1.create(home)
    assert context.frontend_profile.load_status == "invalid"
    assert context.frontend_profile.warning is True
    with pytest.raises(InvalidFrontendProfileResetRequiredError):
        set_frontend_language_v1(context, language="de", expected_generation=0)
    assert path.read_bytes() == invalid

    assert reset_frontend_profile_v1(context, expected_generation=0) == "saved"
    reset = load_frontend_profile_file_v1(home.root)
    assert reset.status == "available"
    assert reset.document == build_local_frontend_profile_v1()
    assert context.frontend_profile.generation == 1
    assert context.frontend_profile.warning is False
    assert set_frontend_language_v1(context, language="de", expected_generation=1) == "saved"
    assert context.frontend_profile.document is not None
    assert context.frontend_profile.document.revision == 1


def test_oversized_and_non_regular_profile_targets_are_invalid(tmp_path: Path) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / FRONTEND_PROFILE_FILENAME
    path.write_bytes(b"x" * (FRONTEND_PROFILE_MAX_FILE_BYTES + 1))
    oversized = load_frontend_profile_file_v1(home.root)
    assert oversized.status == "invalid"
    assert oversized.invalid_raw_digest is not None
    path.unlink()
    path.mkdir()
    non_regular = load_frontend_profile_file_v1(home.root)
    assert non_regular.status == "invalid"
    assert non_regular.invalid_raw_digest is not None

    context = AppWebContextV1.create(home)
    assert reset_frontend_profile_v1(context, expected_generation=0) == "saved"
    assert path.is_file()
    assert load_frontend_profile_file_v1(home.root).status == "available"


def test_profile_read_rejects_a_target_swapped_between_lstat_and_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / FRONTEND_PROFILE_FILENAME
    path.write_bytes(build_frontend_profile_bytes_v1(build_local_frontend_profile_v1()))
    replacement = home.root / "replacement"
    replacement_bytes = build_frontend_profile_bytes_v1(
        build_local_frontend_profile_v1(language="de")
    )
    replacement.write_bytes(replacement_bytes)
    original_open = os.open
    swapped = False

    def swapping_open(target, flags, mode=0o777):
        nonlocal swapped
        if Path(target) == path and not swapped:
            swapped = True
            path.unlink()
            replacement.replace(path)
        return original_open(target, flags, mode)

    monkeypatch.setattr(
        "skatmind.app_web.frontend_profile_persistence.os.open",
        swapping_open,
    )
    loaded = load_frontend_profile_file_v1(home.root)
    assert swapped is True
    assert loaded.status == "invalid"
    assert loaded.document is None
    assert path.read_bytes() == replacement_bytes


def test_failed_empty_directory_reset_restores_the_invalid_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = prepare_managed_home_v1(tmp_path / "managed")
    path = home.root / FRONTEND_PROFILE_FILENAME
    path.mkdir()
    context = AppWebContextV1.create(home)

    def failing_replace(_source, _target) -> None:
        raise OSError("injected replacement failure")

    monkeypatch.setattr(
        "skatmind.app_web.frontend_profile_persistence.os.replace",
        failing_replace,
    )
    with pytest.raises(OSError, match="injected replacement failure"):
        reset_frontend_profile_v1(context, expected_generation=0)
    assert path.is_dir()
    assert load_frontend_profile_file_v1(home.root).status == "invalid"
    assert not tuple(home.root.glob(f".{FRONTEND_PROFILE_FILENAME}.*.tmp"))
