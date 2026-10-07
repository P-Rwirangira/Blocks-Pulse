"""Store block hashes needed for continuity and reorganization checks."""

from alembic import op
import sqlalchemy as sa

revision = "0004_block_identity"
down_revision = "0003_raw_rpc_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rpc_observations", sa.Column("latest_block_hash", sa.String(100)))
    op.add_column("rpc_observations", sa.Column("latest_parent_hash", sa.String(100)))


def downgrade() -> None:
    op.drop_column("rpc_observations", "latest_parent_hash")
    op.drop_column("rpc_observations", "latest_block_hash")
