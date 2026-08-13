from __future__ import annotations

import os
import stat
import threading
from dataclasses import dataclass, field
from pathlib import Path

from skat_ai.match_workspace_contracts import MatchWorkspaceV1
from skat_ai.match_workspace_persistence import (
    load_match_workspace_file_v1,
    save_match_workspace_file_v1,
)
from skat_ai.match_workspace_persistence_codec import (
    build_match_workspace_persistence_document_v1,
)

from .report_store import MatchAnalysisReportStoreV1


@dataclass(slots=True)
class MatchCaptureWebContextV1:
    """Mutable one-file transport state serialized by one process-local lock."""

    workspace_path: Path
    workspace: MatchWorkspaceV1 | None
    content_fingerprint: str | None
    report_store: MatchAnalysisReportStoreV1 = field(
        default_factory=MatchAnalysisReportStoreV1,
        repr=False,
    )
    lock: threading.RLock = field(default_factory=threading.RLock, repr=False)

    @property
    def workspace_filename(self) -> str:
        return self.workspace_path.name

    @classmethod
    def open(cls, file_path: str | os.PathLike[str]) -> MatchCaptureWebContextV1:
        path = Path(file_path).expanduser()
        parent_mode = os.stat(path.parent).st_mode
        if not stat.S_ISDIR(parent_mode):
            raise NotADirectoryError(
                "Match Workspace parent must be an existing directory."
            )
        try:
            resumed = load_match_workspace_file_v1(path)
        except FileNotFoundError:
            return cls(
                workspace_path=path,
                workspace=None,
                content_fingerprint=None,
            )
        return cls(
            workspace_path=path,
            workspace=resumed.document.workspace,
            content_fingerprint=resumed.document.content_fingerprint,
        )

    def reload(self) -> MatchWorkspaceV1 | None:
        """Strictly reloads the fixed target without selecting another path."""
        with self.lock:
            try:
                resumed = load_match_workspace_file_v1(self.workspace_path)
            except FileNotFoundError:
                self.workspace = None
                self.content_fingerprint = None
                self.report_store.clear()
                return None
            self.workspace = resumed.document.workspace
            self.content_fingerprint = resumed.document.content_fingerprint
            self.report_store.clear()
            return self.workspace

    def save_candidate(self, workspace: MatchWorkspaceV1) -> str:
        """Saves once and replaces context only after confirmed persisted content."""
        with self.lock:
            document = build_match_workspace_persistence_document_v1(workspace)
            result = save_match_workspace_file_v1(
                self.workspace_path,
                document,
                expected_content_fingerprint=self.content_fingerprint,
            )
            if result.status in {"saved", "unchanged"}:
                self.workspace = workspace
                self.content_fingerprint = document.content_fingerprint
            return result.status
