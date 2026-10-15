"""Persist versioned ML feature snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0006_feature_snapshots"
down_revision = "0005_metrics_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_snapshots",
        sa.Column("feature_id", sa.String(64), primary_key=True),
        sa.Column("feature_name", sa.String(100), nullable=False),
        sa.Column("feature_version", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(160), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source_observation_ids", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False),
    )
    op.create_index("ix_feature_snapshots_feature_name", "feature_snapshots", ["feature_name"])
    op.create_index("ix_feature_snapshots_feature_version", "feature_snapshots", ["feature_version"])
    op.create_index("ix_feature_snapshots_entity_type", "feature_snapshots", ["entity_type"])
    op.create_index("ix_feature_snapshots_entity_id", "feature_snapshots", ["entity_id"])
    op.create_index("ix_feature_snapshots_chain_id", "feature_snapshots", ["chain_id"])
    op.create_index("ix_feature_snapshots_measured_at", "feature_snapshots", ["measured_at"])


def downgrade() -> None:
    for index_name in (
        "ix_feature_snapshots_measured_at",
        "ix_feature_snapshots_chain_id",
        "ix_feature_snapshots_entity_id",
        "ix_feature_snapshots_entity_type",
        "ix_feature_snapshots_feature_version",
        "ix_feature_snapshots_feature_name",
    ):
        op.drop_index(index_name, table_name="feature_snapshots")
    op.drop_table("feature_snapshots")
