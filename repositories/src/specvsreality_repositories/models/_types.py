"""Cross-dialect column types reused by ORM models.

The new schema uses ``BIGINT`` primary keys to give us headroom in production,
but SQLite (used by the API service tests for fast smoke checks) does not
support autoincrement on ``BIGINT``. ``BigIntPk`` falls back to ``INTEGER`` on
SQLite while remaining ``BIGINT`` everywhere else.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer

BigIntPk = BigInteger().with_variant(Integer, "sqlite")
