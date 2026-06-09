"""Repository access for spec items."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.models.spec_item import SpecItem


class SpecItemRepo:
    """Read/write access for ``spec_item`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, item_id: int) -> SpecItem | None:
        return self._session.get(SpecItem, item_id)

    def list_for_spec_version(self, *, spec_version_id: int) -> list[SpecItem]:
        stmt = (
            select(SpecItem)
            .where(SpecItem.spec_version_id == spec_version_id)
            .order_by(SpecItem.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def add(
        self,
        *,
        spec_version_id: int,
        local_key: str,
        item_type: SpecItemType,
        text: str,
        source_quote: str,
        importance: SpecItemImportance,
        success_criteria: Sequence[str],
        failure_criteria: Sequence[str],
        highlight_spans: dict | None = None,
    ) -> SpecItem:
        row = SpecItem(
            spec_version_id=spec_version_id,
            local_key=local_key,
            item_type=item_type,
            text=text,
            source_quote=source_quote,
            importance=importance,
            success_criteria=list(success_criteria),
            failure_criteria=list(failure_criteria),
            highlight_spans=highlight_spans,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_spec_item_repo(session: Session) -> SpecItemRepo:
    return SpecItemRepo(session)
