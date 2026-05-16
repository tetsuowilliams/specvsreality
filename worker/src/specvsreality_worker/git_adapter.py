"""Read commits and file contents from a local git clone."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from git import Blob, Repo
from git.exc import BadName, GitCommandError
from git.objects.commit import Commit
from git.objects.tree import Tree
from pydantic import BaseModel


class GitAdapterError(Exception):
    """Raised when the repository cannot satisfy a read operation."""


class GitCommitPathInformation(BaseModel):
    new_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]


def _commit_or_raise(repo: Repo, commit_sha: str) -> Commit:
    try:
        commit = repo.commit(commit_sha)
        # GitPython resolves the object lazily; touch the tree to detect missing SHAs.
        _ = commit.tree
    except (BadName, ValueError) as e:
        raise GitAdapterError(f"Unknown commit: {commit_sha!r}") from e
    return commit


class GitAdapter:
    """
    Thin wrapper over GitPython for a repository on disk.

    Default branch is ``main`` if it exists, otherwise ``master``. Merge commits
    compare against the first parent when listing changed paths.
    """

    def __init__(self, repo_path: str | Path) -> None:
        self._path = Path(repo_path).resolve()
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
        """Return changed paths grouped by type against the first parent."""
        commit = _commit_or_raise(self._repo, commit_sha)

        if not commit.parents:
            return GitCommitPathInformation(
                new_files=sorted(_all_blob_paths(commit.tree)),
                modified_files=[],
                deleted_files=[],
            )

        parent = commit.parents[0]
        new_files: set[str] = set()
        modified_files: set[str] = set()
        deleted_files: set[str] = set()
        for diff in parent.diff(commit):
            if diff.change_type == "A":
                if diff.b_path:
                    new_files.add(diff.b_path)
                continue

            if diff.change_type == "D":
                if diff.a_path:
                    deleted_files.add(diff.a_path)
                continue

            # Treat modify/rename/type-change as updates to the current file path.
            if diff.b_path:
                modified_files.add(diff.b_path)
            elif diff.a_path:
                modified_files.add(diff.a_path)

        return GitCommitPathInformation(
            new_files=sorted(new_files),
            modified_files=sorted(modified_files),
            deleted_files=sorted(deleted_files),
        )

    def commit_datetime(self, commit_sha: str) -> datetime:
        """Authored timestamp for a commit SHA."""
        commit = _commit_or_raise(self._repo, commit_sha)
        return commit.authored_datetime

    def file_at_commit(self, commit_sha: str, relpath: str) -> str:
        """UTF-8 text of the file at ``relpath`` in the given commit."""
        commit = _commit_or_raise(self._repo, commit_sha)

        key = relpath.replace("\\", "/").strip("/")
        if not key:
            raise GitAdapterError("relpath must be non-empty")

        try:
            obj = _tree_get_path(commit.tree, key)
        except KeyError as e:
            raise GitAdapterError(f"No path {relpath!r} at commit {commit_sha[:7]}") from e

        if not isinstance(obj, Blob):
            raise GitAdapterError(f"Not a file (blob): {relpath!r}")

        raw: bytes = obj.data_stream.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise GitAdapterError(f"File is not valid UTF-8: {relpath!r}") from e

    def file_at_commit_or_none(self, commit_sha: str, relpath: str) -> str | None:
        """UTF-8 text of the file at ``relpath`` in the commit, or ``None`` if the path is absent."""
        commit = _commit_or_raise(self._repo, commit_sha)

        key = relpath.replace("\\", "/").strip("/")
        if not key:
            raise GitAdapterError("relpath must be non-empty")

        try:
            obj = _tree_get_path(commit.tree, key)
        except KeyError:
            return None

        if not isinstance(obj, Blob):
            raise GitAdapterError(f"Not a file (blob): {relpath!r}")

        raw: bytes = obj.data_stream.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as e:
            raise GitAdapterError(f"File is not valid UTF-8: {relpath!r}") from e

    def list_files_at_commit(self, commit_sha: str) -> list[str]:
        """List all blob paths visible at a commit."""
        commit = _commit_or_raise(self._repo, commit_sha)
        return sorted(_all_blob_paths(commit.tree))


def _all_blob_paths(tree: Tree, prefix: str = "") -> Iterator[str]:
    for item in tree:
        rel = f"{prefix}{item.name}"
        if item.type == "tree":
            yield from _all_blob_paths(item, rel + "/")
        else:
            yield rel


def _tree_get_path(tree: Tree, posix_path: str) -> Blob | Tree:
    parts = posix_path.split("/")
    current: Blob | Tree = tree
    for part in parts:
        if not part:
            continue
        if isinstance(current, Blob):
            raise KeyError(posix_path)
        current = current[part]
    return current
