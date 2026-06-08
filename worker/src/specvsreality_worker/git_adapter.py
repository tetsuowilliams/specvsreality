"""Read commits and file contents from a local git clone."""

from __future__ import annotations

import io
import subprocess
from collections.abc import Iterator
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath

from git import Repo
from git.exc import BadName, GitCommandError
from git.objects.commit import Commit
from pydantic import BaseModel

from specvsreality_worker.core.spec_detection import ArtifactType, SpecDetection


class GitAdapterError(Exception):
    """Raised when the repository cannot satisfy a read operation."""


class PathChangeState(StrEnum):
    NEW = "new"
    MODIFIED = "modified"
    DELETED = "deleted"


class ChangedPath(BaseModel):
    path: str
    state: PathChangeState
    artifact_type: ArtifactType


class GitCommitPathInformation(BaseModel):
    paths: list[ChangedPath]


def _commit_or_raise(repo: Repo, commit_sha: str) -> Commit:
    try:
        repo.git.rev_parse("--verify", f"{commit_sha}^{{commit}}")
        return repo.commit(commit_sha)
    except (BadName, ValueError, GitCommandError) as e:
        raise GitAdapterError(f"Unknown commit: {commit_sha!r}") from e


def _parse_ls_tree_line(line: str) -> tuple[str, str] | None:
    """Return ``(object_type, path)`` from one ``git ls-tree`` line, or ``None`` if malformed."""
    tab = line.find("\t")
    if tab < 0:
        return None
    meta, path = line[:tab], line[tab + 1 :]
    parts = meta.split()
    if len(parts) < 2 or not path:
        return None
    return parts[1], path


def _blob_paths_at_commit(repo: Repo, commit_sha: str) -> list[str]:
    """All blob paths at ``commit_sha`` via ``git ls-tree -r`` (avoids GitPython tree parsing bugs)."""
    try:
        output = repo.git.ls_tree(commit_sha, r=True)
    except GitCommandError as e:
        raise GitAdapterError(f"Cannot list files at commit {commit_sha[:7]}: {e}") from e

    paths: list[str] = []
    for line in output.splitlines():
        parsed = _parse_ls_tree_line(line)
        if parsed is None:
            continue
        obj_type, path = parsed
        if obj_type == "blob":
            paths.append(path)
    return paths


def _treeish_at_path(commit_sha: str, tree_path: str) -> str:
    """Revision spec for ``git ls-tree`` at a directory (``tree_path`` empty = commit root)."""
    return commit_sha if not tree_path else f"{commit_sha}:{tree_path}"


def _ls_tree_children(repo: Repo, commit_sha: str, tree_path: str) -> list[tuple[str, str]]:
    """Immediate children under ``tree_path`` (``""`` for repo root) as ``(type, name)`` pairs."""
    try:
        output = repo.git.ls_tree(_treeish_at_path(commit_sha, tree_path))
    except GitCommandError as e:
        raise GitAdapterError(
            f"Cannot list directory {tree_path!r} at commit {commit_sha[:7]}: {e}",
        ) from e

    children: list[tuple[str, str]] = []
    for line in output.splitlines():
        parsed = _parse_ls_tree_line(line)
        if parsed is None:
            continue
        obj_type, name = parsed
        children.append((obj_type, name))
    return children


def _object_type_at_path(repo: Repo, commit_sha: str, relpath: str) -> str | None:
    """Return git object type at ``relpath`` (``blob``, ``tree``, …) or ``None`` if missing."""
    try:
        output = repo.git.ls_tree(commit_sha, relpath)
    except GitCommandError:
        return None

    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        return None

    parsed = _parse_ls_tree_line(lines[0])
    return parsed[0] if parsed is not None else None


def _git_blob_size(repo: Repo, commit_sha: str, relpath: str) -> int:
    """Return blob byte size at ``relpath`` without reading content."""
    obj_type = _object_type_at_path(repo, commit_sha, relpath)
    if obj_type is None:
        raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}")
    if obj_type != "blob":
        raise GitAdapterError(f"Not a file (blob): {relpath!r}")

    spec = f"{commit_sha}:{relpath}"
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-s", spec],
            cwd=repo.working_dir,
            capture_output=True,
            check=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitAdapterError(f"Timed out reading size for {relpath!r}") from exc
    except subprocess.CalledProcessError as e:
        raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}") from e

    try:
        return int(proc.stdout.decode().strip())
    except ValueError as exc:
        raise GitAdapterError(f"Invalid blob size for {relpath!r}") from exc


def _git_show_text(
    repo: Repo,
    commit_sha: str,
    relpath: str,
    *,
    subprocess_timeout_s: float = 30,
) -> str:
    """UTF-8 file contents at ``relpath`` in ``commit_sha`` using ``git cat-file -p``."""
    obj_type = _object_type_at_path(repo, commit_sha, relpath)
    if obj_type is None:
        raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}")
    if obj_type != "blob":
        raise GitAdapterError(f"Not a file (blob): {relpath!r}")

    spec = f"{commit_sha}:{relpath}"
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-p", spec],
            cwd=repo.working_dir,
            capture_output=True,
            check=True,
            timeout=subprocess_timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitAdapterError(f"Timed out reading {relpath!r} at commit {commit_sha[:7]}") from exc
    except subprocess.CalledProcessError as e:
        raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}") from e

    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitAdapterError(f"File is not valid UTF-8: {relpath!r}") from exc


