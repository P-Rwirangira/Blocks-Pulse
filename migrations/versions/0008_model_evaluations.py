"""Persist detector evaluation reports and parameters."""

from alembic import op
import sqlalchemy as sa

revision = "0008_model_evaluations"
down_revision = "0007_anomaly_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_evaluations",
        sa.Column("run_id", sa.String(64), primary_key=True),
        sa.Column("detector_name", sa.String(80), nullable=False),
        sa.Column("detector_version", sa.String(40), nullable=False),
        sa.Column("feature_version", sa.String(40), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_count", sa.Integer(), nullable=False),
        sa.Column("validation_count", sa.Integer(), nullable=False),
        sa.Column("test_count", sa.Integer(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("false_positive_rate", sa.Float(), nullable=False),
        sa.Column("detection_delay_seconds", sa.Float(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
    )
    for name in ("detector_name", "detector_version", "feature_version", "evaluated_at"):
        op.create_index(f"ix_model_evaluations_{name}", "model_evaluations", [name])


def downgrade() -> None:
    for name in ("evaluated_at", "feature_version", "detector_version", "detector_name"):
        op.drop_index(f"ix_model_evaluations_{name}", table_name="model_evaluations")
    op.drop_table("model_evaluations")
