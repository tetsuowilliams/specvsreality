"""Tests for `ArtifactCandidateRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_artifact_candidate_repo
from tests.fixtures.graph import (
    add_artifact,
    add_artifact_version,
    add_spec,
    add_spec_version,
)


def test_add_and_get_by_id(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    spec = add_spec(db_session, paper_id="specs/candidate", repo_id=git_repo_id)
    version = add_spec_version(db_session, spec_id=spec.id, commit_id=commit_id)
    art = add_artifact(db_session, filepath="src/f.py")
    av = add_artifact_version(db_session, artifact_id=art.id, commit_id=commit_id)

    repo = create_artifact_candidate_repo(db_session)
    row = repo.add(
        spec_version_id=version.id,
        artifact_version_id=av.id,
        reasoning="looks relevant",
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.spec_version_id == version.id
    assert loaded.artifact_version_id == av.id
    assert loaded.reasoning == "looks relevant"


def test_list_for_spec_version_returns_candidates_in_id_order(
    db_session: Session, git_repo_id: int, commit_id: int
) -> None:
    spec = add_spec(db_session, paper_id="specs/multi", repo_id=git_repo_id)
    version = add_spec_version(db_session, spec_id=spec.id, commit_id=commit_id)
    art_a = add_artifact(db_session, filepath="src/a.py")
    art_b = add_artifact(db_session, filepath="src/b.py")
    av_a = add_artifact_version(db_session, artifact_id=art_a.id, commit_id=commit_id)
    av_b = add_artifact_version(db_session, artifact_id=art_b.id, commit_id=commit_id)

    repo = create_artifact_candidate_repo(db_session)
    first = repo.add(
        spec_version_id=version.id,
        artifact_version_id=av_a.id,
        reasoning="first",
    )
    second = repo.add(
        spec_version_id=version.id,
        artifact_version_id=av_b.id,
        reasoning="second",
    )

    rows = repo.list_for_spec_version(spec_version_id=version.id)
    assert [r.id for r in rows] == [first.id, second.id]
    assert [r.reasoning for r in rows] == ["first", "second"]


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_artifact_candidate_repo(db_session)
    assert repo.get_by_id(999_999_999) is None
