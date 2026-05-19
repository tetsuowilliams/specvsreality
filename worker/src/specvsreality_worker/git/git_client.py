"""Read commits, trees, blobs, and refs from a local git clone."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from git import Blob as GitBlob
from git import Repo
from git.exc import BadName, GitCommandError
from git.objects.commit import Commit as GitCommit
from git.objects.tree import Tree as GitTree

from specvsreality_worker.domain import CommitRecord, ParentRef, TreeEntry


class GitClientError(Exception):
    """Raised when the repository cannot satisfy a read operation."""


@dataclass(frozen=True)
class RefRecord:
    """A branch or tag pointer (``ref_type`` is ``'branch'`` or ``'tag'``)."""

    name: str
    ref_type: str
    target_sha: str


class GitClient:
    """Repo-scoped reader: returns plain dataclasses; never touches the DB.

    Constructed with ``repository_id`` so emitted ``CommitRecord`` objects can be
    persisted directly without lookups. Default branch falls back to ``main`` →
    ``master`` → first local head, mirroring the legacy adapter semantics.
    """

    def __init__(self, *, repo_path: str | Path, repository_id: int) -> None:
        self._path = Path(repo_path).resolve()
        try:
            self._repo = Repo(self._path)
        except GitCommandError as e:  # pragma: no cover - invalid path
            raise GitClientError(f"Not a git repository: {self._path}") from e
        if self._repo.bare:
            raise GitClientError(f"Non-bare repository required: {self._path}")
        self._repository_id = repository_id

    @property
    def path(self) -> Path:
        return self._path

    @property
    def repository_id(self) -> int:
        return self._repository_id

    def default_branch_ref(self) -> str:
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
        raise GitClientError("Repository has no local heads to walk")

    def iter_commits(self, *, oldest_first: bool = True) -> Iterator[CommitRecord]:
        """Walk the default branch yielding every commit as a ``CommitRecord``."""
        branch = self.default_branch_ref()
        try:
            commits = list(self._repo.iter_commits(rev=branch, reverse=oldest_first))
        except GitCommandError as e:
            raise GitClientError(f"Invalid revision range: {branch!r}") from e
        for commit in commits:
            yield self._to_record(commit)

    def list_tree(self, commit_sha: str) -> list[TreeEntry]:
        """Every blob in the commit's tree, sorted by path."""
        commit = self._commit_or_raise(commit_sha)
        entries = list(self._iter_tree_entries(commit.tree))
        entries.sort(key=lambda e: e.path)
        return entries

    def read_blob(self, blob_sha: str) -> bytes:
        try:
            blob = self._repo.odb.stream(bytes.fromhex(blob_sha))
        except (BadName, ValueError) as e:
            raise GitClientError(f"Unknown blob: {blob_sha!r}") from e
        return blob.read()

    def list_refs(self) -> list[RefRecord]:
        out: list[RefRecord] = []
        for head in self._repo.heads:
            out.append(
                RefRecord(name=head.name, ref_type="branch", target_sha=head.commit.hexsha)
            )
        for tag in self._repo.tags:
            out.append(
                RefRecord(name=tag.name, ref_type="tag", target_sha=tag.commit.hexsha)
            )
        return out

    def _to_record(self, commit: GitCommit) -> CommitRecord:
        parents = [
            ParentRef(parent_sha=parent.hexsha, parent_order=order)
            for order, parent in enumerate(commit.parents)
        ]
        return CommitRecord(
            sha=commit.hexsha,
            repository_id=self._repository_id,
            commit_date=commit.committed_datetime,
            parent_shas=parents,
            author_name=commit.author.name if commit.author else None,
            author_email=commit.author.email if commit.author else None,
            author_date=commit.authored_datetime,
            committer_name=commit.committer.name if commit.committer else None,
            committer_email=commit.committer.email if commit.committer else None,
            message=(
                commit.message
                if isinstance(commit.message, str)
                else commit.message.decode("utf-8", "replace")
            ),
        )

    def _iter_tree_entries(
        self, tree: GitTree, prefix: str = ""
    ) -> Iterator[TreeEntry]:
        for item in tree:
            relative = f"{prefix}{item.name}"
            if item.type == "tree":
                yield from self._iter_tree_entries(item, relative + "/")
                continue
            if isinstance(item, GitBlob):
                yield TreeEntry(
                    path=relative,
                    blob_sha=item.hexsha,
                    size_bytes=item.size,
                    mode=oct(item.mode)[2:],
                )

    def _commit_or_raise(self, commit_sha: str) -> GitCommit:
        try:
            commit = self._repo.commit(commit_sha)
            _ = commit.tree
        except (BadName, ValueError) as e:
            raise GitClientError(f"Unknown commit: {commit_sha!r}") from e
        return commit
