"""Persist individual RPC retry attempts."""

from alembic import op
import sqlalchemy as sa

revision = "0002_observation_attempts"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rpc_observations",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("rpc_observations", "attempt")
