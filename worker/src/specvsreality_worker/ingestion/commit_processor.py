"""Persist git structure (commit, parents, blobs, tree) for one commit."""

from __future__ import annotations

import logging

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.repos import (
    BlobRepo,
    CommitFileRepo,
    CommitRepo,
)
from specvsreality_worker.domain import CommitRecord, TreeEntry
from specvsreality_worker.git import GitClient

logger = logging.getLogger(__name__)


class CommitProcessor:
    """Idempotent: returns the commit's tree, persisting it on first sight only.

    The same call is safe to make twice -- the first run writes ``commits``,
    ``commit_parents``, ``blobs``, and ``commit_files`` rows; subsequent runs
    short-circuit on ``commit_repo.exists`` and only re-read the tree.
    """

    def __init__(
        self,
        *,
        git_client: GitClient,
        commit_repo: CommitRepo,
        blob_repo: BlobRepo,
        commit_file_repo: CommitFileRepo,
    ) -> None:
        self._git = git_client
        self._commit_repo = commit_repo
        self._blob_repo = blob_repo
        self._commit_file_repo = commit_file_repo

    def process(
        self, *, repository: Repository, commit: CommitRecord
    ) -> list[TreeEntry]:
        tree = self._git.list_tree(commit.sha)

        if self._commit_repo.exists(commit.sha):
            return tree

        del repository  # commit already carries repository_id
        self._commit_repo.insert(
            sha=commit.sha,
            repository_id=commit.repository_id,
            commit_date=commit.commit_date,
            author_name=commit.author_name,
            author_email=commit.author_email,
            author_date=commit.author_date,
            committer_name=commit.committer_name,
            committer_email=commit.committer_email,
            message=commit.message,
        )
        self._commit_repo.insert_parents(
            commit_sha=commit.sha,
            parents=[(p.parent_sha, p.parent_order) for p in commit.parent_shas],
        )

        for entry in tree:
            self._blob_repo.upsert(
                sha=entry.blob_sha, size_bytes=entry.size_bytes
            )

        self._commit_file_repo.insert_many(
            commit_sha=commit.sha,
            entries=[(e.path, e.blob_sha, e.mode) for e in tree],
        )
        logger.info(
            "commit ingested sha=%s files=%d",
            commit.sha[:7],
            len(tree),
        )
        return tree
