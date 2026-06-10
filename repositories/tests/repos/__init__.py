"""Per-repository integration tests.

All repo tests use Postgres via testcontainers (see ``tests/conftest.py``).
Docker must be running. Use the ``db_session`` fixture for transactional isolation.
"""
