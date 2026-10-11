"""Persist derived health metrics and observation-quality reports."""

from alembic import op
import sqlalchemy as sa

revision = "0005_metrics_quality"
down_revision = "0004_block_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "health_metrics",
        sa.Column("metric_id", sa.String(64), primary_key=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("p95_latency_ms", sa.Float(), nullable=False),
        sa.Column("latest_block_number", sa.Integer(), nullable=True),
        sa.Column("block_disagreement", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index("ix_health_metrics_chain_id", "health_metrics", ["chain_id"])
    op.create_index("ix_health_metrics_measured_at", "health_metrics", ["measured_at"])
    op.create_table(
        "observation_quality",
        sa.Column("report_id", sa.String(64), primary_key=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("gap_count", sa.Integer(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
    )
    op.create_index("ix_observation_quality_checked_at", "observation_quality", ["checked_at"])


def downgrade() -> None:
    op.drop_index("ix_observation_quality_checked_at", table_name="observation_quality")
    op.drop_table("observation_quality")
    op.drop_index("ix_health_metrics_measured_at", table_name="health_metrics")
    op.drop_index("ix_health_metrics_chain_id", table_name="health_metrics")
    op.drop_table("health_metrics")
