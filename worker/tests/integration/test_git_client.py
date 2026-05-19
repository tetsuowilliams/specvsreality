"""GitClient against repositories created on disk."""

from __future__ import annotations

import pytest

from fixtures.git_repos import (
    add_commit,
    init_repo_with_config,
    make_linear_three_commit_repo,
    rename_default_branch_to_main,
)
from specvsreality_worker.git import GitClient, GitClientError


def test_iter_commits_yields_oldest_first(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    client = GitClient(repo_path=path, repository_id=42)
    out = [r.sha for r in client.iter_commits(oldest_first=True)]
    assert out == shas


def test_iter_commits_carries_repository_id_and_parents(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    client = GitClient(repo_path=path, repository_id=7)
    records = list(client.iter_commits(oldest_first=True))
    assert all(r.repository_id == 7 for r in records)
    assert records[0].parent_shas == []
    assert [p.parent_sha for p in records[1].parent_shas] == [shas[0]]
    assert [p.parent_order for p in records[1].parent_shas] == [0]


def test_list_tree_returns_full_tree_at_each_commit(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    client = GitClient(repo_path=path, repository_id=1)
    paths_at_c1 = [e.path for e in client.list_tree(shas[0])]
    paths_at_c2 = [e.path for e in client.list_tree(shas[1])]
    paths_at_c3 = [e.path for e in client.list_tree(shas[2])]
    assert paths_at_c1 == ["README.md"]
    assert paths_at_c2 == ["README.md", "docs/feature.spec.md"]
    assert paths_at_c3 == ["README.md", "docs/feature.spec.md"]


def test_list_tree_unknown_commit_raises(tmp_path) -> None:
    path, _ = make_linear_three_commit_repo(tmp_path, use_main=True)
    client = GitClient(repo_path=path, repository_id=1)
    with pytest.raises(GitClientError, match="Unknown commit"):
        client.list_tree("0" * 40)


def test_read_blob_returns_bytes(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    client = GitClient(repo_path=path, repository_id=1)
    entries = {e.path: e for e in client.list_tree(shas[1])}
    spec_blob = entries["docs/feature.spec.md"].blob_sha
    assert client.read_blob(spec_blob) == b"# Spec\n"


def test_default_branch_falls_back_to_master(tmp_path) -> None:
    path = tmp_path / "r"
    path.mkdir()
    repo = init_repo_with_config(path)
    if repo.active_branch.name != "master":
        repo.git.branch("-M", "master")
    add_commit(repo, "c1", {"a.txt": "x"})
    client = GitClient(repo_path=path, repository_id=1)
    assert client.default_branch_ref() == "master"


def test_list_refs_returns_branches(tmp_path) -> None:
    path = tmp_path / "r"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)
    add_commit(repo, "init", {"a.txt": "1"})
    repo.create_tag("v1")
    client = GitClient(repo_path=path, repository_id=1)
    refs = client.list_refs()
    types = {(r.name, r.ref_type) for r in refs}
    assert ("main", "branch") in types
    assert ("v1", "tag") in types