def _git_show_text_lines(
    repo: Repo,
    commit_sha: str,
    relpath: str,
    *,
    start_line: int,
    end_line: int,
    subprocess_timeout_s: float = 30,
) -> list[str]:
    """Return lines ``start_line``..``end_line`` (1-based inclusive) without loading the whole blob."""
    if start_line < 1 or end_line < start_line:
        raise GitAdapterError(
            f"Invalid line range {start_line}-{end_line} for {relpath!r}",
        )

    obj_type = _object_type_at_path(repo, commit_sha, relpath)
    if obj_type is None:
        raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}")
    if obj_type != "blob":
        raise GitAdapterError(f"Not a file (blob): {relpath!r}")

    spec = f"{commit_sha}:{relpath}"
    proc = subprocess.Popen(
        ["git", "cat-file", "-p", spec],
        cwd=repo.working_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    selected: list[str] = []
    try:
        if proc.stdout is None:
            raise GitAdapterError(f"Cannot read {relpath!r} at commit {commit_sha[:7]}")
        reader = io.TextIOWrapper(proc.stdout, encoding="utf-8", errors="replace")
        for lineno, line in enumerate(reader, start=1):
            if lineno < start_line:
                continue
            if lineno > end_line:
                break
            selected.append(line.rstrip("\n\r"))
    except UnicodeDecodeError as exc:
        raise GitAdapterError(f"File is not valid UTF-8: {relpath!r}") from exc
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        proc.terminate()
        try:
            proc.wait(timeout=subprocess_timeout_s)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            proc.wait(timeout=5)
            raise GitAdapterError(
                f"Timed out reading lines {start_line}-{end_line} of {relpath!r}",
            ) from exc

    return selected


class GitAdapter:
    """
    Thin wrapper over GitPython for a repository on disk.

    Default branch is ``main`` if it exists, otherwise ``master``. Merge commits
    compare against the first parent when listing changed paths.
    """

    def __init__(
        self,
        repo_path: str | Path,
        *,
        spec_detection: SpecDetection | None = None,
    ) -> None:
        self._path = Path(repo_path).resolve()
        self._spec_detection = spec_detection or SpecDetection()
        try:
            self._repo = Repo(self._path)
        except GitCommandError as e:  # pragma: no cover - invalid path
            raise GitAdapterError(f"Not a git repository: {self._path}") from e
        if self._repo.bare:
            raise GitAdapterError(f"Non-bare repository required: {self._path}")

    @property
    def path(self) -> Path:
        return self._path

    def default_branch_ref(self) -> str:
        """Return preferred default branch, with graceful fallbacks."""
        names = {h.name for h in self._repo.heads}
        for candidate in ("main", "master"):
            if candidate in names:
                return candidate

        if not self._repo.head.is_detached:
            return self._repo.active_branch.name

        try:
            origin_head = self._repo.git.symbolic_ref("refs/remotes/origin/HEAD")
            if origin_head.startswith("refs/remotes/origin/"):
                candidate = origin_head.removeprefix("refs/remotes/origin/")
                if candidate:
                    return candidate
        except GitCommandError:
            pass

        if names:
            return sorted(names)[0]

        raise GitAdapterError("Repository has no local heads to walk")

    def iter_commits_since(self, since_sha: str | None) -> Iterator[str]:
        """
        Walk the default branch oldest-first.

        If ``since_sha`` is None, yield every commit on the branch. Otherwise yield
        commits reachable from the branch tip but not from ``since_sha`` (git
        ``since_sha..branch``), i.e. exclusive of ``since_sha``.
        """
        branch = self.default_branch_ref()
        rev = branch if since_sha is None else f"{since_sha}..{branch}"
        try:
            for commit in self._repo.iter_commits(rev=rev, reverse=True):
                yield commit.hexsha
        except GitCommandError as e:
            raise GitAdapterError(f"Invalid revision range: {rev!r}") from e

    def changed_paths(self, commit_sha: str) -> GitCommitPathInformation:
        """Return changed paths with state and artifact type against the first parent."""
        commit = _commit_or_raise(self._repo, commit_sha)
        paths: list[ChangedPath] = []

        if not commit.parents:
            for path in sorted(_blob_paths_at_commit(self._repo, commit_sha)):
                if not self._spec_detection.is_tracked_path(path):
                    continue
                paths.append(
                    ChangedPath(
                        path=path,
                        state=PathChangeState.NEW,
                        artifact_type=self._spec_detection.artifact_type(path),
                    )
                )
            return GitCommitPathInformation(paths=paths)

        parent = commit.parents[0]
        for diff in parent.diff(commit):
            if diff.change_type == "A":
                if diff.b_path and self._spec_detection.is_tracked_path(diff.b_path):
                    paths.append(
                        ChangedPath(
                            path=diff.b_path,
                            state=PathChangeState.NEW,
                            artifact_type=self._spec_detection.artifact_type(diff.b_path),
                        )
                    )
                continue

            if diff.change_type == "D":
                if diff.a_path and self._spec_detection.is_tracked_path(diff.a_path):
                    paths.append(
                        ChangedPath(
                            path=diff.a_path,
                            state=PathChangeState.DELETED,
                            artifact_type=self._spec_detection.artifact_type(diff.a_path),
                        )
                    )
                continue

            # Treat modify/rename/type-change as updates to the current file path.
            path = diff.b_path or diff.a_path
            if path and self._spec_detection.is_tracked_path(path):
                paths.append(
                    ChangedPath(
                        path=path,
                        state=PathChangeState.MODIFIED,
                        artifact_type=self._spec_detection.artifact_type(path),
                    )
                )

        paths.sort(key=lambda item: item.path)
        return GitCommitPathInformation(paths=paths)

    def commit_datetime(self, commit_sha: str) -> datetime:
        """Authored timestamp for a commit SHA."""
        commit = _commit_or_raise(self._repo, commit_sha)
        return commit.authored_datetime

    def commit_message(self, commit_sha: str) -> str:
        """Full commit message for a commit SHA."""
        commit = _commit_or_raise(self._repo, commit_sha)
        message = commit.message
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="replace")
        return message.strip()

    def blob_size_at_commit(self, commit_sha: str, relpath: str) -> int:
        """Byte size of the blob at ``relpath`` in the given commit."""
        _commit_or_raise(self._repo, commit_sha)

        key = relpath.replace("\\", "/").strip("/")
        if not key:
            raise GitAdapterError("relpath must be non-empty")

        return _git_blob_size(self._repo, commit_sha, key)

    def file_at_commit(self, commit_sha: str, relpath: str) -> str:
        """UTF-8 text of the file at ``relpath`` in the given commit."""
        _commit_or_raise(self._repo, commit_sha)

        key = relpath.replace("\\", "/").strip("/")
        if not key:
            raise GitAdapterError("relpath must be non-empty")

        return _git_show_text(self._repo, commit_sha, key)

    def file_lines_at_commit(
        self,
        commit_sha: str,
        relpath: str,
        *,
        start_line: int,
        end_line: int,
    ) -> list[str]:
        """Return a 1-based inclusive line slice without loading the entire blob."""
        _commit_or_raise(self._repo, commit_sha)

        key = relpath.replace("\\", "/").strip("/")
        if not key:
            raise GitAdapterError("relpath must be non-empty")

        return _git_show_text_lines(
            self._repo,
            commit_sha,
            key,
            start_line=start_line,
            end_line=end_line,
        )

    def file_at_commit_or_none(self, commit_sha: str, relpath: str) -> str | None:
        """UTF-8 text of the file at ``relpath`` in the commit, or ``None`` if the path is absent."""
        _commit_or_raise(self._repo, commit_sha)

        key = relpath.replace("\\", "/").strip("/")
        if not key:
            raise GitAdapterError("relpath must be non-empty")

        try:
            return _git_show_text(self._repo, commit_sha, key)
        except GitAdapterError:
            return None

    def list_files_at_commit(self, commit_sha: str) -> list[str]:
        """List tracked blob paths visible at a commit."""
        _commit_or_raise(self._repo, commit_sha)
        return sorted(
            p
            for p in _blob_paths_at_commit(self._repo, commit_sha)
            if self._spec_detection.is_tracked_path(p)
        )

    def list_directory_at_commit(self, commit_sha: str, relpath: str = ".") -> list[str]:
        """List immediate children under ``relpath`` at the given commit."""
        _commit_or_raise(self._repo, commit_sha)

        normalized = relpath.replace("\\", "/").strip()
        if normalized in {"", "."}:
            key = ""
        else:
            key = normalized.strip("/")
        if key and ".." in PurePosixPath(key).parts:
            raise GitAdapterError(f"Invalid path: {relpath!r}")

        if key:
            obj_type = _object_type_at_path(self._repo, commit_sha, key)
            if obj_type is None:
                raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}")
            if obj_type != "tree":
                raise GitAdapterError(f"Not a directory: {relpath!r}")

        entries = _ls_tree_children(self._repo, commit_sha, key)

        prefix = f"{key}/" if key else ""
        children: list[str] = []
        for obj_type, name in entries:
            child = f"{prefix}{name}"
            if obj_type == "tree":
                child_dir = f"{child}/"
                if self._spec_detection.is_tracked_path(child) or child.startswith(
                    f"{self._spec_detection.SPECS_DIR}/",
                ):
                    children.append(child_dir)
            elif obj_type == "blob" and self._spec_detection.is_tracked_path(child):
                children.append(child)
        return sorted(children)
