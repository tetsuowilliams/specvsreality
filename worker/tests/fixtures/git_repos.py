"""Create real git repositories under a temporary path for tests."""

from __future__ import annotations

from pathlib import Path

from git import Repo


def init_repo_with_config(path: Path) -> Repo:
    repo = Repo.init(path)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "fixture")
        cw.set_value("user", "email", "fixture@example.com")
    return repo


def rename_default_branch_to_main(repo: Repo) -> None:
    if repo.active_branch.name != "main":
        repo.git.branch("-M", "main")


def add_commit(repo: Repo, message: str, files: dict[str, str]) -> str:
    """Write ``files`` relative to the working tree, stage, commit; return hexsha."""
    root = Path(repo.working_tree_dir or repo.git_dir)
    rels: list[str] = []
    for rel, content in files.items():
        normalized = rel.replace("\\", "/")
        p = root / normalized
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        rels.append(normalized)
    repo.index.add(rels)
    commit = repo.index.commit(message)
    return commit.hexsha


def make_linear_three_commit_repo(base: Path, *, use_main: bool = True) -> tuple[Path, list[str]]:
    """
    Build a repo with three commits on a linear history.

    c1: README.md
    c2: docs/feature.spec.md
    c3: README.md updated

    Returns (repo_path, [sha_c1, sha_c2, sha_c3]).
    """
    path = base / "repo"
    path.mkdir()
    repo = init_repo_with_config(path)
    if use_main:
        rename_default_branch_to_main(repo)

    shas: list[str] = []
    shas.append(add_commit(repo, "init", {"README.md": "hello\n"}))
    shas.append(add_commit(repo, "add spec", {"docs/feature.spec.md": "# Spec\n"}))
    shas.append(add_commit(repo, "touch readme", {"README.md": "hello world\n"}))
    return path, shas
