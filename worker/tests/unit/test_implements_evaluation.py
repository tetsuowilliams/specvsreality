"""Unit tests for async implements evaluation batching."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_worker.agents.implements_agent.models import SpecItemEvaluation
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.implements_evaluation import ImplementsEvaluation
from specvsreality_worker.core.spec_merge import SpecWork


def _spec_item(item_id: int) -> SpecItem:
    return SpecItem(
        id=item_id,
        spec_version_id=1,
        local_key=f"item-{item_id}",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        importance=SpecItemImportance.MUST,
        text=f"Requirement {item_id}",
        success_criteria=[],
        failure_criteria=[],
        highlight_spans=[],
    )


def _evaluation(item_id: int) -> SpecItemEvaluation:
    return SpecItemEvaluation(
        spec_item_id=item_id,
        summary=f"eval {item_id}",
        implemented=True,
        gaps=[],
        confidence=0.9,
        implemented_by=[],
    )


def test_evaluate_runs_batches_concurrently() -> None:
    settings = WorkerSettings(implements_agent_batch_size=10, implements_agent_concurrent_batches=10)
    agent = MagicMock()
    in_flight = 0
    max_in_flight = 0
    batch_sizes: list[int] = []

    async def evaluate_batch(**kwargs: object) -> list[SpecItemEvaluation]:
        nonlocal in_flight, max_in_flight
        spec_items = kwargs["spec_items"]
        batch_sizes.append(len(spec_items))
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return [_evaluation(item.spec_item_id) for item in spec_items]

    agent.evaluate_batch = AsyncMock(side_effect=evaluate_batch)

    implementation_repo = MagicMock()
    implementation_repo.upsert_evaluation.return_value = MagicMock(id=1)

    evaluation = ImplementsEvaluation(
        implements_agent=agent,
        implementation_at_commit_repo=implementation_repo,
        implements_repo=MagicMock(),
        artifact_version_repo=MagicMock(),
        settings=settings,
    )

    work = SpecWork(
        spec_version=SpecVersion(id=1, spec_id=1, commit_id=1, status="active"),
        spec_items=[_spec_item(item_id) for item_id in range(1, 26)],
        spec_label="specs/demo",
        spec_md="# Demo",
        tasks_md=None,
        plan_md=None,
    )
    commit = CommitContext(
        repo_id=1,
        commit_id=1,
        commit_sha="abc123",
        commit_datetime=None,
        commit_message="test",
    )

    evaluation.evaluate(commit=commit, work=work, candidates=[])

    assert batch_sizes == [10, 10, 5]
    assert max_in_flight == 3
    assert agent.evaluate_batch.await_count == 3
    assert implementation_repo.upsert_evaluation.call_count == 25
