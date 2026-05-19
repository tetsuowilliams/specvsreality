"""Tests for ``SpecRepo``."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import SpecRepo


def test_get_or_create_returns_existing(db_session: Session, repository_id: int) -> None:
    repo = SpecRepo(db_session)
    first = repo.get_or_create(
        repository_id=repository_id,
        name="auth",
        spec_path="specs/auth/spec.md",
        plan_path="specs/auth/plan.md",
        tasks_path="specs/auth/tasks.md",
    )
    second = repo.get_or_create(
        repository_id=repository_id,
        name="auth",
        spec_path="specs/auth/spec.md",
        plan_path="specs/auth/plan.md",
        tasks_path="specs/auth/tasks.md",
    )

    assert first.id == second.id


def test_get_or_create_refreshes_paths_when_spec_moves(
    db_session: Session, repository_id: int
) -> None:
    """Folder renames change tree paths; the same ``name`` should follow detection."""
    repo = SpecRepo(db_session)
    first = repo.get_or_create(
        repository_id=repository_id,
        name="001-count-pdfs-in-directory",
        spec_path="test_speckit/specs/001-count-pdfs-in-directory/spec.md",
        plan_path="test_speckit/specs/001-count-pdfs-in-directory/plan.md",
        tasks_path="test_speckit/specs/001-count-pdfs-in-directory/tasks.md",
    )
    second = repo.get_or_create(
        repository_id=repository_id,
        name="001-count-pdfs-in-directory",
        spec_path="specs/001-count-pdfs-in-directory/spec.md",
        plan_path="specs/001-count-pdfs-in-directory/plan.md",
        tasks_path="specs/001-count-pdfs-in-directory/tasks.md",
    )

    assert first.id == second.id
    assert second.spec_path == "specs/001-count-pdfs-in-directory/spec.md"
    assert second.plan_path == "specs/001-count-pdfs-in-directory/plan.md"
    assert second.tasks_path == "specs/001-count-pdfs-in-directory/tasks.md"


def test_list_for_repo_orders_by_name(db_session: Session, repository_id: int) -> None:
    repo = SpecRepo(db_session)
    repo.get_or_create(
        repository_id=repository_id,
        name="b",
        spec_path="specs/b/spec.md",
        plan_path="specs/b/plan.md",
        tasks_path="specs/b/tasks.md",
    )
    repo.get_or_create(
        repository_id=repository_id,
        name="a",
        spec_path="specs/a/spec.md",
        plan_path="specs/a/plan.md",
        tasks_path="specs/a/tasks.md",
    )

    rows = repo.list_for_repo(repository_id=repository_id)
    assert [r.name for r in rows] == ["a", "b"]
