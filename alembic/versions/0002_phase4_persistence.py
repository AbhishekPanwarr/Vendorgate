"""Phase 4: current_version pointer, run result JSON, run events, case docs."""

from alembic import op
import sqlalchemy as sa

revision = "0002_phase4_persistence"
down_revision = "0001_initial"


def _str(n):
    return sa.String(n)


def upgrade() -> None:
    with op.batch_alter_table("cases") as b:
        b.add_column(sa.Column("run_id", _str(64), nullable=True))
        b.add_column(sa.Column("requester", _str(256), server_default=""))
        b.add_column(sa.Column("submission_type", _str(32), server_default="NEW_VENDOR"))
        b.add_column(sa.Column("existing_vendor_id", _str(64), nullable=True))
        b.add_column(sa.Column("reason_codes", sa.JSON, nullable=True))
        b.add_column(sa.Column("current_version", sa.Integer, server_default="1"))
    with op.batch_alter_table("runs") as b:
        b.add_column(sa.Column("result", sa.JSON, nullable=True))
    with op.batch_alter_table("submission_versions") as b:
        b.create_index("ix_submission_versions_case_version", ["case_id", "version"], unique=True)
    with op.batch_alter_table("idempotency_keys") as b:
        b.add_column(sa.Column("response", sa.JSON, nullable=True))
    op.create_table(
        "run_events",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("run_id", _str(64)),
        sa.Column("seq", sa.Integer),
        sa.Column("type", _str(64)),
        sa.Column("data", sa.JSON),
    )
    op.create_table(
        "case_docs",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("run_id", _str(64)),
        sa.Column("doc_id", _str(64)),
        sa.Column("filename", _str(256)),
        sa.Column("sha256", _str(128)),
        sa.Column("data", sa.LargeBinary),
    )
    # 0001 created these as (id, payload) stubs; the app writes full rows.
    # No production rows can exist (in-memory era), so rebuild to model shape.
    for t in ("callbacks", "messages", "approvals", "resolutions", "clock_state", "adapter_faults"):
        op.drop_table(t)
    op.create_table(
        "callbacks",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("number_used", _str(64)),
        sa.Column("number_source", _str(64)),
        sa.Column("outcome", _str(64)),
        sa.Column("independent", sa.Boolean),
        sa.Column("actor", _str(64)),
        sa.Column("attested", sa.Boolean),
        sa.Column("at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "messages",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("run_id", _str(64)),
        sa.Column("audience", _str(32)),
        sa.Column("kind", _str(32)),
        sa.Column("subject", _str(512)),
        sa.Column("body", _str(8192)),
        sa.Column("items", sa.JSON),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "approvals",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("role", _str(64)),
        sa.Column("actor", _str(64)),
        sa.Column("action", _str(32)),
        sa.Column("note", _str(2048)),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "resolutions",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("finding_key", _str(256)),
        sa.Column("action", _str(32)),
        sa.Column("role", _str(64)),
        sa.Column("actor", _str(64)),
        sa.Column("note", _str(2048)),
        sa.Column("at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "clock_state",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("virtual_now", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "adapter_faults",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("adapter", _str(64)),
        sa.Column("mode", _str(32)),
        sa.Column("until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for t in ("adapter_faults", "clock_state", "resolutions", "approvals", "messages", "callbacks"):
        op.drop_table(t)
        op.create_table(
            t,
            sa.Column("id", _str(64), primary_key=True),
            sa.Column("payload", sa.JSON, nullable=True),
        )
    op.drop_table("case_docs")
    op.drop_table("run_events")
    with op.batch_alter_table("submission_versions") as b:
        b.drop_index("ix_submission_versions_case_version")
    with op.batch_alter_table("runs") as b:
        b.drop_column("result")
    with op.batch_alter_table("cases") as b:
        b.drop_column("current_version")
        b.drop_column("reason_codes")
        b.drop_column("existing_vendor_id")
        b.drop_column("submission_type")
        b.drop_column("requester")
        b.drop_column("run_id")
