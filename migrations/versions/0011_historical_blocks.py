"""Store sampled historical block facts and restart cursors."""

from alembic import op
import sqlalchemy as sa

revision = "0011_historical_blocks"
down_revision = "0010_ai_interaction_audits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historical_blocks",
        sa.Column("block_id", sa.String(160), primary_key=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("block_hash", sa.String(100), nullable=False),
        sa.Column("parent_hash", sa.String(100), nullable=True),
        sa.Column("block_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transaction_count", sa.Integer(), nullable=False),
        sa.Column("gas_used", sa.Integer(), nullable=True),
        sa.Column("gas_limit", sa.Integer(), nullable=True),
        sa.Column("base_fee_per_gas", sa.Integer(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        if_not_exists=True,
    )
    for name in ("chain_id", "block_number", "block_timestamp", "collected_at", "source"):
        op.create_index(f"ix_historical_blocks_{name}", "historical_blocks", [name], if_not_exists=True)

    op.create_table(
        "historical_backfill_cursors",
        sa.Column("backfill_key", sa.String(160), primary_key=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_minutes", sa.Integer(), nullable=False),
        sa.Column("last_block_number", sa.Integer(), nullable=False),
        if_not_exists=True,
    )
    op.create_index(
        "ix_historical_backfill_cursors_chain_id",
        "historical_backfill_cursors",
        ["chain_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_historical_backfill_cursors_chain_id", table_name="historical_backfill_cursors")
    op.drop_table("historical_backfill_cursors")
    for name in ("source", "collected_at", "block_timestamp", "block_number", "chain_id"):
        op.drop_index(f"ix_historical_blocks_{name}", table_name="historical_blocks")
    op.drop_table("historical_blocks")
