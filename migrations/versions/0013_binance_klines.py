"""Store normalized Binance Spot candlesticks for the market-data MVP."""

from alembic import op
import sqlalchemy as sa

revision = "0013_binance_klines"
down_revision = "0012_historical_block_bigints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "binance_klines",
        sa.Column("symbol", sa.String(30), primary_key=True),
        sa.Column("interval", sa.String(10), primary_key=True),
        sa.Column("open_time", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("high_price", sa.Float(), nullable=False),
        sa.Column("low_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("quote_volume", sa.Float(), nullable=False),
        sa.Column("trade_count", sa.BigInteger(), nullable=False),
        sa.Column("taker_buy_volume", sa.Float(), nullable=False),
        sa.Column("taker_buy_quote_volume", sa.Float(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        if_not_exists=True,
    )
    for name in ("close_time", "collected_at", "source"):
        op.create_index(f"ix_binance_klines_{name}", "binance_klines", [name], if_not_exists=True)


def downgrade() -> None:
    for name in ("source", "collected_at", "close_time"):
        op.drop_index(f"ix_binance_klines_{name}", table_name="binance_klines")
    op.drop_table("binance_klines")
