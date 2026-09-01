from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .frontend_profile_contracts import LocalFrontendProfileV1
from .frontend_profile_persistence import (
    frontend_profile_path_v1,
    load_frontend_profile_file_v1,
)
from .locale_resolution import resolve_frontend_locale_v1
from .localization_contracts import BrowserSafeFrontendProfileStateV1


@dataclass(frozen=True, slots=True)
class FrontendProfileStateV1:
    profile_path: Path
    load_status: str
    document: LocalFrontendProfileV1 | None
    expected_fingerprint: str | None
    invalid_raw_digest: str | None
    generation: int
    warning: bool

    def __post_init__(self) -> None:
        if not isinstance(self.profile_path, Path):
            raise ValueError("profile_path must be a Path.")
        if self.load_status not in {"absent", "available", "invalid"}:
            raise ValueError("load_status must be canonical.")
        if type(self.generation) is not int or self.generation < 0:
            raise ValueError("generation must be a non-negative integer.")
        if type(self.warning) is not bool or self.warning != (self.load_status == "invalid"):
            raise ValueError("warning must identify exactly an invalid profile.")
        if self.load_status == "available":
            if type(self.document) is not LocalFrontendProfileV1:
                raise ValueError("Available state requires one exact profile document.")
            if self.expected_fingerprint != self.document.content_fingerprint:
                raise ValueError("Available state must retain the expected fingerprint.")
            if self.invalid_raw_digest is not None:
                raise ValueError("Available state must not retain an invalid digest.")
        elif self.document is not None or self.expected_fingerprint is not None:
            raise ValueError("Unavailable state must not retain a trusted document.")
        if self.load_status == "invalid" and self.invalid_raw_digest is None:
            raise ValueError("Invalid state must retain its observation digest.")
        if self.load_status != "invalid" and self.invalid_raw_digest is not None:
            raise ValueError("Only invalid state may retain an invalid digest.")
        if self.invalid_raw_digest is not None and (
            len(self.invalid_raw_digest) != 64
            or any(character not in "0123456789abcdef" for character in self.invalid_raw_digest)
        ):
            raise ValueError("Invalid profile observation digest must be lowercase SHA-256.")


def build_frontend_profile_state_v1(
    managed_data_root: Path,
    *,
    generation: int = 0,
) -> FrontendProfileStateV1:
    load = load_frontend_profile_file_v1(managed_data_root)
    return FrontendProfileStateV1(
        profile_path=frontend_profile_path_v1(managed_data_root),
        load_status=load.status,
        document=load.document,
        expected_fingerprint=(
            None if load.document is None else load.document.content_fingerprint
        ),
        invalid_raw_digest=load.invalid_raw_digest,
        generation=generation,
        warning=load.status == "invalid",
    )


def state_from_saved_profile_v1(
    prior: FrontendProfileStateV1,
    document: LocalFrontendProfileV1,
) -> FrontendProfileStateV1:
    return FrontendProfileStateV1(
        profile_path=prior.profile_path,
        load_status="available",
        document=document,
        expected_fingerprint=document.content_fingerprint,
        invalid_raw_digest=None,
        generation=prior.generation + 1,
        warning=False,
    )


def project_browser_safe_frontend_profile_state_v1(
    state: FrontendProfileStateV1,
    *,
    accept_language: str | None,
) -> BrowserSafeFrontendProfileStateV1:
    if type(state) is not FrontendProfileStateV1:
        raise ValueError("state must be an exact FrontendProfileStateV1.")
    saved_language = None if state.document is None else state.document.language
    resolution = resolve_frontend_locale_v1(
        saved_language=saved_language,
        accept_language=accept_language,
        profile_status=state.load_status,
    )
    return BrowserSafeFrontendProfileStateV1(
        locale=resolution.locale,
        resolution_source=resolution.source,
        profile_status=state.load_status,
        profile_revision=None if state.document is None else state.document.revision,
        profile_generation=state.generation,
        warning=state.warning,
    )
