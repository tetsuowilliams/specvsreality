from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import ClassVar


class ArtifactType(StrEnum):
    SPEC = "spec"
    CODE = "code"


class SpecDetection:
    SPEC_FILENAMES: ClassVar[frozenset[str]] = frozenset({"plan.md", "tasks.md", "spec.md"})
    SPECS_DIR: ClassVar[str] = "specs"
    IGNORED_DIR_SEGMENTS: ClassVar[frozenset[str]] = frozenset({".cursor", ".specify", ".skills"})
    BINARY_FILE_SUFFIXES: ClassVar[frozenset[str]] = frozenset(
        {
            ".pdf",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".zip",
            ".gz",
            ".tar",
            ".pyc",
            ".woff",
            ".woff2",
            ".ico",
            ".mp4",
            ".mp3",
        },
    )

    def is_tracked_path(self, relpath: str) -> bool:
        """
        Return True for paths we scan: anything under ``specs/``, or any other path
        that does not pass through an ignored tooling directory.
        """
        posix = relpath.replace("\\", "/").strip("/")
        if not posix:
            return False
        parts = PurePosixPath(posix).parts
        if parts[0] == self.SPECS_DIR:
            return True
        return not any(part in self.IGNORED_DIR_SEGMENTS for part in parts)

    def is_spec_file(self, relpath: str) -> bool:
        basename = PurePosixPath(relpath.replace("\\", "/")).name
        return basename.lower() in self.SPEC_FILENAMES

    def get_parent_spec_folder(self, relpath: str) -> str | None:
        parent = PurePosixPath(relpath.replace("\\", "/")).parent.name
        return parent or None

    def artifact_type(self, relpath: str) -> ArtifactType:
        return ArtifactType.SPEC if self.is_spec_file(relpath) else ArtifactType.CODE

    def is_text_file(self, relpath: str) -> bool:
        """Return False for known binary extensions (images, archives, fonts, etc.)."""
        lower = relpath.replace("\\", "/").lower()
        return not any(lower.endswith(suffix) for suffix in self.BINARY_FILE_SUFFIXES)
