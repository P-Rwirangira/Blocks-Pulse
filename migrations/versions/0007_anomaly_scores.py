"""Persist deterministic and learned anomaly scores."""

from alembic import op
import sqlalchemy as sa

revision = "0007_anomaly_scores"
down_revision = "0006_feature_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anomaly_scores",
        sa.Column("anomaly_id", sa.String(64), primary_key=True),
        sa.Column("detector_name", sa.String(80), nullable=False),
        sa.Column("detector_version", sa.String(40), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.String(160), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("drivers", sa.JSON(), nullable=False),
        sa.Column("feature_ids", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False),
    )
    for name, column in (
        ("detector_name", "detector_name"),
        ("detector_version", "detector_version"),
        ("entity_type", "entity_type"),
        ("entity_id", "entity_id"),
        ("chain_id", "chain_id"),
        ("detected_at", "detected_at"),
    ):
        op.create_index(f"ix_anomaly_scores_{name}", "anomaly_scores", [column])


def downgrade() -> None:
    for name in (
        "detected_at",
        "chain_id",
        "entity_id",
        "entity_type",
        "detector_version",
        "detector_name",
    ):
        op.drop_index(f"ix_anomaly_scores_{name}", table_name="anomaly_scores")
    op.drop_table("anomaly_scores")
