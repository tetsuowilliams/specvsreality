"""Unit tests for commit-scoped repository tools."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fixtures.git_repos import add_commit, init_repo_with_config, rename_default_branch_to_main
from specvsreality_worker.core.spec_detection import ArtifactType  # noqa: F401
from specvsreality_worker.git_adapter import GitAdapter
from specvsreality_worker.agents.artifact_candidate_agent.deps import CommitToolDeps
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.agents.artifact_candidate_agent.repository_tools import (
    find_files,
    list_directory,
    read_file,
    search_text,
)
from specvsreality_worker.agents.artifact_candidate_agent.tool_cache import CommitToolCache


def _make_repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)
    sha = add_commit(
        repo,
        "initial",
        {
            "src/main.py": "def hello():\n    return 'hello'\n",
            "src/util.py": "def helper():\n    return 42\n",
            "README.md": "hello world\n",
            ".cursor/rules.md": "ignore me\n",
        },
    )
    adapter = GitAdapter(path)
    return adapter, sha


def test_find_files_matches_glob(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    assert find_files(deps, "src/**/*.py") == ["src/main.py", "src/util.py"]
    assert find_files(deps, "README.md") == ["README.md"]


def test_list_directory_root_and_nested(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    assert list_directory(deps, ".") == ["README.md", "src/"]
    assert list_directory(deps, "src") == ["src/main.py", "src/util.py"]


def test_read_file_full_and_range(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    assert read_file(deps, "src/main.py") == "def hello():\n    return 'hello'\n"
    assert read_file(deps, "src/main.py", start_line=2, end_line=2) == "2:     return 'hello'"


def test_search_text_finds_matches(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    matches = search_text(deps, pattern=r"def helper", path="src", file_glob="*.py")
    assert matches == ["src/util.py:1:def helper():"]


def test_search_text_invalid_regex_returns_error(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    assert search_text(deps, pattern="[") == ["error: invalid regex: unterminated character set at position 0"]


def test_search_text_at_repo_root_without_glob_rejected(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        label="FR-3",
    )

    result = search_text(deps, pattern="hello", path=".")
    assert len(result) == 1
    assert result[0].startswith("error:")


def test_search_text_at_repo_root_uses_path_globs_hints(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        path_globs=("src/**/*.py",),
    )

    matches = search_text(deps, pattern=r"def hello", path=".")
    assert any("src/main.py" in line for line in matches)


def test_search_text_caps_files_scanned(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(artifact_candidate_agent_search_max_files=1),
    )

    matches = search_text(deps, pattern=".", path="src", file_glob="*.py")
    assert any(line.startswith("warning: scanned 1 of") for line in matches)


def test_read_file_rejects_binary_suffix(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    result = read_file(deps, "docs/report.pdf")
    assert result.startswith("error:")


def test_read_file_rejects_oversized_without_line_range(tmp_path) -> None:
    path = tmp_path / "repo"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)
    sha = add_commit(repo, "big", {"big.txt": "x" * 500})
    adapter = GitAdapter(path)
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(artifact_candidate_agent_read_max_bytes=100),
    )

    result = read_file(deps, "big.txt")
    assert result.startswith("error:")
    assert "bytes" in result


def test_read_file_line_range_uses_streaming(tmp_path) -> None:
    path = tmp_path / "repo"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)
    sha = add_commit(
        repo,
        "big",
        {"big.txt": "\n".join(f"line {index}" for index in range(1, 501))},
    )
    adapter = GitAdapter(path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    result = read_file(deps, "big.txt", start_line=10, end_line=20)
    assert "10: line 10" in result
    assert "20: line 20" in result
    assert "line 500" not in result


def test_read_file_rejects_wide_line_span(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(artifact_candidate_agent_read_max_line_span=50),
    )

    result = read_file(deps, "src/main.py", start_line=1, end_line=260)
    assert result.startswith("error:")
    assert "limit 50" in result


def test_read_file_without_cache_hits_git_each_call(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(git_adapter=adapter, commit_sha=sha, settings=WorkerSettings())

    with patch.object(adapter, "file_at_commit", wraps=adapter.file_at_commit) as mock_file:
        read_file(deps, "src/main.py")
        read_file(deps, "src/main.py")
        assert mock_file.call_count == 2


def test_read_file_tool_cache_reuses_full_file_read(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    cache = CommitToolCache()
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        tool_cache=cache,
    )

    with patch.object(adapter, "file_at_commit", wraps=adapter.file_at_commit) as mock_file:
        first = read_file(deps, "src/main.py")
        second = read_file(deps, "src/main.py")
        assert mock_file.call_count == 1
    assert first == second


def test_read_file_tool_cache_distinguishes_line_ranges(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    cache = CommitToolCache()
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        tool_cache=cache,
    )

    with patch.object(
        adapter,
        "file_lines_at_commit",
        wraps=adapter.file_lines_at_commit,
    ) as mock_lines:
        read_file(deps, "src/main.py", start_line=1, end_line=1)
        read_file(deps, "src/main.py", start_line=2, end_line=2)
        assert mock_lines.call_count == 2


def test_read_file_tool_cache_logs_cache_hit(tmp_path, caplog) -> None:
    import logging

    adapter, sha = _make_repo(tmp_path)
    cache = CommitToolCache()
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        tool_cache=cache,
    )
    caplog.set_level(logging.INFO)

    read_file(deps, "src/main.py")
    read_file(deps, "src/main.py")

    assert any("tool read_file cache_hit" in record.message for record in caplog.records)


def test_find_files_tool_cache_reuses_result(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    cache = CommitToolCache()
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        tool_cache=cache,
    )

    with patch.object(
        adapter,
        "list_files_at_commit",
        wraps=adapter.list_files_at_commit,
    ) as mock_list:
        assert find_files(deps, "src/**/*.py") == ["src/main.py", "src/util.py"]
        assert find_files(deps, "src/**/*.py") == ["src/main.py", "src/util.py"]
        assert mock_list.call_count == 1


def test_search_text_tool_cache_reuses_result(tmp_path) -> None:
    adapter, sha = _make_repo(tmp_path)
    cache = CommitToolCache()
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        tool_cache=cache,
    )

    with patch.object(adapter, "file_at_commit", wraps=adapter.file_at_commit) as mock_file:
        first = search_text(deps, pattern=r"def helper", path="src", file_glob="*.py")
        reads_after_first = mock_file.call_count
        second = search_text(deps, pattern=r"def helper", path="src", file_glob="*.py")
        assert mock_file.call_count == reads_after_first
    assert first == second


def test_read_file_logs_start_before_hang_risk(tmp_path, monkeypatch, caplog) -> None:
    import logging

    adapter, sha = _make_repo(tmp_path)
    deps = CommitToolDeps(
        git_adapter=adapter,
        commit_sha=sha,
        settings=WorkerSettings(),
        label="FR-2",
    )
    caplog.set_level(logging.INFO)

    read_file(deps, "src/main.py", start_line=1, end_line=2)

    assert any("tool read_file start" in record.message for record in caplog.records)
