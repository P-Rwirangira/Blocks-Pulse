"""Allow historical EVM numeric fields to exceed 32-bit integer range."""

from alembic import op
import sqlalchemy as sa

revision = "0012_historical_block_bigints"
down_revision = "0011_historical_blocks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("historical_blocks") as batch:
        for column in ("block_number", "transaction_count", "gas_used", "gas_limit", "base_fee_per_gas"):
            batch.alter_column(column, existing_type=sa.Integer(), type_=sa.BigInteger())
    with op.batch_alter_table("historical_backfill_cursors") as batch:
        batch.alter_column("last_block_number", existing_type=sa.Integer(), type_=sa.BigInteger())


def downgrade() -> None:
    with op.batch_alter_table("historical_blocks") as batch:
        for column in ("block_number", "transaction_count", "gas_used", "gas_limit", "base_fee_per_gas"):
            batch.alter_column(column, existing_type=sa.BigInteger(), type_=sa.Integer())
    with op.batch_alter_table("historical_backfill_cursors") as batch:
        batch.alter_column("last_block_number", existing_type=sa.BigInteger(), type_=sa.Integer())
