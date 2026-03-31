"""GitAdapter against repositories created on disk."""

from __future__ import annotations

import pytest
from git import Repo

from fixtures.git_repos import (
    add_commit,
    init_repo_with_config,
    make_linear_three_commit_repo,
    rename_default_branch_to_main,
)
from specvsreality_worker.git_adapter import GitAdapter, GitAdapterError


def test_default_branch_prefers_main(tmp_path) -> None:
    path, _ = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert adapter.default_branch_ref() == "main"


def test_default_branch_falls_back_to_master(tmp_path) -> None:
    path = tmp_path / "r"
    path.mkdir()
    repo = init_repo_with_config(path)
    if repo.active_branch.name != "master":
        repo.git.branch("-M", "master")
    add_commit(repo, "c1", {"a.txt": "x"})
    adapter = GitAdapter(path)
    assert adapter.default_branch_ref() == "master"


def test_iter_commits_since_all_chronological(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert list(adapter.iter_commits_since(None)) == shas


def test_iter_commits_since_exclusive_of_ancestor(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert list(adapter.iter_commits_since(shas[0])) == shas[1:]
    assert list(adapter.iter_commits_since(shas[1])) == shas[2:]


def test_iter_commits_since_at_tip_empty(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert list(adapter.iter_commits_since(shas[2])) == []


def test_changed_paths_root_commit_lists_all_blobs(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert adapter.changed_paths(shas[0]) == ["README.md"]


def test_changed_paths_middle_commit(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert adapter.changed_paths(shas[1]) == ["docs/feature.spec.md"]


def test_changed_paths_modification_commit(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert adapter.changed_paths(shas[2]) == ["README.md"]


def test_file_at_commit_reads_utf8_text(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    assert adapter.file_at_commit(shas[1], "docs/feature.spec.md") == "# Spec\n"


def test_file_at_commit_missing_raises(tmp_path) -> None:
    path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    with pytest.raises(GitAdapterError, match="No path"):
        adapter.file_at_commit(shas[1], "nope.txt")


def test_file_at_commit_directory_not_blob_raises(tmp_path) -> None:
    path = tmp_path / "r"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)
    add_commit(repo, "c1", {"docs/inside.txt": "x"})
    sha = repo.head.commit.hexsha
    adapter = GitAdapter(path)
    with pytest.raises(GitAdapterError, match="Not a file"):
        adapter.file_at_commit(sha, "docs")


def test_file_at_commit_unknown_commit_raises(tmp_path) -> None:
    path, _ = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    with pytest.raises(GitAdapterError, match="Unknown commit"):
        adapter.file_at_commit("0" * 40, "README.md")


def test_changed_paths_unknown_commit_raises(tmp_path) -> None:
    path, _ = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    with pytest.raises(GitAdapterError, match="Unknown commit"):
        adapter.changed_paths("0" * 40)


def test_iter_commits_since_invalid_range_raises(tmp_path) -> None:
    path, _ = make_linear_three_commit_repo(tmp_path, use_main=True)
    adapter = GitAdapter(path)
    with pytest.raises(GitAdapterError, match="Invalid revision"):
        list(adapter.iter_commits_since("not-a-real-sha"))


def test_repo_neither_main_nor_master_raises(tmp_path) -> None:
    path = tmp_path / "empty_heads"
    path.mkdir()
    repo = Repo.init(path)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "x")
        cw.set_value("user", "email", "x@x")
    repo.git.checkout("--orphan", "orph")
    (path / "f.txt").write_text("a", encoding="utf-8")
    repo.index.add(["f.txt"])
    repo.index.commit("only")
    repo.delete_head("main", force=True) if "main" in {h.name for h in repo.heads} else None
    for h in list(repo.heads):
        if h.name != "orph":
            repo.delete_head(h, force=True)
    repo.git.branch("-m", "orph", "develop")
    adapter = GitAdapter(path)
    with pytest.raises(GitAdapterError, match="neither main nor master"):
        adapter.default_branch_ref()
