"""Create the initial append-only monitoring schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rpc_observations",
        sa.Column("observation_id", sa.String(length=64), primary_key=True),
        sa.Column("endpoint_name", sa.String(length=100), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("latest_block_number", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_rpc_observations_endpoint_name", "rpc_observations", ["endpoint_name"])
    op.create_index("ix_rpc_observations_chain_id", "rpc_observations", ["chain_id"])
    op.create_index("ix_rpc_observations_observed_at", "rpc_observations", ["observed_at"])

    op.create_table(
        "pool_events",
        sa.Column("event_id", sa.String(length=160), primary_key=True),
        sa.Column("pool_id", sa.String(length=120), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("block_hash", sa.String(length=100), nullable=False),
        sa.Column("transaction_hash", sa.String(length=100), nullable=False),
        sa.Column("log_index", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount0", sa.Float(), nullable=True),
        sa.Column("amount1", sa.Float(), nullable=True),
        sa.Column("reserve0", sa.Float(), nullable=True),
        sa.Column("reserve1", sa.Float(), nullable=True),
        sa.Column("sqrt_price_x96", sa.String(length=80), nullable=True),
        sa.Column("tick", sa.Integer(), nullable=True),
        sa.Column("active_liquidity", sa.String(length=80), nullable=True),
        sa.Column("tick_lower", sa.Integer(), nullable=True),
        sa.Column("tick_upper", sa.Integer(), nullable=True),
    )
    op.create_index("ix_pool_events_pool_id", "pool_events", ["pool_id"])
    op.create_index("ix_pool_events_chain_id", "pool_events", ["chain_id"])
    op.create_index("ix_pool_events_block_number", "pool_events", ["block_number"])
    op.create_index("ix_pool_events_event_type", "pool_events", ["event_type"])
    op.create_index("ix_pool_events_occurred_at", "pool_events", ["occurred_at"])

    op.create_table(
        "pool_cursors",
        sa.Column("pool_id", sa.String(length=120), primary_key=True),
        sa.Column("last_processed_block", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("pool_cursors")
    for index_name in (
        "ix_pool_events_occurred_at",
        "ix_pool_events_event_type",
        "ix_pool_events_block_number",
        "ix_pool_events_chain_id",
        "ix_pool_events_pool_id",
    ):
        op.drop_index(index_name, table_name="pool_events")
    op.drop_table("pool_events")
    for index_name in (
        "ix_rpc_observations_observed_at",
        "ix_rpc_observations_chain_id",
        "ix_rpc_observations_endpoint_name",
    ):
        op.drop_index(index_name, table_name="rpc_observations")
    op.drop_table("rpc_observations")
