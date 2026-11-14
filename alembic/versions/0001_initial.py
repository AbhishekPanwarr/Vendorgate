"""Initial schema — frozen; later phases add migrations forward, never edit this."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None


def _str(n):
    return sa.String(n)


TABLES = [
    "cases",
    "submission_versions",
    "documents",
    "runs",
    "claims",
    "findings",
    "decisions",
    "check_cache",
    "case_events",
    "approvals",
    "resolutions",
    "callbacks",
    "llm_calls",
    "messages",
    "vendors",
    "vendor_bank_accounts",
    "erp_outbox",
    "eval_runs",
    "eval_case_results",
    "clock_state",
    "adapter_faults",
    "idempotency_keys",
]


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("vendor_id", _str(64)),
        sa.Column("type", _str(32)),
        sa.Column("status", _str(32)),
        sa.Column("awaiting", sa.JSON),
        sa.Column("tier", _str(32)),
        sa.Column("score", sa.Float),
        sa.Column("attempt_count", sa.Integer),
        sa.Column("payments_blocked", sa.Boolean),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", _str(32)),
    )
    op.create_table(
        "submission_versions",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("version", sa.Integer),
        sa.Column("payload", sa.JSON),
        sa.Column("payload_hash", _str(128)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", _str(64)),
    )
    op.create_table(
        "documents",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("submission_version_id", _str(64)),
        sa.Column("doc_type", _str(32)),
        sa.Column("filename", _str(256)),
        sa.Column("sha256", _str(128)),
        sa.Column("path", _str(512)),
        sa.Column("pages", sa.Integer),
        sa.Column("text_layer", sa.Boolean),
        sa.Column("extracted", sa.JSON),
    )
    op.create_table(
        "runs",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("submission_version_id", _str(64)),
        sa.Column("mode", _str(16)),
        sa.Column("policy_version", _str(128)),
        sa.Column("llm_mode", _str(16)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timings", sa.JSON),
        sa.Column("cache_hits", sa.Integer),
        sa.Column("cache_misses", sa.Integer),
        sa.Column("llm_tokens", sa.Integer),
        sa.Column("llm_cost_usd", sa.Float),
    )
    op.create_table(
        "claims",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("run_id", _str(64)),
        sa.Column("path", _str(256)),
        sa.Column("raw", _str(1024), nullable=True),
        sa.Column("value", _str(1024), nullable=True),
        sa.Column("source", _str(32)),
        sa.Column("doc_id", _str(64), nullable=True),
        sa.Column("page", sa.Integer, nullable=True),
        sa.Column("quote", _str(2048), nullable=True),
        sa.Column("confidence", sa.Float),
    )
    op.create_table(
        "findings",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("run_id", _str(64)),
        sa.Column("check_id", _str(64)),
        sa.Column("stage", _str(16)),
        sa.Column("outcome", _str(32)),
        sa.Column("severity", sa.Integer),
        sa.Column("reason_code", _str(128), nullable=True),
        sa.Column("fixed_by", _str(32)),
        sa.Column("deterministic", sa.Boolean),
        sa.Column("cached", sa.Boolean),
        sa.Column("fingerprint", _str(128)),
        sa.Column("body", sa.JSON),
    )
    op.create_table(
        "decisions",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("run_id", _str(64)),
        sa.Column("status", _str(32)),
        sa.Column("awaiting", sa.JSON),
        sa.Column("tier", _str(32)),
        sa.Column("score_total", sa.Float),
        sa.Column("score_breakdown", sa.JSON),
        sa.Column("reason_codes", sa.JSON),
        sa.Column("counterfactuals", sa.JSON),
        sa.Column("reproducibility_hash", _str(128)),
    )
    op.create_table(
        "check_cache",
        sa.Column("fingerprint", _str(128), primary_key=True),
        sa.Column("check_id", _str(64)),
        sa.Column("result", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "case_events",
        sa.Column("id", _str(64), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("seq", sa.Integer),
        sa.Column("ts", sa.DateTime(timezone=True)),
        sa.Column("actor", _str(64)),
        sa.Column("type", _str(64)),
        sa.Column("payload", sa.JSON),
        sa.Column("prev_hash", _str(128)),
        sa.Column("entry_hash", _str(128)),
    )
    for t in [
        "approvals",
        "resolutions",
        "callbacks",
        "llm_calls",
        "messages",
        "vendors",
        "vendor_bank_accounts",
        "erp_outbox",
        "eval_runs",
        "eval_case_results",
        "clock_state",
        "adapter_faults",
    ]:
        op.create_table(
            t,
            sa.Column("id", _str(64), primary_key=True),
            sa.Column("payload", sa.JSON, nullable=True),
        )
    op.create_table(
        "idempotency_keys",
        sa.Column("key", _str(128), primary_key=True),
        sa.Column("case_id", _str(64)),
        sa.Column("run_id", _str(64)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for t in reversed(TABLES):
        op.drop_table(t)
