"""Persist privacy-safe AI interaction audit metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0010_ai_interaction_audits"
down_revision = "0009_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_interaction_audits",
        sa.Column("interaction_id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("tool_calls", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("validation_state", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("incident_id", "model_version", "validation_state", "created_at"):
        op.create_index(f"ix_ai_interaction_audits_{name}", "ai_interaction_audits", [name])


def downgrade() -> None:
    for name in ("created_at", "validation_state", "model_version", "incident_id"):
        op.drop_index(f"ix_ai_interaction_audits_{name}", table_name="ai_interaction_audits")
    op.drop_table("ai_interaction_audits")
