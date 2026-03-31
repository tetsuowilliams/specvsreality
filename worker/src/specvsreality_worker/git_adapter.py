"""Read commits and file contents from a local git clone."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from git import Blob, Repo
from git.exc import BadName, GitCommandError
from git.objects.commit import Commit
from git.objects.tree import Tree


class GitAdapterError(Exception):
    """Raised when the repository cannot satisfy a read operation."""


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
        """Return ``main`` or ``master``, whichever exists."""
        names = {h.name for h in self._repo.heads}
        for candidate in ("main", "master"):
            if candidate in names:
                return candidate
        raise GitAdapterError(
            f"Repository has neither main nor master branch (heads: {sorted(names)!r})"
        )

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

    def changed_paths(self, commit_sha: str) -> list[str]:
        """Paths touched in this commit vs its first parent; root commit = full tree."""
        commit = _commit_or_raise(self._repo, commit_sha)

        if not commit.parents:
            return sorted(_all_blob_paths(commit.tree))

        parent = commit.parents[0]
        paths: set[str] = set()
        for diff in parent.diff(commit):
            if diff.a_path:
                paths.add(diff.a_path)
            if diff.b_path:
                paths.add(diff.b_path)
        return sorted(paths)

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
