"""Reusable builders for spec / artifact graph test data."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.models.git_repo import GitRepo
from specvsreality_repositories.models.spec import Spec
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
    create_git_repo_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

DEFAULT_COMMIT_DT = datetime(2026, 1, 15, tzinfo=UTC)


def add_git_repo(
    session: Session,
    *,
    name: str = "repo",
    url: str = "https://example.test/repo.git",
    cursor_position: str = "a" * 40,
    location: str = "/tmp/repo",
) -> GitRepo:
    return create_git_repo_repo(session).add(
        name=name,
        url=url,
        cursor_position=cursor_position,
        location=location,
    )


def add_commit(
    session: Session,
    *,
    repo_id: int,
    commit_sha: str,
    commit_message: str = "commit message",
    committed_at: datetime = DEFAULT_COMMIT_DT,
) -> Commit:
    return create_commit_repo(session).get_or_create(
        repo_id=repo_id,
        commit_sha=commit_sha,
        commit_message=commit_message,
        committed_at=committed_at,
    )


def add_spec(
    session: Session,
    *,
    paper_id: str,
    repo_id: int,
) -> Spec:
    return create_spec_repo(session).add(paper_id=paper_id, repo_id=repo_id)


def add_spec_version(
    session: Session,
    *,
    spec_id: int,
    commit_id: int,
    title: str = "Title",
    summary: str = "Summary",
    spec_md: str = "# S",
    tasks_md: str | None = "- T",
    plan_md: str | None = "P",
    created_at: datetime = DEFAULT_COMMIT_DT,
    status: VersionStatus = VersionStatus.ACTIVE,
) -> SpecVersion:
    return create_spec_version_repo(session).add(
        spec_id=spec_id,
        commit_id=commit_id,
        title=title,
        summary=summary,
        spec_md=spec_md,
        tasks_md=tasks_md,
        plan_md=plan_md,
        created_at=created_at,
        status=status,
    )


def add_spec_item(
    session: Session,
    *,
    spec_version_id: int,
    local_key: str = "FR-1",
    item_type: SpecItemType = SpecItemType.FUNCTIONAL_BEHAVIOR,
    text: str = "do thing",
    source_quote: str = "thing",
    importance: SpecItemImportance = SpecItemImportance.MUST,
    success_criteria: list[str] | None = None,
    failure_criteria: list[str] | None = None,
) -> SpecItem:
    return create_spec_item_repo(session).add(
        spec_version_id=spec_version_id,
        local_key=local_key,
        item_type=item_type,
        text=text,
        source_quote=source_quote,
        importance=importance,
        success_criteria=success_criteria or ["works"],
        failure_criteria=failure_criteria or ["broken"],
    )


def add_artifact(session: Session, *, filepath: str) -> Artifact:
    return create_artifact_repo(session).add(filepath=filepath)


def add_artifact_version(
    session: Session,
    *,
    artifact_id: int,
    commit_id: int,
    status: str = "active",
    file_content: str = "x = 1",
) -> ArtifactVersion:
    return create_artifact_version_repo(session).add(
        artifact_id=artifact_id,
        commit_id=commit_id,
        status=status,
        file_content=file_content,
    )
