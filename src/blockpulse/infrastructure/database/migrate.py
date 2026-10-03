"""Command-line entry point for applying database migrations."""

from alembic import command
from alembic.config import Config


def main() -> None:
    """Apply all migrations to the configured database."""

    command.upgrade(Config("alembic.ini"), "head")
