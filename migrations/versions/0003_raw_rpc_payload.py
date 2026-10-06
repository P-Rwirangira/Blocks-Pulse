"""Preserve raw JSON-RPC response payloads for evidence and replay."""

from alembic import op
import sqlalchemy as sa

revision = "0003_raw_rpc_payload"
down_revision = "0002_observation_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rpc_observations",
        sa.Column("raw_payload", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rpc_observations", "raw_payload")
