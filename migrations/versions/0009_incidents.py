"""Persist incident lifecycle records and typed evidence."""

from alembic import op
import sqlalchemy as sa

revision = "0009_incidents"
down_revision = "0008_model_evaluations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(64), primary_key=True),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("anomaly_event_id", sa.String(64), nullable=False),
        sa.Column("anomaly_score_id", sa.String(64), nullable=True),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=True),
    )
    for name in ("chain_id", "created_at", "status", "severity", "anomaly_event_id", "anomaly_score_id", "fingerprint"):
        op.create_index(f"ix_incidents_{name}", "incidents", [name])

    op.create_table(
        "incident_evidence",
        sa.Column("evidence_id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(64), nullable=False),
        sa.Column("evidence_type", sa.String(40), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    for name in ("incident_id", "evidence_type", "source_id", "observed_at"):
        op.create_index(f"ix_incident_evidence_{name}", "incident_evidence", [name])

    op.create_table(
        "incident_status_changes",
        sa.Column("change_id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=False),
        sa.Column("to_status", sa.String(20), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
    )
    for name in ("incident_id", "changed_at"):
        op.create_index(f"ix_incident_status_changes_{name}", "incident_status_changes", [name])


def downgrade() -> None:
    for name in ("changed_at", "incident_id"):
        op.drop_index(f"ix_incident_status_changes_{name}", table_name="incident_status_changes")
    op.drop_table("incident_status_changes")
    for name in ("observed_at", "source_id", "evidence_type", "incident_id"):
        op.drop_index(f"ix_incident_evidence_{name}", table_name="incident_evidence")
    op.drop_table("incident_evidence")
    for name in ("fingerprint", "anomaly_score_id", "anomaly_event_id", "severity", "status", "created_at", "chain_id"):
        op.drop_index(f"ix_incidents_{name}", table_name="incidents")
    op.drop_table("incidents")
