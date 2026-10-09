import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect


POSTGRES_URL = os.getenv("BLOCKPULSE_TEST_POSTGRES_URL")


@pytest.mark.skipif(
    not POSTGRES_URL,
    reason="set BLOCKPULSE_TEST_POSTGRES_URL to run PostgreSQL migration coverage",
)
def test_postgres_migrations_upgrade_and_rollback() -> None:
    """Exercise the complete migration chain against a dedicated PostgreSQL database."""

    root = Path(__file__).parents[2]
    environment = os.environ.copy()
    environment["BLOCKPULSE_DATABASE_URL"] = POSTGRES_URL or ""

    def run(*arguments: str) -> None:
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=root,
            env=environment,
            check=True,
        )

    run("upgrade", "head")
    engine = create_engine(POSTGRES_URL.replace("+async", ""))
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"rpc_observations", "pool_events", "pool_cursors", "alembic_version"} <= tables
        run("downgrade", "base")
        assert "rpc_observations" not in set(inspect(engine).get_table_names())
    finally:
        run("upgrade", "head")
        engine.dispose()
